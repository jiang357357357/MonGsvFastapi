"""Exercise real CUDA training, checkpoint resume, telemetry and preview HTTP APIs."""
import argparse
import base64
import hashlib
import io
import json
import time
from pathlib import Path

import requests
import soundfile as sf

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:40322')
parser.add_argument('--output',default='Data/Output/TrainingWorkbench')
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
output=root/args.output;output.mkdir(parents=True,exist_ok=True)
session=requests.Session()
def get(path):
    response=session.get(args.base_url+path,timeout=60);response.raise_for_status();return response.json()
def start(options):
    response=session.post(args.base_url+'/training/workbench/start',files={'options':(None,json.dumps(options,ensure_ascii=False))},timeout=90)
    response.raise_for_status();return response.json()['training_workflow']
def wait(run):
    deadline=time.monotonic()+600;seen=set()
    while time.monotonic()<deadline:
        run=get('/training/workbench/runs/'+run['workflow_id'])
        state=(run['phase'],run.get('current_target'),run['status'])
        if state not in seen:print('STATE',state,flush=True);seen.add(state)
        if run['status'] in {'completed','failed','stopped'}:
            assert run['status']=='completed',run.get('error')
            return run
        time.sleep(2)
    raise TimeoutError('Real training timed out')
original=root/'Resources/Model/蔚蓝档案/阿罗娜v21'
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for version in ('v5dev','v5turbo') for folder,pattern in (('GPT','*.ckpt'),('SoVITS','*.pth')) for p in (original/version/folder).glob(pattern)}
options={'project_name':'阿罗娜v21','world_name':'蔚蓝档案','version':'v5dev','source_version':'v5turbo',
         'role_mode':'existing','preprocessing_mode':'cached','training_mode':'fresh',
         'train_gpt':True,'train_sovits':True,'gpt_batch_size':8,'sovits_batch_size':4,
         'gpt_total_epoch':1,'sovits_total_epoch':1,'gpu_numbers':'0','lora_rank':4,'save_every_epoch':1,
         'grad_checkpoint':True,'publish_models':False}
fresh=wait(start(options))
assert fresh['preprocessing']['semantic_encoding']=='completed'
workspace=Path(fresh['project_root']);assert workspace.parent.name=='runs'
assert (workspace/'dataset/4-cnhubert').is_symlink()
assert fresh['targets'][0]['target']=='sovits'
for target in fresh['targets']:
    assert target['telemetry']['loss_history'] and target['telemetry']['current_epoch']==1
    log=get('/training/workbench/runs/'+fresh['workflow_id']+'/logs?target='+target['target'])
    assert log['text'] and Path(log['log_file']).is_file()
    (output/(target['target']+'-fresh.log')).write_text(log['text'])
(output/'fresh.json').write_text(json.dumps(fresh,ensure_ascii=False,indent=2))
print('FRESH_REAL_GPU_PASSED',fresh['workflow_id'],flush=True)
resume=wait(start(dict(options,training_mode='resume',resume_workspace=str(workspace),gpt_total_epoch=2,sovits_total_epoch=2)))
assert resume['project_root']==str(workspace)
for target in resume['targets']:
    assert target['telemetry']['current_epoch']==2
    assert Path(target['model']).is_file()
    log=get('/training/workbench/runs/'+resume['workflow_id']+'/logs?target='+target['target'])
    if target['target']=='sovits':assert 'start training from epoch 2' in Path(log['log_file']).read_text()
    else:assert 'ckpt_path: None' not in Path(log['log_file']).read_text()
(output/'resume.json').write_text(json.dumps(resume,ensure_ascii=False,indent=2))
print('RESUME_REAL_GPU_PASSED',resume['workflow_id'],flush=True)
emotion=resume['preview']['emotions'][0]['name']
response=session.post(args.base_url+'/training/workbench/runs/'+resume['workflow_id']+'/preview',json={'text':'老师，今天也一起加油吧！','emotion':emotion,'seed':2027},timeout=180)
response.raise_for_status();audio=response.json();assert audio['success']
raw=base64.b64decode(audio['audio_data']);wave,sr=sf.read(io.BytesIO(raw));assert sr==48000 and len(wave)>sr
(output/'preview.wav').write_bytes(raw)
assert all(Path(path).is_file() and hashlib.sha256(Path(path).read_bytes()).hexdigest()==value for path,value in before.items())
assert {r['workflow_id'] for r in get('/training/workbench/runs')['runs']} >= {fresh['workflow_id'],resume['workflow_id']}
(output/'report.json').write_text(json.dumps({'status':'passed','fresh':fresh['workflow_id'],'resume':resume['workflow_id'],'sample_rate':sr,'duration':len(wave)/sr,'original_model_hashes':before},ensure_ascii=False,indent=2))
print('WORKBENCH_REAL_GPU_HTTP_PREVIEW_PASSED',flush=True)
