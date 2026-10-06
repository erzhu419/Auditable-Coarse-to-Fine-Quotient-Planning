from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
from time import perf_counter

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
command = [str(root/'.venv-lmta-v42/bin/python'),'scripts/run_teacher_calibration_v320.py',
    '--source-summary','reports/query_supervision_v319/summary.json','--output','reports/teacher_calibration_v320']
started = datetime.now(timezone.utc).isoformat()
wall = perf_counter(); before = resource.getrusage(resource.RUSAGE_CHILDREN)
with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
    result = subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src')),stdout=stdout,stderr=stderr)
after = resource.getrusage(resource.RUSAGE_CHILDREN)
(out/'execution.json').write_text(json.dumps(dict(command=command,cwd=str(root),started_utc=started,
    completed_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,
    process_tree_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
    monotonic_wall_seconds=perf_counter()-wall,summary_exists=(out/'summary.json').exists(),
    scientific_status='TERMINAL_PENDING_AUDIT' if result.returncode==0 else 'INCOMPLETE_NO_SUPPORT'),indent=2)+'\n')
