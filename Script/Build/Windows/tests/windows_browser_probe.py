"""Exercise real Windows Edge UI against the portable backend using CDP."""
import argparse,base64,json,os,shutil,subprocess,time,traceback
from pathlib import Path
import requests
from websockets.sync.client import connect

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--reports',type=Path,required=True);p.add_argument('--endpoint',required=True);args=p.parse_args()
r=requests.Session();r.trust_env=False;api='http://127.0.0.1:40302';assets=args.reports/'qa-assets/trained';result={'success':False,'platform':'Windows Edge','errors':[]}
def upload(path):
    with path.open('rb') as f:r.put(args.endpoint+'/reports/'+path.name,data=f,timeout=20).raise_for_status()
def post(path,**kw):
    res=r.post(api+path,timeout=60,**kw);res.raise_for_status();return res.json()
try:
    world='Windows验收世界';role='Windows验收角色'
    try:post('/api/world/create/',json={'name':world,'version':'v5turbo'})
    except requests.HTTPError as error:
        if '已存在' not in error.response.text:raise
    ref=json.loads((assets/'reference.json').read_text(encoding='utf-8'))
    existing=r.get(api+'/api/role/list/',params={'world_name':world,'version':'v5turbo'},timeout=30).json()['roles']
    role_id=next((x['id'] for x in existing if x['name']==role),None)
    if role_id is None:role_id=post('/api/role/create/',json={'name':role,'world_name':world,'version':'v5turbo','language':'zh'})['data']['id']
    model=args.root/'app/Resources/Model'/world/role/'v5turbo'
    for folder,file in [('GPT','gpt.ckpt'),('SoVITS','sovits.pth')]:
        target=model/folder;target.mkdir(parents=True,exist_ok=True);shutil.copy2(assets/file,target/file)
    with (assets/'reference.wav').open('rb') as f:post('/api/role/emotions/upsert/',data={'role_id':role_id,'emotion_name':'默认','emotion_text':ref['text'],'text_language':'zh'},files={'audio_file':('reference.wav',f,'audio/wav')})
    edge=Path(os.environ['ProgramFiles(x86)'])/'Microsoft/Edge/Application/msedge.exe'
    subprocess.Popen([str(edge),'--user-data-dir='+str(args.reports/'edge-test-profile'),'--remote-debugging-port=9222','--no-first-run','--no-default-browser-check','http://127.0.0.1:40031/'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(3)
    deadline=time.monotonic()+90;target=None
    while time.monotonic()<deadline:
        try:target=next(t for t in r.get('http://127.0.0.1:9222/json/list',timeout=2).json() if t['type']=='page' and '40031' in t['url']);break
        except Exception:time.sleep(1)
    if not target:raise RuntimeError('Edge did not expose the test page')
    with connect(target['webSocketDebuggerUrl'],max_size=8*1024**2) as ws:
        seq=0
        def command(method,params=None):
            global seq
            seq+=1;ident=seq;ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
            while True:
                data=json.loads(ws.recv(timeout=90))
                if data.get('id')==ident:
                    if 'error' in data:raise RuntimeError(str(data['error']))
                    return data.get('result',{})
        def js(code):
            data=command('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True,'userGesture':True})
            if data.get('exceptionDetails'):raise RuntimeError(str(data['exceptionDetails']))
            return data.get('result',{}).get('value')
        def wait(code,seconds=30):
            stop=time.monotonic()+seconds
            while time.monotonic()<stop:
                value=js(code)
                if value:return value
                time.sleep(.3)
            raise RuntimeError('Browser condition timed out: '+code)
        def click_contains(label):
            text=json.dumps(label,ensure_ascii=False)
            if not wait(f"(()=>{{const b=[...document.querySelectorAll('button')].find(b=>!b.disabled&&b.innerText.includes({text}));if(b){{b.click();return true}}return false}})()"):
                raise RuntimeError('Missing button: '+label)
        def choose(label,value):
            label_js=json.dumps(label,ensure_ascii=False);value_js=json.dumps(value,ensure_ascii=False)
            wait(f"(()=>{{const e=[...document.querySelectorAll('span')].find(e=>e.textContent.trim()==={label_js});if(e){{e.parentElement.click();return true}}return false}})()")
            wait(f"(()=>{{const e=[...document.querySelectorAll('.theme-dropdown-panel div.cursor-pointer')].find(e=>e.innerText.trim().startsWith({value_js}));if(e){{e.click();return true}}return false}})()")
            time.sleep(.7)
        command('Page.navigate',{'url':'http://127.0.0.1:40031/'})
        r.get('http://127.0.0.1:9222/json/activate/'+target['id'],timeout=5)
        command('Page.bringToFront')
        time.sleep(1)
        window=command('Browser.getWindowForTarget')
        command('Browser.setWindowBounds',{'windowId':window['windowId'],'bounds':{'windowState':'maximized'}})
        wait("document.querySelector('textarea')&&[...document.querySelectorAll('span')].some(b=>b.textContent.trim()==='模型版本')")
        wait("document.body.innerText.includes('Windows验收角色')&&document.body.innerText.includes('v5turbo')")
        command('Page.bringToFront')
        wait("document.visibilityState==='visible'")
        js("window.__qaResult=null;window.__qaRequests=[];window.__qaOriginalFetch=window.__qaOriginalFetch||window.fetch;window.fetch=async(...a)=>{const r=await window.__qaOriginalFetch(...a);const u=String(a[0]?.url||a[0]);if(u.includes('/api/synthesis/')||u.includes('/inference/'))r.clone().json().then(d=>{window.__qaRequests.push({url:u,status:r.status,success:d.success,message:d.message});if(d.audio_data)window.__qaResult={http:r.status,...d}});return r;};const t=document.querySelector('textarea');t.focus();t.select();")
        command('Input.insertText',{'text':'你好，这是网页合成测试。'})
        wait("document.querySelector('textarea').value==='你好，这是网页合成测试。'")
        point=wait("(()=>{const b=[...document.querySelectorAll('button')].find(b=>!b.disabled&&b.textContent.includes('开始合成'));if(!b)return false;b.scrollIntoView({block:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        js("[...document.querySelectorAll('button')].find(b=>!b.disabled&&b.textContent.includes('开始合成')).click()")
        audio=wait('window.__qaResult',90)
        if not audio.get('success') or audio.get('http')!=200:raise RuntimeError(str(audio)[:1200])
        wav=args.reports/'windows-web-synthesis.wav';wav.write_bytes(base64.b64decode(audio['audio_data']));upload(wav)
        command('Page.bringToFront')
        wait("[...document.querySelectorAll('audio')].some(a=>a.readyState>=2&&a.duration>0)")
        js("(async()=>{const a=[...document.querySelectorAll('audio')].find(a=>a.readyState>=2&&a.duration>0);a.scrollIntoView({block:'center'});a.muted=true;await a.play();return true})()")
        time.sleep(.5);playback=js("(()=>{const a=[...document.querySelectorAll('audio')].find(a=>a.readyState>=2&&a.duration>0);const r=a.getBoundingClientRect();const d={duration:a.duration,currentTime:a.currentTime,readyState:a.readyState,error:a.error?.message||null,visible:r.top>=0&&r.bottom<=innerHeight,top:r.top,bottom:r.bottom,viewport_height:innerHeight};a.pause();return d})()")
        if not playback['currentTime']>0 or playback['error'] or not playback['visible']:raise RuntimeError('Playback failed: '+str(playback))
        downloads=args.reports/'browser-downloads';downloads.mkdir(exist_ok=True)
        for old in downloads.glob('*.wav'):old.unlink()
        command('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads)})
        point=wait("(()=>{const b=[...document.querySelectorAll('button')].find(b=>!b.disabled&&b.textContent.includes('下载音频'));if(!b)return false;b.scrollIntoView({block:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        js("[...document.querySelectorAll('button')].find(b=>!b.disabled&&b.textContent.includes('下载音频')).click()")
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            files=list(downloads.glob('*.wav'))
            if files:break
            time.sleep(.2)
        if not files:raise RuntimeError('The UI download did not produce a WAV file')
        import soundfile as sf
        downloaded=args.reports/'windows-ui-download.wav';shutil.copy2(files[0],downloaded);info=sf.info(str(downloaded));upload(downloaded)
        if info.samplerate!=audio['sample_rate'] or abs(info.duration-audio['duration'])>.05:raise RuntimeError('Downloaded audio differs from synthesis metadata')
        shot=args.reports/'windows-web-synthesis.png';shot.write_bytes(base64.b64decode(command('Page.captureScreenshot',{'format':'png'})['data']));upload(shot)
        result.update(success=True,browser=command('Browser.getVersion'),synthesis={'duration':audio['duration'],'sample_rate':audio['sample_rate'],'http':audio['http']},playback=playback,download={'filename':files[0].name,'bytes':downloaded.stat().st_size,'duration':info.duration,'sample_rate':info.samplerate},role_id=role_id)
except Exception as e:
    result['errors'].append(str(e));result['traceback']=traceback.format_exc();print(result['traceback'],flush=True)
finally:
    path=args.reports/'windows-browser-result.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');upload(path)
print(json.dumps(result,ensure_ascii=False),flush=True)
raise SystemExit(0 if result['success'] else 1)
