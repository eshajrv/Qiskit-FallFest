# Handoff: IBM Qiskit Fall Fest 2026, Noise Busters challenge

You are taking over a live hackathon task from another Claude session. Read this whole file before doing anything. The person you are helping is Amirshayan, a CS senior at SFSU who does quantum reservoir computing research on IBM Heron hardware. He is at the event in Berkeley today (Saturday 10 October 2026). **Judging starts at 5:00 PM Pacific.** Teams presenting a final result must show it reproduces from their QPU job IDs.

## 1. The task

Estimate the expectation value ⟨Z6 Z7⟩ of a fixed 15 qubit circuit on a real IBM quantum computer, with error mitigation, as close as possible to a hidden reference value.

- Circuit: 1D transverse field Ising chain, 15 qubits, 8 Trotter steps, each step is `rx(pi/4)` on every qubit, then `sdg, sdg, cz` on even bonds, then on odd bonds. Code is in section 6.
- Observable: `ZZ` on qubits 6 and 7.
- `circuit_mirror` = circuit followed by its inverse. Its ideal ⟨Z6 Z7⟩ is exactly 1.0. Use it only to validate the pipeline.
- Grader: `from qc_grader.challenges.fallfest_2026.noise_buster import check_result; check_result(value)`. It returns a score from 0 to 100. |error| ≥ 0.1 scores 0, |error| ≤ 0.001 scores 100. Calling it is free. It authenticates with the saved IBM Quantum account.

## 2. Credentials and budget

- IBM Quantum Platform API key: **not included in this file on purpose.** Amirshayan will paste it into the chat. Save it once with
  `QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token=KEY, overwrite=True, set_as_default=True)`
  and never print it or write it into any file you hand back.
- Instance: `student-67` (Open Plan). Backend used so far: **ibm_kingston** (Heron), opened with `use_fractional_gates=True` (needed for post-selection with `x_pulse_type="rx"`).
- **QPU time left: about 302 seconds** (checked 14:47 PT). The allowance is 600 s per rolling window. Check with `service.usage()["usage_remaining_seconds"]` before every job. Measured costs on this circuit: noise learning 88 s, executor with 2 items at 256×128 shots 21 s, at 512×256 shots 75 s, baseline Estimator 5 s.
- No Anthropic API key is needed for any of this. Only the IBM key.

## 3. Packages (versions that ran)

```
pip install -U qiskit qiskit-ibm-runtime samplomatic qiskit-addon-slc qiskit-addon-utils qc-grader
```
Ran with qiskit 2.5.2, qiskit-ibm-runtime 0.50.0, samplomatic 0.21.0, qiskit-addon-slc 0.1.0, qiskit-addon-utils 0.4.0. `NoiseLearnerV3` does not work in local or simulator mode. It needs the real backend.

## 4. What has been done and the results

**Strategy: shot budget aware SLC (shaded lightcones on top of PEC), plus TREX readout correction and post-selection.** For each bias tolerance, SLC gives a residual bias bound b and a sampling overhead γ². With N shots, the predicted error is sqrt(b² + γ²/N). The pipeline sweeps the tolerance on the CPU and picks the one with the lowest predicted error. This ties directly to Amirshayan's research on shot budgets ("the shot wall").

| Run | Time (PT) | Job IDs | Notes |
|---|---|---|---|
| Baseline, Estimator resilience 0, 10k shots | 14:11 | `db5ajpcvf2bc73cvks4g` | ⟨Z6Z7⟩ = 0.5774, **score 0** |
| Noise learning, scored circuit | 14:12 | `db5ak64vf2bc73cvkshg` | 3 unique layers, 88 s |
| Run 1 executor, 256×128 shots | 14:18 | `db5al9qmb58s738a7sa0` | tolerance 1e-3, γ² 3.09 (full PEC 7.90) |
| Run 2 executor, 512×256 shots, **reused the 14:12 noise model** | 14:30 | `db5armklf4us73c3pn20` | tolerance 1e-6, γ² 3.14 |
| Mirror noise learning | 14:33 | `db5as9clf4us73c3pof0` | same qubit chain |
| Mirror executor, 256×128 | 14:39 | `db5av2amb58s738a8f70` | tolerance 1e-2, γ² 46.8 (full PEC 118) |

