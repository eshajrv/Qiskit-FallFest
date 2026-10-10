# RESULTS log, Noise Busters (ibm_kingston, chain [30, 29, 38, 49, 48, 47, 46, 45, 44, 43, 42, 41, 36, 21, 20])

All times Pacific, 2026-10-10. Every job is listed, including bad ones. Values are <Z6 Z7>.

## Prior session (from the handoff)

| Time | Job ID | What | Result |
|---|---|---|---|
| 14:11 | db5ajpcvf2bc73cvks4g | Baseline Estimator, resilience 0, 10k shots | 0.5774, submitted, score 0 |
| 14:12 | db5ak64vf2bc73cvkshg | Noise learning, scored circuit (3 layers, 88 s) | model used by run 1 and run 2 |
| 14:18 | db5al9qmb58s738a7sa0 | Run 1 executor 256x128, tol 1e-3, gamma^2 3.09 | raw 0.5450+/-0.0046; SLC node 0.7151+/-0.0152 (submitted, score 48.1); SLC edge 0.6938+/-0.0102 |
| 14:30 | db5armklf4us73c3pn20 | Run 2 executor 512x256, tol 1e-6, gamma^2 3.14, stale 14:12 model | raw 0.5710+/-0.0023; SLC node 0.6839+/-0.0075; SLC edge 0.6749+/-0.0052 |
| 14:33 | db5as9clf4us73c3pof0 | Mirror noise learning | - |
| 14:39 | db5av2amb58s738a8f70 | Mirror executor 256x128, tol 1e-2, gamma^2 46.8 | raw 0.5860; SLC node 1.0523+/-0.0665; SLC edge 1.0186+/-0.0430 (ideal 1.0) |

Submission 3 (current best): inverse-variance mean of run 1 edge and run 2 edge = 0.6788 +/- 0.0046, **score 51.8**.

## This session

- 15:29 dry run of `next_run.py fresh --dry-run`: 302 s remaining, chain reproduced, 3 unique layers, estimated cost ~165 s. No QPU job submitted.
- 15:32 `next_run.py fresh` submitted noise learning job **db5bq4svf2bc73cvmidg** (QUEUED, 0 s used). Executor not yet submitted; it goes in automatically after learning finishes.
- 15:45 job still QUEUED, ibm_kingston 85 pending jobs, 302 s remaining.
- 15:50 plan update: hard cutoff 4:40 PM PT, staleness gate (executor start > 15 min after learning finish = stale, log but do not submit), second key not used. See SUBMISSION_RULES.md items 6-9.

## Finding for the slides: queue delay causes stale noise model bias

ibm_kingston went from 8 pending jobs at 2:10 PM to 81 at 3:45 PM (85 at 3:45 by our check). Device
noise drifts while jobs wait: the raw <Z6 Z7> moved from 0.545 to 0.571 (over 5 sigma) in 12 minutes
earlier today. A noise model learned in one job and consumed by an executor job that waits in a long
queue is therefore out of date by the time it is used, even if the two jobs are submitted back to back.
Queue delay itself is a source of error mitigation bias, not just a loss of wall-clock time.
- 16:28 still QUEUED, ibm_kingston 92 pending jobs, 302 s remaining.
- 16:41 **cutoff reached.** Noise learning job db5bq4svf2bc73cvmidg was still QUEUED (0 s used) and was cancelled with job.cancel(). Executor never submitted. Fresh run produced no result.
- **Final answer stands: submission 3, 0.6788 +/- 0.0046, score 51.8.** Nothing submitted after 16:40, per SUBMISSION_RULES.md item 7. Remaining QPU budget untouched at 302 s.
