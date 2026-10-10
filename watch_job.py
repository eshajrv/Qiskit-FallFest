"""Poll the fresh-run jobs every ~150 s. Exit (which wakes the assistant) only when something changes
or the 4:40 PM PT cutoff is reached. Prints only state changes. Key is read from the environment only."""
import os, sys, json, time, datetime
from zoneinfo import ZoneInfo
from qiskit_ibm_runtime import QiskitRuntimeService
PT = ZoneInfo("America/Los_Angeles")
CUTOFF = datetime.datetime(2026, 10, 10, 16, 40, tzinfo=PT)
s = QiskitRuntimeService(channel="ibm_quantum_platform", token=os.environ["IBM_QUANTUM_TOKEN"], instance="student-67")
def snapshot():
    jobs = json.load(open("fresh.json"))
    return {k: (jobs[k], str(s.job(jobs[k]).status())) for k in ("nl", "ex") if k in jobs}
prev = snapshot()
print(datetime.datetime.now(PT).strftime("%H:%M:%S"), "watching", prev, flush=True)
while True:
    time.sleep(150)
    now = datetime.datetime.now(PT)
    if now >= CUTOFF:
        print(now.strftime("%H:%M:%S"), "CUTOFF REACHED", snapshot(), flush=True); sys.exit(0)
    cur = snapshot()
    if cur != prev:
        print(now.strftime("%H:%M:%S"), "CHANGE", prev, "->", cur, "remaining", s.usage()["usage_remaining_seconds"], flush=True)
        sys.exit(0)