Qubit chain for all runs (seed_transpiler=1234): `[30, 29, 38, 49, 48, 47, 46, 45, 44, 43, 42, 41, 36, 21, 20]`

Results, ⟨Z6 Z7⟩:

| Method | Run 1 node | Run 1 edge | Run 2 node | Run 2 edge | Mirror node | Mirror edge |
|---|---|---|---|---|---|---|
| Raw | 0.5450 ± 0.0046 | same | 0.5710 ± 0.0023 | same | 0.5860 ± 0.0045 | same |
| TREX + post-selection | 0.6157 ± 0.0075 | 0.5947 ± 0.0052 | 0.6354 ± 0.0036 | 0.6199 ± 0.0025 | 0.6867 ± 0.0073 | 0.6480 ± 0.0049 |
| SLC + TREX + post-selection | 0.7151 ± 0.0152 | 0.6938 ± 0.0102 | 0.6839 ± 0.0075 | 0.6749 ± 0.0052 | 1.0523 ± 0.0665 | 1.0186 ± 0.0430 |

Submissions so far:
1. Baseline 0.5774, score 0.
2. Run 1 SLC node 0.7151, **score 48.1**.
3. Current best: inverse variance weighted mean of run 1 edge and run 2 edge = **0.6788 ± 0.0046, score 51.8** (|error| 0.0165).

The decision rule for submission 3 was written at 14:29, before the mirror or run 2 results were seen: pick node or edge by which SLC mirror value lands closer to 1.0 (edge won: 1.019 vs 1.052), then combine run 1 and run 2 with that strategy.

## 5. Diagnosis: what limits the score now

- The submitted error (0.0165) is about 3.5 times the statistical error (0.0046). So the remaining error is **bias, not shot noise**. More shots alone will not help much.
- The raw value drifted from 0.545 (14:18) to 0.571 (14:30), more than 5σ. The device noise changed, but run 2 reused the noise model learned at 14:12. **A stale noise model is the most likely source of the bias.**
- The mirror check passed (1.019 ± 0.043 edge), so the pipeline wiring is correct.

## 6. Recommended next step (fits the budget)

Learn a fresh noise model and run the executor immediately after it, so the model matches the device. Script `next_run.py` below does exactly this and does **not** submit. Cost about 165 s of the ~302 s left. It refuses to run if fewer than 180 s remain.

Before running it, write down the submission rule, for example: "submit the fresh run's edge SLC value on its own, because it is the only run whose noise model is current" or "inverse variance combine it with the earlier edge runs". Decide this **before** seeing the result.

Other ideas, only if time and budget allow (each needs noise learning, so realistically pick one):
- Dynamical decoupling: `apply_dynamical_decoupling` from `qiskit_ibm_runtime.executor.dynamical_decoupling` padded into the `QuantumProgram`.
- PNA (`qiskit-addon-pna`) as a cross check against SLC using the same learned noise model. It needs no extra noise learning, only extra shots for the larger observable.
- Probabilistic error amplification style ZNE: add executor items with `noise_scales` set to +1 and +2 (amplified noise) and extrapolate to −1. No γ² overhead.
- Pick a lower error qubit chain with real time benchmarking. This changes the layout, so it requires new noise learning.

## 7. Integrity rules (important for judging)

- At 15 qubits the exact noiseless value can be computed with a statevector in seconds. **Never submit it, and never choose between runs or settings by comparing against it.** Judges will ask to reproduce the number from job IDs.
- Do not pick between results by looking at grader scores. Choose with a rule written before the data is seen, as in section 4.
- Keep every job ID. Reuse finished jobs with `service.job(job_id)` instead of resubmitting.

## 8. Code

### 8a. `nb_pipeline.py` (the pipeline every run used)

The driver scripts `exec` this file after defining `service`, `backend`, `circuit` and `observable`, and patch both pass managers to use `seed_transpiler=1234` so the qubit chain is reproducible.

```python
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
```

### 8b. `next_run.py` (fresh noise model, then executor, no submission)

Put it in the same folder as `nb_pipeline.py` and run `python next_run.py fresh`. It writes `fresh.json` with job IDs and results and can be rerun safely, since it reattaches to saved job IDs.

