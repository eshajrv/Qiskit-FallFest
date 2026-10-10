# ==== CELL: setup ====
import numpy as np
import samplomatic
from qiskit.transpiler import PassManager, generate_preset_pass_manager
from qiskit.transpiler.passes import RemoveBarriers

from qiskit_addon_slc.bounds import (
    compute_backward_bounds,
    compute_forward_bounds,
    compute_local_scales,
    merge_bounds,
    tighten_with_speed_limit,
)
from qiskit_addon_slc.utils import generate_noise_model_paulis, map_modifier_ref_to_ref
from qiskit_addon_utils.exp_vals.expectation_values import executor_expectation_values
from qiskit_addon_utils.exp_vals.measurement_bases import get_measurement_bases
from qiskit_addon_utils.exp_vals.observable_mappings import map_observable_virtual_to_canonical
from qiskit_addon_utils.noise_management import gamma_from_noisy_boxes, trex_factors
from qiskit_addon_utils.noise_management.post_selection import PostSelector
from qiskit_addon_utils.noise_management.post_selection.transpiler.passes import (
    AddPostSelectionMeasures,
    AddSpectatorMeasures,
)
from qiskit_ibm_runtime import Executor, QuantumProgram
from qiskit_ibm_runtime.noise_learner_v3 import NoiseLearnerV3
from samplomatic.transpiler import generate_boxing_pass_manager
from samplomatic.utils import find_unique_box_instructions

# --- knobs ---
SLC_MAX_TERMS = 1000
SLC_TIMEOUT = 60
NOISE_LEARNER_OPTIONS = {  # the challenge's suggested budget, under ~4 min per job
    "num_randomizations": 32,
    "shots_per_randomization": 128,
    "layer_pair_depths": [1, 4, 16, 32],
    "post_selection": {"enable": True, "strategy": "edge", "x_pulse_type": "rx"},
}
NUM_RANDOMIZATIONS = 256        # executor randomizations per item
SHOTS_PER_RANDOMIZATION = 128   # 256 x 128 = 32,768 shots per item
TOLERANCES = [1e-6, 1e-3, 3e-3, 1e-2, 2e-2, 3e-2, 5e-2]

boxes_pm = generate_boxing_pass_manager(
    twirling_strategy="active",
    inject_noise_strategy="individual_modification",
    inject_noise_site="after",
    inject_noise_targets="gates",
    measure_annotations="all",
)


# ==== CELL: stage 1, CPU only ====
def prepare(circ, label):
    """Layout, boxing, candidate noise terms, and both SLC bounds. No QPU."""
    c = RemoveBarriers()(circ)
    c.measure_active()
    layout = generate_preset_pass_manager(
        backend=backend, optimization_level=3
    ).run(c).layout.final_index_layout()
    isa = generate_preset_pass_manager(
        backend=backend, initial_layout=layout, optimization_level=0
    ).run(c)
    boxed = boxes_pm.run(isa)
    unique = find_unique_box_instructions(boxed, normalize_annotations=None, undress_boxes=True)
    nmp = generate_noise_model_paulis(unique, backend.coupling_map, boxed)

    bwd = compute_backward_bounds(
        boxed, nmp, evolution_max_terms=SLC_MAX_TERMS, timeout=SLC_TIMEOUT
    )
    isa_obs = observable.apply_layout(layout, num_qubits=isa.num_qubits)
    fwd = compute_forward_bounds(
        boxed, nmp, isa_obs,
        evolution_max_terms=SLC_MAX_TERMS, eigval_max_qubits=18, atol=1e-8,
        timeout=SLC_TIMEOUT,
    )
    fwd = tighten_with_speed_limit(fwd, boxed, nmp, isa_obs)

    # measurement bases + reversers (canonical order for TREX, virtual for the executor)
    meas_box = boxed.data[-1]
    canonical_qubits = [i for i, q in enumerate(boxed.qubits) if q in meas_box.qubits]
    obs_canon = map_observable_virtual_to_canonical(observable, layout, canonical_qubits)
    bases, rev_canon = get_measurement_bases(obs_canon)
    _, rev_meas = get_measurement_bases(observable)

    n_box = sum(1 for inst in boxed.data if inst.operation.name == "box")
    print(f"[{label}] chain {layout}")
    print(f"[{label}] {n_box} boxes, {len(unique)} unique layers to learn")
    return dict(label=label, layout=layout, isa=isa, boxed=boxed, unique=unique,
                nmp=nmp, bwd=bwd, fwd=fwd, basis=bases[0],
                rev_canon=rev_canon, rev_meas=rev_meas)


# ==== CELL: stage 2, noise learning (QPU) ====
def learn_noise(state, job_id=None):
    """Submit noise learning, or reattach to a finished job by id."""
    if job_id:
        job = service.job(job_id)
    else:
        job = NoiseLearnerV3(mode=backend, options=NOISE_LEARNER_OPTIONS).run(state["unique"])
    state["nl_job"] = job
    print(f"[{state['label']}] noise learning job id: {job.job_id()}  <- save this")
    return job


