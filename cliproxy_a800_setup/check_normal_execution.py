"""Run a real one-episode entrypoint against a deterministic local API stub."""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import io
from pathlib import Path
import runpy
import sys
import threading
import time


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path('/home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x')
    sys.path.insert(0,str(root))
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    code="for _ in range(8): env._step_once()\nprint('NORMAL_CODE_ONCE')"
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,body):
            data=json.dumps(body).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            self.reply(dict(id='gpt-6.1-sol',object='model',created=0,owned_by='local-test'))
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            images=[]
            def without_images(value):
                if isinstance(value,dict):return {k:without_images(v) for k,v in value.items()}
                if isinstance(value,list):return [without_images(v) for v in value]
                if isinstance(value,str) and value.startswith('data:image/'):
                    from PIL import Image
                    image=Image.open(io.BytesIO(base64.b64decode(value.split(',',1)[1]))).convert('RGB')
                    name=f'request_{len(requests):02d}_image_{len(images):02d}.png'
                    image.save(output/name)
                    images.append(name)
                    return dict(image_index=len(images)-1,image_size=list(image.size))
                return value
            normalized=without_images(body)
            requests.append(dict(path=self.path,sha256=digest(json.dumps(body,sort_keys=True).encode()),
                non_image_sha256=digest(json.dumps(normalized,sort_keys=True).encode()),images=images))
            text='```python\n'+code+'\n```' if len(requests)==1 else 'FINISH'
            self.reply(dict(id='resp_normal_test',object='response',created_at=int(time.time()),
                status='completed',model=body['model'],output=[dict(type='message',id='msg_normal_test',
                status='completed',role='assistant',content=[dict(type='output_text',text=text,annotations=[])])]))
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    os.environ['OPENAI_BASE_URL']=f'http://127.0.0.1:{server.server_port}/v1'
    os.environ['OPENAI_API_KEY']='local-test-only-no-upstream'
    os.environ['NO_PROXY']=os.environ['no_proxy']='127.0.0.1,localhost'
    import yaml
    config=yaml.safe_load((root/'env_configs/libero/franka_libero_spatial_0.yaml').read_text())
    config['api_servers']=[]
    path=output/'config.yaml';path.write_text(yaml.safe_dump(config,sort_keys=False))
    from capx.envs.tasks.base import CodeExecutionEnvBase
    original_reset,original_step=CodeExecutionEnvBase.reset,CodeExecutionEnvBase.step
    states=[]
    instances=[]
    def snapshot(env,label):
        low=env.low_level_env;sim=low.handle.env.sim
        states.append(dict(label=label,physical_sha256=digest(sim.get_state().flatten().tobytes()+sim.data.ctrl.tobytes()),
            code_steps=env._step_count,control_steps=low._sim_step_count))
    def reset(env,*args,**kwargs):
        result=original_reset(env,*args,**kwargs)
        instances.append(env);snapshot(env,'after_reset')
        return result
    def step(env,code):
        result=original_step(env,code);snapshot(env,'after_code')
        assert result[-1]['sandbox_rc']==0,result[-1]
        return result
    CodeExecutionEnvBase.reset,CodeExecutionEnvBase.step=reset,step
    try:
        runner=runpy.run_path(str(args.runner.resolve()),run_name='_normal_api_check')
        sys.argv=[str(args.runner),'--model','gpt-6.1-sol','--reasoning-effort','medium',
            '--prompt-profile','original','--config-path',str(path),'--output-dir',str(output/'episode')]
        runner['main']()
        assert len(requests)==2,requests
        assert len(states)==2,states
        assert states[-1]['control_steps']-states[0]['control_steps']==8 and states[-1]['code_steps']==1,states
        report=dict(local_mock_only=True,external_api_requests=0,api_calls=2,code_executions=1,
            requests=requests,states=states,code_sha256=digest(code.encode()))
        (output/'report.json').write_text(json.dumps(report,indent=2))
        print('NORMAL_EXECUTION_PASS',output,flush=True)
    finally:
        CodeExecutionEnvBase.reset,CodeExecutionEnvBase.step=original_reset,original_step
        for env in instances:env.close()
        server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':main()
