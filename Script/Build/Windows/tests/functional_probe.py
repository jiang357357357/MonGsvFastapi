"""Real HTTP synthesis/training acceptance. Run with the target runtime, never mocks."""
from __future__ import annotations
import argparse,base64,hashlib,json,os,platform,time,traceback
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
import numpy as np
import requests
import soundfile as sf


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--reports',type=Path,required=True);p.add_argument('--backend',required=True);p.add_argument('--mode',choices=['windows-cpu','linux-gpu'],required=True);p.add_argument('--upload',default='');p.add_argument('--resume',action='store_true');p.add_argument('--existing-workflow',default='');p.add_argument('--project-name',default='功能验收角色');args=p.parse_args()
    args.root=args.root.resolve();args.assets=args.assets.resolve();args.reports.mkdir(parents=True,exist_ok=True)
    report={'success':False,'mode':args.mode,'started_at':datetime.now().astimezone().isoformat(),'platform':platform.platform(),'checks':[],'errors':[]}
    session=requests.Session();session.trust_env=False
    def upload(path):
        if args.upload:
            try:
                with path.open('rb') as f:session.put(args.upload+'/reports/'+path.name,data=f,timeout=20).raise_for_status()
            except Exception as e:print('Report upload:',e,flush=True)
    def write(name,obj):
        path=args.reports/name;path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');upload(path);return path
    def progress(stage,**details):
        print(json.dumps({'stage':stage,**details},ensure_ascii=False),flush=True);write('functional-progress.json',{'stage':stage,'at':datetime.now().astimezone().isoformat(),**details})
    def api(method,path,**kwargs):
        for attempt in range(4):
            try:
                r=session.request(method,args.backend+path,timeout=1800,**kwargs);break
            except requests.ConnectionError:
                if method!='GET' or attempt==3:raise
                time.sleep(attempt+1)
        if not r.ok:raise RuntimeError(f'{method} {path}: HTTP {r.status_code}: {r.text[:1800]}')
        return r.json()
    def check(name,fn):
        progress(name);started=time.monotonic()
        try:
            result=fn();report['checks'].append({'name':name,'success':True,'seconds':round(time.monotonic()-started,2),'result':result});return result
        except Exception as e:
            report['checks'].append({'name':name,'success':False,'error':str(e),'traceback':traceback.format_exc()});report['errors'].append(name+': '+str(e));print(traceback.format_exc(),flush=True);return None
        finally:write('functional-result.json',report)
    def audio_result(data,name):
        if not data.get('success') or not data.get('audio_data'):raise RuntimeError(str(data)[:1800])
        audio=base64.b64decode(data['audio_data']);path=args.reports/name;path.write_bytes(audio)
        samples,rate=sf.read(path,dtype='float32');duration=len(samples)/rate
        if not np.isfinite(samples).all() or duration<.25 or np.max(np.abs(samples))<1e-4:raise RuntimeError('Invalid, empty or silent audio output')
        upload(path)
        return {'file':str(path),'bytes':len(audio),'sha256':hashlib.sha256(audio).hexdigest(),'sample_rate':rate,'duration':round(duration,4),'peak':float(np.max(np.abs(samples))),'rms':float(np.sqrt(np.mean(samples**2))),'processing_time':data.get('processing_time')}
    def synth(version,language='zh',trained=False):
        pretrained=args.root/'app/GPT_SoVITS/pretrained_models'
        loaded=api('POST','/inference/models/load',data={'gpt_path':str(args.assets/'trained/gpt.ckpt') if trained else str(pretrained/'s1v3.ckpt'),'sovits_path':str(args.assets/'trained/sovits.pth') if trained else str(pretrained/f'gsv-v5-pretrained/s2G{version}.pth')})
        sample=json.loads((args.assets/'trained/reference.json').read_text(encoding='utf-8')) if trained else json.loads((args.assets/'samples.json').read_text(encoding='utf-8'))[-1]
        text='你好，这是语音合成测试。' if language=='zh' else 'This is a voice test.'
        with (args.assets/sample['file']).open('rb') as f:
            result=api('POST','/inference/tts',data={'text':text,'text_language':language,'prompt_text':sample['text'],'prompt_language':'zh','seed':2027,'return_base64':'true'},files={'ref_audio':(sample['file'],f,'audio/wav')})
        info=audio_result(result,('trained-' if trained else '')+f'{version}-{language}.wav');info['model_info']=api('GET','/inference/models/info');api('POST','/inference/models/unload');return info
    def asr(path):
        with path.open('rb') as f:result=api('POST','/inference/transcribe',data={'language':'zh','precision':'float32','model_type':'funasr','model_size':'large'},files={'audio_file':(path.name,f,'audio/wav')})
        if not result.get('success') or not result.get('text','').strip():raise RuntimeError(str(result))
        api('POST','/inference/transcribe/models/unload');return result
    def options(**updates):
        return dict({'project_name':args.project_name,'world_name':'功能验收世界','version':'v5turbo','role_mode':'new','preprocessing_mode':'full','training_mode':'fresh','language':'zh','train_gpt':True,'train_sovits':True,'training_order':'sovits_first','gpt_batch_size':1,'sovits_batch_size':1,'gpt_total_epoch':1,'sovits_total_epoch':1,'save_every_epoch':1,'lora_rank':8,'log_interval':1,'grad_checkpoint':False,'fp16':args.mode=='linux-gpu','gpu_numbers':'0','publish_models':True},**updates)
    def train(opt):
        if args.existing_workflow:
            record=api('GET','/training/workbench/runs/'+args.existing_workflow);args.existing_workflow=''
        else:
            try:api('POST','/api/world/create/',json={'name':opt['world_name'],'version':opt['version']})
            except RuntimeError as e:
                if '已存在' not in str(e):raise
            with ExitStack() as stack:
                files=[] if opt['training_mode']=='resume' else [('audio_files',(f.name,stack.enter_context(f.open('rb')),'audio/wav')) for f in sorted(args.assets.glob('*.wav'))]
                record=api('POST','/training/workbench/start',data={'options':json.dumps(opt,ensure_ascii=False)},files=files)['training_workflow']
        workflow=record['workflow_id'];write('latest-workflow.json',record);deadline=time.monotonic()+3600;last=None
        while time.monotonic()<deadline:
            record=api('GET','/training/workbench/runs/'+workflow);write('latest-workflow.json',record)
            key=(record['status'],record['phase'],record.get('current_stage'),record.get('current_target'))
            if key!=last:progress('training-progress',workflow=workflow,status=key);last=key
            if record['status'] in ['completed','failed','stopped','interrupted']:break
            time.sleep(5)
        if record['status']!='completed':
            for target in record['targets']:
                try:write('training-'+target['target']+'-error-log.json',api('GET',f'/training/workbench/runs/{workflow}/logs?target='+target['target']))
                except Exception:pass
            raise RuntimeError('Training did not complete: '+json.dumps(record,ensure_ascii=False)[-3500:])
        write(workflow+'.json',record)
        for target in record['targets']:
            model=Path(target['model'])
            if not model.is_file() or model.stat().st_size<1000:raise RuntimeError('Missing exported checkpoint: '+str(model))
            target['export_bytes']=model.stat().st_size
        return record
    try:
        import torch
        report['runtime']={'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
        if args.mode=='windows-cpu':assert os.name=='nt' and not torch.cuda.is_available()
        else:assert os.name=='posix' and torch.cuda.is_available()
        health=api('GET','/health');assert health['healthy_services']==health['total_services']==8;report['health']=health
        if args.mode=='windows-cpu':
            check('v5turbo-chinese-synthesis',lambda:synth('v5turbo'))
            check('v5turbo-english-synthesis',lambda:synth('v5turbo','en'))
            check('v5dev-chinese-synthesis',lambda:synth('v5dev'))
            trained_audio=check('trained-v5turbo-chinese-synthesis',lambda:synth('v5turbo',trained=True))
            if trained_audio:check('trained-audio-asr-roundtrip',lambda:asr(Path(trained_audio['file'])))
            check('chinese-asr',lambda:asr(args.assets/'sample_03.wav'))
            def rejected_gpu():
                r=session.post(args.backend+'/training/workbench/start',data={'options':json.dumps(options(),ensure_ascii=False)},timeout=30)
                if r.status_code!=400 or 'GPU' not in r.text:raise RuntimeError('Missing CUDA must be rejected clearly: '+r.text)
                return {'status':r.status_code,'response':r.json()}
            check('training-without-cuda-is-rejected',rejected_gpu)
        else:
            fresh=check('full-preprocessing-and-both-training-targets',lambda:train(options()))
            if fresh:
                latest=fresh
                if args.resume:latest=check('resume-both-training-targets',lambda:train(options(role_mode='existing',training_mode='resume',resume_workspace=fresh['project_root'],preprocessing_mode='cached',gpt_total_epoch=2,sovits_total_epoch=2))) or fresh
                def preview():
                    result=api('POST','/training/workbench/runs/'+latest['workflow_id']+'/preview',json={'text':'你好，这是训练后的试听。','emotion':latest['preview']['emotions'][0]['name'],'seed':2027})
                    return audio_result(result,'trained-v5turbo-preview.wav')
                audio=check('reload-trained-weights-and-synthesize',preview)
                if audio:check('trained-audio-asr-roundtrip',lambda:asr(Path(audio['file'])))
        report['success']=bool(report['checks']) and not report['errors']
    except Exception as e:report['errors'].append(str(e));report['traceback']=traceback.format_exc();print(traceback.format_exc(),flush=True)
    finally:
        report['finished_at']=datetime.now().astimezone().isoformat();write('functional-result.json',report);progress('finished',success=report['success'],errors=report['errors'])
    return 0 if report['success'] else 1

if __name__=='__main__':raise SystemExit(main())
