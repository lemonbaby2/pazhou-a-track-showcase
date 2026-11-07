from pathlib import Path
from huggingface_hub import snapshot_download
import hashlib, json, sys, time
root=Path(r'E:\研究生学习\黑客松\pazhou_a_open_datasets_2026-11-07')
items=[
 ('lerobot/aloha_mobile_wipe_wine','b57bde2a10c343cbc2be9a0052f126854c4bb091','aloha_mobile_wipe_wine'),
 ('lerobot/aloha_static_coffee','b144896feb1f37398a862927b22cd3abdf005a6b','aloha_static_coffee'),
]
for repo,rev,name in items:
 dest=root/name
 print(f'START {repo} @ {rev}',flush=True)
 t=time.time()
 snapshot_download(repo_id=repo,repo_type='dataset',revision=rev,local_dir=dest,token=False,max_workers=8)
 files=[]
 for p in sorted(dest.rglob('*')):
  if p.is_file() and '.cache' not in p.parts:
   h=hashlib.sha256()
   with p.open('rb') as f:
    for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
   files.append({'path':str(p.relative_to(root)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':h.hexdigest()})
 manifest={'repo_id':repo,'revision':rev,'downloaded_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'files':files}
 (root/f'{name}_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(f'DONE {repo}: {len(files)} files, {manifest["total_bytes"]} bytes in {time.time()-t:.1f}s',flush=True)
