from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
from time import perf_counter

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
command = [str(root/'.venv-lmta-v42/bin/python'),'scripts/verify_terminal_win_v326.py',str(out)]
started = datetime.now(timezone.utc).isoformat()
wall = perf_counter(); before = resource.getrusage(resource.RUSAGE_CHILDREN)
with (out/'audit_stdout.log').open('w') as stdout,(out/'audit_stderr.log').open('w') as stderr:
    result = subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src')),stdout=stdout,stderr=stderr)
after = resource.getrusage(resource.RUSAGE_CHILDREN)
execution = dict(command=command,cwd=str(root),started_utc=started,
    completed_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,
    process_tree_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
    monotonic_wall_seconds=perf_counter()-wall,audit_exists=(out/'audit.json').exists())
(out/'audit_execution.json').write_text(json.dumps(execution,indent=2)+'\n')
if result.returncode == 0:
    audit = json.loads((out/'audit.json').read_text())
    costs = dict(schema='acfqp.terminal_win_full_execution_cost.v326',
        component_new_experiment_cpu_seconds=audit['new_experiment_component_cpu_seconds'],
        full_execution_process_tree_cpu_seconds=audit['new_experiment_full_cpu_seconds'],
        final_serialization_and_shutdown_cpu_seconds=audit['new_experiment_full_cpu_seconds']-audit['new_experiment_component_cpu_seconds'],
        full_economic_source_and_experiment_cpu_seconds=audit['full_economic_source_and_experiment_cpu_seconds'],
        independent_audit_process_tree_cpu_seconds=execution['process_tree_cpu_seconds'],
        independent_audit_monotonic_wall_seconds=execution['monotonic_wall_seconds'],
        scope='Successful V312 SOURCE inherited once. Full new execution includes fresh target acquisition, shared first spawns, terminal suffixes, equal-update replay fits and final shutdown. '
            'Previous target experiments excluded; audits separate; historical dynamics and failed-attempt CPU unknown.')
    (out/'audit_costs.json').write_text(json.dumps(costs,indent=2)+'\n')
