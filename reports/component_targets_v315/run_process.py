from pathlib import Path
import json,os,subprocess
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent
command=[str(root/'.venv-lmta-v42/bin/python'),'scripts/run_component_targets_v315.py','--prior-summary','reports/local_targets_v314/summary.json','--output','reports/component_targets_v315']
started=datetime.now(timezone.utc).isoformat()
with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
    result=subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src')),stdout=stdout,stderr=stderr)
(out/'execution.json').write_text(json.dumps(dict(command=command,cwd=str(root),started=started,completed=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,summary_exists=(out/'summary.json').exists(),scientific_status='TERMINAL_PENDING_AUDIT' if result.returncode==0 else 'INCOMPLETE_NO_SUPPORT'),indent=2)+'\n')
