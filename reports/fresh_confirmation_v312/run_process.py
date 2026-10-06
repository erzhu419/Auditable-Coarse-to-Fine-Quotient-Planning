from pathlib import Path
import json, os, subprocess
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[2]; out=Path(__file__).resolve().parent
started=datetime.now(timezone.utc).isoformat()
env=dict(os.environ,PYTHONPATH=str(root/'src'))
command=[str(root/'.venv-lmta-v42/bin/python'),'scripts/run_fresh_confirmation_v312.py','--source-summary','reports/fresh_source_v312/source_summary.json','--output','reports/fresh_confirmation_v312']
with (out/'stdout.log').open('w') as stdout, (out/'stderr.log').open('w') as stderr:
    result=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr)
(out/'execution.json').write_text(json.dumps(dict(command=command,cwd=str(root),started=started,completed=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,summary_exists=(out/'summary.json').exists()),indent=2)+'\n')
