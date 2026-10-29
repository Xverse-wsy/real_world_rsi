"""Retry API requests, then wait for an explicit resume without leaving the call."""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import json
import math
import os
from pathlib import Path
import signal
import sys
import threading
import time
import uuid


class IncompleteResponseError(RuntimeError):
    """A response cannot yet be used as an executable model reply."""


class ApiCredentialsError(RuntimeError):
    """A credential file needs repair; keep the pending request in memory."""


def read_api_key(path):
    try:
        key=Path(path).read_text().strip()
    except (OSError, UnicodeError) as exc:
        raise ApiCredentialsError('API key file is not readable') from exc
    if not key:
        raise ApiCredentialsError('API key file is empty')
    return key


def write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


@contextmanager
def suspend_trial_alarm():
    """Keep POSIX trial alarms from destroying the env during API waits."""
    enabled = hasattr(signal, 'setitimer') and threading.current_thread() is threading.main_thread()
    timer = signal.setitimer(signal.ITIMER_REAL, 0) if enabled else None
    try:
        yield
    finally:
        if enabled:
            signal.setitimer(signal.ITIMER_REAL, *timer)


def error_details(exc):
    # Deliberately omit exception text, headers, URLs and request bodies: they
    # may contain credentials or user content. Retain useful upstream codes.
    details = {'type': type(exc).__name__}
    status = getattr(exc, 'status_code', None)
    if isinstance(status, int):
        details['http_status'] = status
    body = getattr(exc, 'body', None)
    if isinstance(body, dict):
        error = body.get('error', body)
        if isinstance(error, dict):
            for field in ('code', 'type'):
                value = error.get(field)
                if isinstance(value, str) and len(value) <= 100:
                    details['upstream_' + field] = value
    return details


class ApiPauseGate:
    """One initial request + three retries; no requests after exhaustion until resume."""

    def __init__(self, directory, *, retry_delays=(5., 15., 30.), poll_seconds=1.,
                 on_wait=None, log=None):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.retry_delays = tuple(retry_delays)
        if len(self.retry_delays)!=3 or any(not math.isfinite(x) or x<0 for x in self.retry_delays):
            raise ValueError('Exactly three finite, nonnegative retry delays are required')
        if not math.isfinite(poll_seconds) or poll_seconds<=0:
            raise ValueError('Polling interval must be finite and positive')
        self.poll_seconds = poll_seconds
        self.on_wait = on_wait or (lambda event: None)
        self.log = log or (lambda text: print(text, file=sys.stderr, flush=True))
        self.request_id = None

    def _state(self, phase, **data):
        value = dict(phase=phase, pid=os.getpid(), request_id=self.request_id,
                     updated_at_utc=datetime.now(timezone.utc).isoformat(), **data)
        write_json(self.directory / 'status.json', value)
        with (self.directory / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(value) + '\n')
        return value

    def _manual_wait(self, **data):
        token = uuid.uuid4().hex
        state = self._state('paused', pause_id=token, **data)
        self.log(f'API PAUSED: simulator/process kept alive; control directory: {self.directory}')
        self.log(f'Resume after fixing API: python {Path(__file__).resolve()} resume {str(self.directory)!r}')
        control = self.directory / 'resume.json'
        while True:
            try:
                request = json.loads(control.read_text())
            except (OSError, ValueError):
                request = {}
            if not isinstance(request,dict):
                request = {}
            if request.get('pause_id') == token:
                control.unlink(missing_ok=True)
                self._state('resuming', pause_id=state['pause_id'])
                self.log('API resume accepted; retrying the same pending request.')
                return
            time.sleep(self.poll_seconds)

    def call(self, operation, *, retryable):
        self.request_id = uuid.uuid4().hex
        started = False
        with suspend_trial_alarm():
            try:
                # Hybrid parent acknowledges this message and suspends its own
                # deadline before the first HTTP request, including retry time.
                self.on_wait('begin')
                started = True
                cycle = 0
                while True:
                    cycle += 1
                    for attempt in range(1, len(self.retry_delays) + 2):
                        self._state('requesting', cycle=cycle, attempt=attempt)
                        try:
                            result = operation()
                        except retryable as exc:
                            details = error_details(exc)
                            self.log(f'API attempt {attempt}/{len(self.retry_delays)+1} failed: {json.dumps(details)}')
                            if attempt <= len(self.retry_delays):
                                delay = self.retry_delays[attempt - 1]
                                self._state('retry_wait', cycle=cycle, attempt=attempt,
                                            delay_seconds=delay, error=details)
                                time.sleep(delay)
                            else:
                                self._manual_wait(cycle=cycle, attempts=attempt, error=details)
                        else:
                            self._state('ready', cycle=cycle, attempt=attempt)
                            return result
            except BaseException as exc:
                self._state('interrupted', error=error_details(exc))
                raise
            finally:
                if started:
                    self.on_wait('end')


def resume(directory):
    directory = Path(directory).resolve()
    status = json.loads((directory / 'status.json').read_text())
    if not isinstance(status,dict):
        raise ValueError('Invalid API control status')
    if status.get('phase') != 'paused':
        raise ValueError(f"Request is not paused (phase={status.get('phase')})")
    if not isinstance(status.get('pause_id'),str) or not status['pause_id']:
        raise ValueError('Paused request has no valid resume token')
    if type(status.get('pid')) is not int or status['pid']<=0:
        raise ValueError('Paused request has no valid process ID')
    os.kill(status['pid'], 0)
    write_json(directory / 'resume.json', {'pause_id': status['pause_id']})
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'resume'])
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.command == 'resume':
        resume(args.directory)
        print('Resume signal sent. The existing process will retry its pending API request.')
    else:
        print((args.directory / 'status.json').read_text())


if __name__ == '__main__':
    main()
