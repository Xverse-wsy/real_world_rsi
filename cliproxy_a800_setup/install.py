"""Install an official CLIProxyAPI release without changing the source checkout."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import tarfile


BASE = Path('/home/wenchaoxu/wsy/CLIProxyAPI')
VERSION = '8.0.33'
PROXY = 'http://127.0.0.1:20171'
SETUP = BASE / '.setup'
ARCHIVE = f'CLIProxyAPI_{VERSION}_linux_amd64.tar.gz'


def download(name):
    target = SETUP / name
    subprocess.run(['curl', '--fail', '--location', '--show-error',
                    '--proxy', PROXY, '--noproxy', '', '--connect-timeout', '10',
                    '--max-time', '180', '--retry', '2', '--output', str(target),
                    f'https://github.com/router-for-me/CLIProxyAPI/releases/download/v{VERSION}/{name}'], check=True)
    return target


def private_write(path, text, executable=False):
    with path.open('x') as stream:
        stream.write(text)
    path.chmod(0o700 if executable else 0o600)


def main():
    os.umask(0o077)
    SETUP.mkdir(exist_ok=True)
    exclude = BASE / '.git/info/exclude'
    existing = exclude.read_text() if exclude.exists() else ''
    additions = [name for name in ('/.setup/', '/bin/') if name not in existing.splitlines()]
    if additions:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open('a') as stream:
            stream.write('\n' + '\n'.join(additions) + '\n')
    if (BASE / 'config.yaml').exists():
        raise FileExistsError('Preserve existing config.yaml; inspect before changing it')
    checksums = download('checksums.txt')
    archive = download(ARCHIVE)
    expected = None
    for line in checksums.read_text().splitlines():
        columns = line.split()
        if len(columns) >= 2 and columns[-1].lstrip('*') == ARCHIVE:
            expected = columns[0]
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected is None or actual != expected:
        raise ValueError('Official release checksum verification failed')
    destination = BASE / 'bin' / VERSION
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, 'r:gz') as tar:
        candidates = [m for m in tar.getmembers() if m.isfile()
                      and Path(m.name).name.lower() in {'cli-proxy-api', 'cliproxyapi'}]
        if len(candidates) != 1:
            raise ValueError('Expected one CLIProxyAPI executable')
        binary = destination / 'cli-proxy-api'
        binary.write_bytes(tar.extractfile(candidates[0]).read())
        binary.chmod(0o700)
    auth = BASE / 'auths'
    auth.mkdir(exist_ok=True)
    auth.chmod(0o700)
    key = 'cpa-' + secrets.token_urlsafe(32)
    config = f'''config-version: 8
server:
  host: "127.0.0.1"
  port: 8317
management:
  allow-remote: false
  secret-key: ""
  disable-control-panel: true
access:
  api-keys:
    - "{key}"
requests:
  proxy-url: "{PROXY}"
oauth:
  auth-dir: "{auth}"
observability:
  logs:
    debug: false
    logging-to-file: false
    request-log: false
'''
    private_write(BASE / 'config.yaml', config)
    private_write(SETUP / 'client.env',
                  'export OPENAI_BASE_URL=http://127.0.0.1:8317/v1\n'
                  f'export OPENAI_API_KEY={shlex.quote(key)}\n')
    prefix = '#!/usr/bin/env bash\nset -euo pipefail\n'
    prefix += 'cd ' + shlex.quote(str(BASE)) + '\n'
    for name, value in dict(HTTP_PROXY=PROXY, HTTPS_PROXY=PROXY,
                            ALL_PROXY=PROXY, NO_PROXY='localhost,127.0.0.1,::1').items():
        prefix += 'export ' + name + '=' + shlex.quote(value) + '\n'
    command = [str(binary), '--config', str(BASE / 'config.yaml')]
    private_write(SETUP / 'start.sh', prefix + shlex.join(command)
                  + ' 2>&1 | tee -a ' + shlex.quote(str(SETUP / 'server.log')) + '\n', True)
    private_write(SETUP / 'login_codex.sh', prefix + 'exec '
                  + shlex.join(command + ['--codex-device-login', '--no-browser']) + '\n', True)
    private_write(SETUP / 'installation.json', json.dumps(dict(
        version=VERSION, archive_sha256=actual, binary=str(binary),
        listen='127.0.0.1:8317', proxy=PROXY,
        client_environment=str(SETUP / 'client.env'),
        oauth_completed=False), indent=2) + '\n')
    subprocess.run(['screen', '-dmS', 'cliproxyapi_server',
                    'bash', str(SETUP / 'start.sh')], check=True)
    print(json.dumps(dict(installed=True, version=VERSION,
                          checksum_verified=True, screen='cliproxyapi_server',
                          config=str(BASE / 'config.yaml'),
                          client_key_saved=True, client_key_printed=False)), flush=True)


if __name__ == '__main__':
    main()
