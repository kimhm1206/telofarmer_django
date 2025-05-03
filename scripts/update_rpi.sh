#!/bin/bash

BASEDIR="/home/telofarm"

echo "🔄 Daphne 종료"
pkill -f "daphne config.asgi:application"

echo "🔄 Controller 종료"
pkill -f "python3 main.py"

echo "🔄 Cloudflared 종료"
pkill -f "cloudflared tunnel run"

echo "📥 Django pull"
cd "$BASEDIR/telofarmer_django" || exit 1
git pull

echo "📥 Controller pull"
cd "$BASEDIR/controller_project" || exit 1
git pull

echo "🚀 cloudflared 실행"
lxterminal -t "Cloudflared" -e "bash -c 'cloudflared tunnel run --url http://localhost:8000 seongju'" &

sleep 2

echo "🌀 daphne 실행"
lxterminal -t "Daphne" -e "bash -c 'cd $BASEDIR/telofarmer_django && daphne config.asgi:application'" &

sleep 2

echo "🐍 controller 실행"
lxterminal -t "Controller" -e "bash -c 'cd $BASEDIR/controller_project && python3 main.py'" &

echo "✅ 모든 서비스 실행 완료"
