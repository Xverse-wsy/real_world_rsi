set -euo pipefail
source .setup/env.sh
mkdir -p .setup/vendor
for spec in chungmin99/pyroki/95afccc22658c461ab1042a048ae4e9c24bc2a47 brentyi/jaxls/6fe7cf9d56223736b2c0272d080ec7346203c648; do
  repo=${spec%/*}; commit=${spec##*/}; name=${repo##*/}
  curl -fsSL --retry 5 --connect-timeout 20 --max-time 180 "https://codeload.github.com/$repo/tar.gz/$commit" -o ".setup/archives/$commit.tar.gz"
  mkdir -p ".setup/vendor/$name"
  tar -xzf ".setup/archives/$commit.tar.gz" --strip-components=1 -C ".setup/vendor/$name"
done
uv export --frozen --extra libero --extra contactgraspnet --no-hashes --no-emit-project -o .setup/requirements.lock.txt
python3 - <<'PY'
p='.setup/requirements.lock.txt'; s=open(p).read()
s=s.replace('git+https://github.com/chungmin99/pyroki.git@95afccc22658c461ab1042a048ae4e9c24bc2a47','file:///home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.setup/vendor/pyroki')
s=s.replace('git+https://github.com/brentyi/jaxls.git@6fe7cf9d56223736b2c0272d080ec7346203c648','file:///home/wenchaoxu/wsy/vla-recovery-posttrain-loop/cap-x/.setup/vendor/jaxls')
open('.setup/requirements.local.txt','w').write(s)
PY
