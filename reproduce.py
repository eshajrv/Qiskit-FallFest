"""Reproduce the submitted <Z6 Z7> = 0.6788 from the finished job IDs. Uses NO QPU time.

Usage:  python reproduce.py
Reattaches to the noise learning job and the two executor jobs, reruns the CPU stages
(SLC bounds, tolerance selection, TREX + post-selection), and combines run 1 and run 2
edge values by inverse variance. Reads the IBM key only from IBM_QUANTUM_TOKEN.
"""
import os, sys, numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import QiskitRuntimeService

JOBS = {
    "nl": "db5ak64vf2bc73cvkshg",                      # noise learning, 14:12
    "run1": ("db5al9qmb58s738a7sa0", 256, 128),         # executor, 14:18
    "run2": ("db5armklf4us73c3pn20", 512, 256),         # executor, 14:30
}

TOKEN = os.environ.get("IBM_QUANTUM_TOKEN") or sys.exit("IBM_QUANTUM_TOKEN is not set")
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN,
                               instance=os.environ.get("IBM_QUANTUM_INSTANCE", "student-67"))
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

st = prepare(circuit, "reproduce")
learn_noise(st, job_id=JOBS["nl"])

edge = {}
for name in ("run1", "run2"):
    job_id, NUM_RANDOMIZATIONS, SHOTS_PER_RANDOMIZATION = JOBS[name]
    print(f"\n==== {name}: {NUM_RANDOMIZATIONS}x{SHOTS_PER_RANDOMIZATION} shots, job {job_id}")
    select_errors(st)
    run_executor(st, job_id=job_id)
    out = postprocess(st, strategy="edge")
    edge[name] = out["SLC + TREX + post-selection"]

v = np.array([edge[k][0] for k in ("run1", "run2")])
e = np.array([edge[k][1] for k in ("run1", "run2")])
w = 1 / e**2
m, s = (w * v).sum() / w.sum(), 1 / np.sqrt(w.sum())
print(f"\nrun 1 edge SLC: {v[0]:.4f} +/- {e[0]:.4f}")
print(f"run 2 edge SLC: {v[1]:.4f} +/- {e[1]:.4f}")
print(f"SUBMITTED VALUE (inverse-variance mean): {m:.4f} +/- {s:.4f}   (expected 0.6788 +/- 0.0046)")