```python
"""Fresh noise model + immediate executor run on the scored circuit.

Usage:  python next_run.py fresh
Costs about 90 s (noise learning) + 75 s (executor, 4x shots) of QPU time.
Does NOT submit to the grader. Decide the submission with the written rule.
"""
import json, os, sys, time, numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import QiskitRuntimeService

MODE = sys.argv[1] if len(sys.argv) > 1 else "fresh"
STATE = f"{MODE}.json"
jobs = json.load(open(STATE)) if os.path.exists(STATE) else {}
def save(): json.dump(jobs, open(STATE, "w"), indent=1)
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

service = QiskitRuntimeService()
left = service.usage()["usage_remaining_seconds"]
log("remaining QPU seconds", left)
if left < 180 and "ex" not in jobs:
    sys.exit("Not enough QPU time for a fresh learn + 4x run. Stop here.")
backend = service.backend("ibm_kingston", use_fractional_gates=True)

def construct_ising_circuit(n, steps, a):
    qc = QuantumCircuit(n)
    for _ in range(steps):
        qc.rx(a, range(n))
        for f in (1, 2):
            for i in range(f, n, 2):
                qc.sdg([i - 1, i]); qc.cz(i - 1, i)
    return qc
circuit = construct_ising_circuit(15, 8, np.pi / 4)
observable = SparsePauliOp.from_sparse_list([("ZZ", [6, 7], 1.0)], num_qubits=15)

src = open("nb_pipeline.py").read()
src = src.replace("optimization_level=3\n", "optimization_level=3, seed_transpiler=1234\n")
src = src.replace("initial_layout=layout, optimization_level=0\n",
                  "initial_layout=layout, optimization_level=0, seed_transpiler=1234\n")
exec(src)
NUM_RANDOMIZATIONS, SHOTS_PER_RANDOMIZATION = 512, 256   # 4x run 1

st = prepare(circuit, f"circuit-{MODE}")
learn_noise(st, job_id=jobs.get("nl")); jobs["nl"] = st["nl_job"].job_id(); save()
st["nl_job"].result(); log("noise learning usage", st["nl_job"].usage())
select_errors(st)                      # runs right after learning, so the model is fresh
run_executor(st, job_id=jobs.get("ex")); jobs["ex"] = st["ex_job"].job_id(); save()
st["ex_job"].result()
log("executor usage", st["ex_job"].usage(), "remaining", service.usage()["usage_remaining_seconds"])
res = {s: postprocess(st, strategy=s) for s in ("node", "edge")}
jobs["results"] = {s: {k: list(v) for k, v in r.items()} for s, r in res.items()}
jobs["gamma2"] = float(st["gamma"] ** 2); jobs["tolerance"] = float(st["tol"]); jobs["chain"] = st["layout"]
save(); log("DONE (not submitted)")
```

### 8c. Combining runs and submitting

```python
import json, numpy as np
from qc_grader.challenges.fallfest_2026.noise_buster import check_result
vals = [(0.6938105, 0.0102419), (0.6749, 0.0052)]   # replace with the runs your rule selects, (value, error)
v = np.array([a for a, _ in vals]); e = np.array([b for _, b in vals]); w = 1 / e**2
m, s = (w * v).sum() / w.sum(), 1 / np.sqrt(w.sum())
print(m, s)
check_result(float(m))
```
Exact run 2 edge value: 0.6749155654560804 ± 0.005187463941710799.

## 9. Presentation talking points

- SLC cut the sampling overhead from 7.9× (full PEC) to 3.1×.
- The shot budget rule picks the bias tolerance that minimizes sqrt(b² + γ²/N), instead of cancelling every error and drowning the answer in shot noise.
- The mirror check validates the pipeline: raw 0.586 → SLC 1.019 ± 0.043 (ideal 1.0).
- Honest finding: after 4× more shots, the error was dominated by noise model drift, not shot noise. Noise models go stale in about 15 minutes on this device.
- Score went 0 → 48.1 → 51.8, each step with a rule written in advance.

## 10. How to behave in this chat

- Amirshayan writes informally and fast. Answer in short, plain sentences.
- If your chat cannot run code or reach `quantum.cloud.ibm.com`, give him exact commands to run on his laptop and ask him to paste the output back.
- Confirm the remaining QPU seconds with him before submitting any QPU job.
