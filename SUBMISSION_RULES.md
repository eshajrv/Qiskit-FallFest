# Submission rule for the fresh run (written 2026-10-10 before `python next_run.py fresh` produced any result)

Context: current best submission is the inverse-variance mean of run 1 edge and run 2 edge,
0.6788 +/- 0.0046, score 51.8. The handoff diagnosis is that the remaining error is bias from a
stale noise model (run 2 reused the 14:12 model while the raw value drifted 5 sigma).

## Rule

1. **Post-selection strategy: edge.** Fixed by the earlier rule (mirror SLC edge 1.019 was closer
   to 1.0 than node 1.052). Not revisited.

2. **Submit the fresh run's "SLC + TREX + post-selection" edge value ON ITS OWN.**
   Do not inverse-variance combine it with run 1 or run 2. Reason: those runs used a noise model
   that the diagnosis says was stale; combining would pull the stale bias back in, and the fresh
   run has ~4x the shots of run 1 anyway.

3. **Validity gates (checked without the grader and without the exact statevector value):**
   - The fresh noise learning and executor jobs both complete without error.
   - The chosen SLC tolerance yields a predicted total error (sqrt(b^2 + gamma^2/N)) <= 0.03.
   - The fresh SLC edge value lies in the physical range [-1, 1] and its statistical error <= 0.03.
   If any gate fails, we do NOT submit anything new and keep submission 3 (0.6788, score 51.8).

4. **We will call the grader once on the fresh edge SLC value** if the gates pass, log the score in
   RESULTS.md, and report it honestly whether it is above or below 51.8. We do not then switch to
   another value or combination because of the score.

5. We never choose runs, settings, or node/edge by comparing with the exact noiseless value or by
   comparing grader scores.

## Budget rule
- Estimated cost of next_run.py: noise learning ~88-90 s + executor at 512x256 shots ~75 s = ~165 s.
- Check `service.usage()["usage_remaining_seconds"]` first; next_run.py refuses below 180 s.
- No QPU job is submitted until Amirshayan gives an explicit OK after seeing the estimate.

## Additions written 2026-10-10 ~15:50 PT (still before any fresh result exists)

6. **Staleness gate.** If the executor job starts running more than 15 minutes after the noise
   learning job finished, the fresh noise model counts as stale. Log the result in RESULTS.md but
   do NOT submit it; keep submission 3 (0.6788, score 51.8). The learning finish time and the
   executor start time are taken from the job metadata (job.metrics() timestamps) and recorded in
   RESULTS.md.

7. **Hard cutoff 4:40 PM PT.** If the executor result is not back by 4:40 PM, cancel any queued job
   from this run with job.cancel(), stop, and keep 0.6788 (score 51.8) as the final answer. Nothing
   is submitted after 4:40 PM.

8. The noise learning job db5bq4svf2bc73cvmidg is left queued (queued time costs nothing).

9. The second IBM key is not used at all. The queue, not QPU seconds, is the bottleneck. That key
   should be deleted after today.
