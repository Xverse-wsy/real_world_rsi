"""API outage handling without model calls or simulator dependencies."""
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest

spec=importlib.util.spec_from_file_location('api_pause',Path(__file__).resolve().parents[1]/'capx/llm/api_pause.py')
pause=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pause)


class FakeApiError(Exception):
    status_code=429
    body={'error':{'code':'insufficient_quota','type':'quota'}}


class ApiPauseTests(unittest.TestCase):
    def test_three_retries_then_manual_resume_same_pending_request(self):
        with tempfile.TemporaryDirectory() as temp:
            gate=pause.ApiPauseGate(temp,retry_delays=(.001,)*3,poll_seconds=.002,log=lambda _:None)
            calls=[]
            result=[]
            payload={'messages':['original request']}
            def operation():
                calls.append(payload)
                if len(calls)<=4:raise FakeApiError('secret must never be logged')
                return 'code to execute once'
            worker=threading.Thread(target=lambda:result.append(gate.call(operation,retryable=(FakeApiError,))),daemon=True)
            worker.start()
            status=Path(temp)/'status.json'
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                if status.exists() and json.loads(status.read_text())['phase']=='paused':break
                time.sleep(.005)
            self.assertEqual(json.loads(status.read_text())['phase'],'paused')
            self.assertEqual(len(calls),4)
            for malformed in ([],None,False,23,'resume'):
                pause.write_json(Path(temp)/'resume.json',malformed)
                time.sleep(.01)
                self.assertTrue(worker.is_alive())
                self.assertEqual(len(calls),4)
            # An old resume signal must not accidentally authorize another cycle.
            pause.write_json(Path(temp)/'resume.json',{'pause_id':'stale-token'})
            time.sleep(.05)
            self.assertTrue(worker.is_alive())
            self.assertEqual(len(calls),4)
            pause.resume(temp)
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result,['code to execute once'])
            self.assertEqual(len(calls),5)
            self.assertTrue(all(value is payload for value in calls))
            self.assertNotIn('secret', (Path(temp)/'events.jsonl').read_text())

    def test_successful_first_call_returns_original_object_once(self):
        with tempfile.TemporaryDirectory() as temp:
            events=[]
            calls=[]
            expected=object()
            gate=pause.ApiPauseGate(temp,on_wait=events.append,log=lambda _:None)
            def operation():
                calls.append(1)
                return expected
            self.assertIs(gate.call(operation,retryable=(FakeApiError,)),expected)
            self.assertEqual((len(calls),events),(1,['begin','end']))
            states=[json.loads(line)['phase'] for line in (Path(temp)/'events.jsonl').read_text().splitlines()]
            self.assertEqual(states,['requesting','ready'])

    def test_missing_credential_file_can_be_repaired_while_paused(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)/'control'
            key=Path(temp)/'key'
            gate=pause.ApiPauseGate(directory,retry_delays=(0,0,0),poll_seconds=.002,log=lambda _:None)
            result=[]
            worker=threading.Thread(target=lambda:result.append(gate.call(
                lambda:pause.read_api_key(key),retryable=(pause.ApiCredentialsError,))),daemon=True)
            worker.start()
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                try:state=json.loads((directory/'status.json').read_text())
                except (OSError,ValueError):state={}
                if state.get('phase')=='paused':break
                time.sleep(.005)
            self.assertEqual(state.get('phase'),'paused')
            key.write_text('replacement-test-key')
            pause.resume(directory)
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result,['replacement-test-key'])
            self.assertNotIn('replacement-test-key',(directory/'events.jsonl').read_text())

    def test_invalid_credential_files_and_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            key=Path(temp)/'key'
            for content in (b'',b'  ',b'\xff'):
                key.write_bytes(content)
                with self.assertRaises(pause.ApiCredentialsError):pause.read_api_key(key)
            for delays in ((0,0),(-1,0,0),(float('nan'),0,0)):
                with self.assertRaises(ValueError):pause.ApiPauseGate(temp,retry_delays=delays)

    def test_failed_manual_resume_blocks_again_with_a_new_token(self):
        with tempfile.TemporaryDirectory() as temp:
            gate=pause.ApiPauseGate(temp,retry_delays=(0,0,0),poll_seconds=.002,log=lambda _:None)
            calls=[];result=[];fixed=threading.Event()
            def operation():
                calls.append(1)
                if not fixed.is_set():raise FakeApiError()
                return 'one response'
            worker=threading.Thread(target=lambda:result.append(gate.call(operation,retryable=(FakeApiError,))),daemon=True)
            worker.start()
            def wait_for_pause(cycle):
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    try:state=json.loads((Path(temp)/'status.json').read_text())
                    except (OSError,ValueError):state={}
                    if state.get('phase')=='paused' and state.get('cycle')==cycle:return state
                    time.sleep(.005)
                self.fail('Request never paused')
            first=wait_for_pause(1)
            pause.resume(temp)
            second=wait_for_pause(2)
            self.assertEqual(len(calls),8)
            self.assertEqual(first['request_id'],second['request_id'])
            self.assertNotEqual(first['pause_id'],second['pause_id'])
            pause.write_json(Path(temp)/'resume.json',{'pause_id':first['pause_id']})
            time.sleep(.02)
            self.assertEqual(len(calls),8)
            fixed.set();pause.resume(temp);worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual((len(calls),result),(9,['one response']))

    def test_successful_retry_needs_no_manual_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            events=[]
            gate=pause.ApiPauseGate(temp,retry_delays=(0,0,0),on_wait=events.append,log=lambda _:None)
            count=0
            def operation():
                nonlocal count
                count+=1
                if count<3:raise FakeApiError()
                return 42
            self.assertEqual(gate.call(operation,retryable=(FakeApiError,)),42)
            self.assertEqual((count,events),(3,['begin','end']))
            self.assertEqual(json.loads((Path(temp)/'status.json').read_text())['phase'],'ready')

    @unittest.skipUnless(hasattr(signal,'setitimer'),'POSIX timer required')
    def test_trial_alarm_is_suspended_and_remaining_budget_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            original=signal.getitimer(signal.ITIMER_REAL)
            gate=pause.ApiPauseGate(temp,log=lambda _:None)
            signal.setitimer(signal.ITIMER_REAL,.2)
            try:
                gate.call(lambda:time.sleep(.3),retryable=(FakeApiError,))
                remaining=signal.getitimer(signal.ITIMER_REAL)[0]
                self.assertGreater(remaining,.12)
            finally:
                signal.setitimer(signal.ITIMER_REAL,*original)

    def test_programming_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            gate=pause.ApiPauseGate(temp,log=lambda _:None)
            with self.assertRaises(ValueError):
                gate.call(lambda:(_ for _ in ()).throw(ValueError()),retryable=(FakeApiError,))


if __name__=='__main__':unittest.main()
