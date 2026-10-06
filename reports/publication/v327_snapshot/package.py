"""Publish existing large report JSON without changing its scientific content."""
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
names = subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
sources = [root/name for name in names if name.startswith('reports/') and name.endswith('.json')
    and (root/name).stat().st_size >= 1000000 and not name.startswith('reports/publication/')]
mapping, entries = {}, []
for source in sources:
    archive = out/source.relative_to(root/'reports')
    archive = archive.with_suffix('.json.gz')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb') as src, archive.open('wb') as dst:
        with gzip.GzipFile(fileobj=dst,mode='wb',filename='',mtime=0,compresslevel=6) as zipped:
            shutil.copyfileobj(src,zipped)
    mapping[source] = archive
    entries.append(dict(source=source.relative_to(root).as_posix(),archive=archive.relative_to(root).as_posix(),
        source_bytes=source.stat().st_size,archive_bytes=archive.stat().st_size))

# Update report links only; source JSON, numerical results and provenance stay intact.
documents = [root/'README.md']+[root/name for name in names if name.endswith('.md')]
changed = []
for document in documents:
    original = document.read_text()
    def link(match):
        target, separator, fragment = match[2].partition('#')
        if '://' in target:
            return match[0]
        source = (document.parent/target).resolve()
        if source not in mapping:
            return match[0]
        target = Path(os.path.relpath(mapping[source],document.parent)).as_posix()
        return match[1]+target+(separator+fragment if separator else '')+match[3]
    updated = re.sub(r'(\[[^\]\n]*\]\()([^\)\n]+)(\))',link,original)
    if updated != original:
        document.write_text(updated);changed.append(document.relative_to(root).as_posix())

with (root/'.gitignore').open('a') as ignored:
    ignored.write('\n# Full report JSON is published in the V327 gzip snapshot; originals remain local.\n')
    ignored.writelines('/'+entry['source']+'\n' for entry in entries)
manifest = dict(schema='acfqp.publication_snapshot.v327',files=entries,updated_link_documents=changed,
    source_bytes=sum(e['source_bytes'] for e in entries),archive_bytes=sum(e['archive_bytes'] for e in entries),
    scientific_content='Complete original JSON, compressed without modifying results, labels or provenance.',
    omitted='Raw trajectories, NPZ heads, native builds, environments and caches remain local.',
    snapshot_generation='One-time packaging of unpublished report JSON at least 1000000 bytes before the V327 commit.')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(files=len(entries),source_bytes=manifest['source_bytes'],archive_bytes=manifest['archive_bytes'],
    updated_link_documents=len(changed))))
