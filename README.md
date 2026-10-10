# Qiskit-FallFest
## Noise Busters challenge (IBM Qiskit Fall Fest 2026, Berkeley)

Estimate <Z6 Z7> of a 15-qubit Ising Trotter circuit on ibm_kingston with error mitigation.
Final answer **0.6788 ± 0.0046, grader score 51.8**, using shaded lightcones (SLC) on top of PEC
with a shot-budget rule for the bias tolerance, TREX readout correction and edge post-selection.

- `nb_pipeline.py` the five-stage pipeline (prepare, learn_noise, select_errors, run_executor, postprocess)
- `reproduce.py` recomputes the submitted value from the finished job IDs, no QPU time needed; output in `reproduce.log`
- `next_run.py` driver for a fresh noise model + executor run (`python next_run.py fresh`, `--dry-run` to only estimate cost)
- `RESULTS.md` every job ID and result, including the failed ones
- `SUBMISSION_RULES.md` the submission rules, written before the data was seen
- `NOISE_BUSTERS_HANDOFF.md` full write-up of the method, results and diagnosis
- `Noise_Busters_Presentation.pdf` 3-minute deck (`make_slides.py` builds it)
- `pyscf/` tiny scipy shim for the one pyscf call in qiskit-addon-slc (pyscf has no Windows wheel)

The IBM key is read only from the `IBM_QUANTUM_TOKEN` environment variable and is not stored anywhere.
