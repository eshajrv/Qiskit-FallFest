"""Fresh noise model + immediate executor run on the scored circuit.

Usage:  python next_run.py fresh
Costs about 90 s (noise learning) + 75 s (executor, 4x shots) of QPU time.
Does NOT submit to the grader. Decide the submission with the written rule.
"""
import json, os, sys, time, numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import QiskitRuntimeService

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DRY_RUN = "--dry-run" in sys.argv      # stop before any QPU job, print the estimate only
MODE = ARGS[0] if ARGS else "fresh"
STATE = f"{MODE}.json"
jobs = json.load(open(STATE)) if os.path.exists(STATE) else {}
def save(): json.dump(jobs, open(STATE, "w"), indent=1)
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

# Key is read ONLY from the environment; it is never saved to disk or printed.
TOKEN = os.environ.get("IBM_QUANTUM_TOKEN")
if not TOKEN:
    sys.exit("IBM_QUANTUM_TOKEN is not set")
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN,
                               instance=os.environ.get("IBM_QUANTUM_INSTANCE", "student-67"))
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
EST_NL, EST_EX = 90, 75   # measured on this circuit (handoff section 2)
need = (0 if "nl" in jobs else EST_NL) + (0 if "ex" in jobs else EST_EX)
log(f"estimated QPU cost of this run: ~{need} s (noise learning ~{EST_NL} s + executor 512x256 ~{EST_EX} s); "
    f"remaining now {left:.0f} s -> ~{left - need:.0f} s after")
if DRY_RUN and not ("nl" in jobs and "ex" in jobs):
    log("DRY RUN: stopping before any QPU job is submitted"); sys.exit(0)
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
