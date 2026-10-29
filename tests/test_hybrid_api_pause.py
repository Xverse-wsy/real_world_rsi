"""Exercise the real parent RPC loop with a lightweight subprocess, no models."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

DIRECTORY=Path(__file__).resolve().parents[1]/'wcm_pi05_monitor/hybrid'
if not DIRECTORY.is_dir():
    DIRECTORY=Path(__file__).resolve().parents[2]/'wcm_pi05_monitor/hybrid'
package=types.ModuleType('_hybrid_pause_tests')
package.__path__=[str(DIRECTORY)]
sys.modules[package.__name__]=package
wire=types.ModuleType(package.__name__+'.wire')
def send(stream,value):
    stream.write(json.dumps(value)+'\n');stream.flush()
def receive(stream):
    line=stream.readline()
    if not line:raise EOFError('Worker exited')
    return json.loads(line)
wire.send,wire.receive=send,receive
sys.modules[wire.__name__]=wire
spec=importlib.util.spec_from_file_location(package.__name__+'.recovery',DIRECTORY/'recovery.py')
recovery=importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)

WORKER='''import json,sys,time
def send(message):
    print(json.dumps(message),flush=True)
def receive():
    line=sys.stdin.readline()
    if not line:raise EOFError('parent closed')
    return json.loads(line)
request=receive()
mode=sys.argv[1]
if mode!='normal':
    send(dict(kind='api_wait',event='begin'));receive()
    if mode=='exit':sys.exit(0)
    if mode=='illegal_call':
        send(dict(kind='call',method='step',args={}));sys.exit(0)
    if mode=='illegal_result':
        send(dict(kind='result',result={}));sys.exit(0)
    if mode=='mutated_scene':
        send(dict(kind='api_wait',event='end'));sys.exit(0)
    time.sleep(1.2)
    send(dict(kind='api_wait',event='end'));receive()
    if mode=='active_timeout':time.sleep(1.2)
send(dict(kind='call',method='step',args={}))
result=receive()
send(dict(kind='result',result=result))
'''


class Environment:
    def __init__(self):
        self.instruction='test';self.home=[];self.last_gripper=-1
        self.env=types.SimpleNamespace(sim=object())
        self.control=types.SimpleNamespace(steps=0,counts={'pi05':0,'capx':0},owner='capx',handoff={})
    def fingerprint(self):return str(self.control.steps)
    def dispatch(self,method,args):
        self.control.steps+=1
        self.control.counts['capx']+=1
        return {'steps':self.control.steps}


class ParentApiPauseTests(unittest.TestCase):
    def run_worker(self,mode,env,directory):
        script=Path(directory)/'worker.py';script.write_text(WORKER)
        real_popen=subprocess.Popen
        def launch(_command,**kwargs):
            kwargs['cwd']=directory
            return real_popen([sys.executable,str(script),mode],**kwargs)
        with patch.object(recovery.subprocess,'Popen',side_effect=launch):
            return recovery.recover(env,Path(directory)/'output',mode='scripted',timeout=1)

    def test_normal_worker_runs_action_once_without_pause(self):
        with tempfile.TemporaryDirectory() as temp:
            env=Environment()
            result=self.run_worker('normal',env,temp)
            self.assertEqual(result,{'result':{'steps':1}})
            self.assertEqual(env.control.steps,1)
            self.assertFalse((Path(temp)/'output/api_wait_events.jsonl').exists())

    def test_pause_longer_than_budget_preserves_state_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp:
            env=Environment()
            self.run_worker('pause',env,temp)
            events=[json.loads(line) for line in (Path(temp)/'output/api_wait_events.jsonl').read_text().splitlines()]
            self.assertEqual(events[0]['state'],events[1]['state'])
            self.assertTrue(events[1]['state_unchanged'])
            self.assertEqual(env.control.steps,1)

    def test_execution_deadline_still_fires_after_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            env=Environment()
            with self.assertRaises(TimeoutError):self.run_worker('active_timeout',env,temp)
            self.assertEqual(env.control.steps,0)

    def test_worker_exit_during_pause_does_not_hang(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(EOFError):self.run_worker('exit',Environment(),temp)

    def test_calls_and_results_cannot_bypass_pause(self):
        for mode in ('illegal_call','illegal_result'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                env=Environment()
                with self.assertRaises(RuntimeError):self.run_worker(mode,env,temp)
                self.assertEqual(env.control.steps,0)

    def test_changed_scene_is_rejected_before_any_action(self):
        with tempfile.TemporaryDirectory() as temp:
            env=Environment()
            original_send=recovery.send
            def change_state_after_snapshot(stream,message):
                if message.get('api_wait')=='begin':env.last_gripper=1
                original_send(stream,message)
            with patch.object(recovery,'send',side_effect=change_state_after_snapshot):
                with self.assertRaisesRegex(RuntimeError,'state changed'):
                    self.run_worker('mutated_scene',env,temp)
            self.assertEqual(env.control.steps,0)


if __name__=='__main__':unittest.main()
