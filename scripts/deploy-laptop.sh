#!/usr/bin/env bash
# 메인 Mac 에서 실행: 번들 하나를 노트북(mbp2017) Prism 에 올리고 적재한다. Prism 코드는 건드리지 않는다.
#   scripts/deploy-laptop.sh build/dist/zoomtology-<version>.tar.gz
# 전제: AgentPrism kg 모듈이 노트북에 배포돼 있다(AgentPrism/scripts/deploy-laptop.sh, 1·4단계).
set -euo pipefail
HOST="${PRISM_LAPTOP_HOST:-mbp2017}"
BUNDLE="${1:?번들 경로를 주세요}"
NAME="$(basename "$BUNDLE")"
echo "TODO(ZDV-348): scp \"$BUNDLE\" \"$HOST:~/apps/agent-prism/var/kg/$NAME\" && ssh \"$HOST\" 'source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd ~/apps/agent-prism && node dist/kg/cli.js load var/kg/$NAME && node dist/kg/cli.js status'" >&2
exit 2