# ==== CELL: stage 3, pick the bias tolerance for the shot budget (CPU) ====
def select_errors(state):
    """Shot-budget-aware SLC.

    For each bias tolerance, SLC returns a residual bias bound b and a gamma.
    With N shots the statistical error is about gamma / sqrt(N), so the
    predicted total error is sqrt(b^2 + gamma^2 / N). Pick the tolerance that
    minimizes it instead of always cancelling everything.
    """
    job = state["nl_job"]
    assert job.backend().name == backend.name, "noise job ran on a different backend"
    res = job.result()
    refs = res.to_dict(state["unique"], require_refs=False)
    id_map = map_modifier_ref_to_ref(state["boxed"])
    merged = merge_bounds(state["boxed"], state["fwd"], state["bwd"], refs)
    n_shots = NUM_RANDOMIZATIONS * SHOTS_PER_RANDOMIZATION

    gamma_full = gamma_from_noisy_boxes(refs, id_map)
    print(f"[{state['label']}] full PEC gamma^2 = {gamma_full**2:.2f}, "
          f"shot error ~ {gamma_full / np.sqrt(n_shots):.4f}")
    print(f"{'tolerance':>10} {'bias bound':>11} {'gamma^2':>9} {'shot err':>9} {'pred total':>11}")
    best = None
    for tol in TOLERANCES:
        try:
            ls, _cost, bias = compute_local_scales(
                state["boxed"], merged, refs,
                sampling_cost_budget=np.inf, bias_tolerance=tol,
            )
        except IndexError:  # tolerance above the total bias: nothing left to mitigate
            continue
        gamma = gamma_from_noisy_boxes(refs, id_map, ls)
        shot = gamma / np.sqrt(n_shots)
        pred = float(np.sqrt(bias**2 + shot**2))
        print(f"{tol:>10.0e} {bias:>11.4f} {gamma**2:>9.2f} {shot:>9.4f} {pred:>11.4f}")
        if best is None or pred < best[0]:
            best = (pred, tol, ls, gamma, bias)

    pred, tol, ls, gamma, bias = best
    print(f"[{state['label']}] chosen tolerance {tol:.0e}: gamma^2 = {gamma**2:.2f}, "
          f"predicted total error {pred:.4f}")
    state.update(refs=refs, id_map=id_map, ls=ls, gamma=gamma, tol=tol,
                 meas_noise=res[-1].to_pauli_lindblad_map())
    return state


# ==== CELL: stage 4, executor (QPU) ====
def run_executor(state, job_id=None):
    """Two items: SLC mitigated (anti-noise on) and an unmitigated baseline."""
    template, samplex = samplomatic.build(state["boxed"])
    final_template = PassManager([
        AddSpectatorMeasures(backend.coupling_map),
        AddPostSelectionMeasures(x_pulse_type="rx"),
    ]).run(template)
    state["final_template"] = final_template  # needed for post-selection, even on reuse

    if job_id:
        job = service.job(job_id)
    else:
        basis_key = next(s.name.split(".", 1)[1]
                         for s in samplex.inputs().get_specs("basis_changes"))
        noise_refs = [s.name.split(".", 1)[1]
                      for s in samplex.inputs().get_specs("noise_scales")]
        program = QuantumProgram(shots=SHOTS_PER_RANDOMIZATION, noise_maps=state["refs"])
        # bind EVERY noise_scales ref: an unbound ref injects full-strength noise
        for scale, ls in ((-1.0, state["ls"]), (0.0, None)):
            inp = {f"noise_scales.{r}": scale for r in noise_refs}
            inp |= {"basis_changes": {basis_key: state["basis"]}}
            if ls is not None:
                inp |= {"local_scales": ls}
            program.append_samplex_item(
                circuit=final_template,
                samplex=samplex,
                samplex_arguments=samplex.inputs().make_broadcastable().bind(**inp),
                shape=(NUM_RANDOMIZATIONS,),
            )
        job = Executor(backend).run(program)
    state["ex_job"] = job
    print(f"[{state['label']}] executor job id: {job.job_id()}  <- save this")
    return job


# ==== CELL: stage 5, post-process (CPU) ====
def postprocess(state, strategy="node"):
    res = state["ex_job"].result()
    ps = PostSelector.from_circuit(circuit=state["final_template"],
                                   coupling_map=backend.coupling_map)
    trex = trex_factors(state["meas_noise"], state["rev_canon"])
    d_slc, d_raw = res[0], res[1]

    def ev(d, mitigate_gates, mitigate_readout):
        kw = {}
        if mitigate_readout:
            kw = dict(postselect_mask=ps.compute_mask(d, strategy=strategy),
                      rescale_factors=trex)
        v = executor_expectation_values(
            d["meas"], state["rev_meas"], None, avg_axis=0,
            measurement_flips=d["measurement_flips.meas"],
            pauli_signs=d.get("pauli_signs", None),
            gamma_factor=state["gamma"] if mitigate_gates else 1.0,
            **kw,
        )
        return float(v[0][0]), float(np.sqrt(v[0][1]))

    out = {
        "raw": ev(d_raw, False, False),
        "readout only (TREX + post-selection)": ev(d_raw, False, True),
        "SLC + TREX + post-selection": ev(d_slc, True, True),
    }
    print(f"[{state['label']}] <Z6 Z7>   ({strategy} post-selection)")
    for name, (v, e) in out.items():
        print(f"  {name:38s} {v:+.4f} +/- {e:.4f}")
    state["result"] = out
    return out
