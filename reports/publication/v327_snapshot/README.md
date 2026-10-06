# Complete report JSON snapshot through V327

Large new research JSON is stored here with gzip compression. The manifest maps
each archive to its original project path. Compression preserves the complete
original content; scientific results, negative outcomes and provenance are
unchanged. Report links point directly to these archives. Small reports,
configuration, execution and verification records are published at their normal
paths. Raw trajectories, NPZ models, native builds, environments and caches are
retained locally rather than published in Git.

To restore the JSON at its original path in a fresh checkout, run from the
repository root:

```python
import gzip
import json
from pathlib import Path
import shutil

root = Path.cwd()
manifest = json.loads((root/'reports/publication/v327_snapshot/manifest.json').read_text())
for entry in manifest['files']:
    target = root/entry['source']
    if target.exists():
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(root/entry['archive'], 'rb') as source, target.open('wb') as output:
        shutil.copyfileobj(source, output)
```

Restoring report JSON does not supply the locally retained raw traces or head
arrays required for a complete experiment replay. The source entrypoints and
frozen protocols describe how those inputs were generated. `package.py` records
the one-time publication operation for this snapshot.
