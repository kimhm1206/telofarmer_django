#!/bin/bash

BASEDIR="/home/telofarm"
USE_GUI=0

# DISPLAY 존재 여부로 GUI 환경 판단
if [ -n "$DISPLAY" ]; then
    USE_GUI=1
fi


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
if [ "$USE_GUI" -eq 1 ]; then
    lxterminal -t "Cloudflared" -e "bash -c 'cloudflared tunnel run --url http://localhost:8000 seongju'" &
else
    nohup cloudflared tunnel run --url http://localhost:8000 seongju &
fi

sleep 2

echo "🌀 daphne 실행"
if [ "$USE_GUI" -eq 1 ]; then
    lxterminal -t "Daphne" -e "bash -c 'cd $BASEDIR/telofarmer_django && daphne config.asgi:application'" &
else
    cd "$BASEDIR/telofarmer_django"
    nohup daphne config.asgi:application &
fi

sleep 2

echo "🐍 controller 실행"
if [ "$USE_GUI" -eq 1 ]; then
    lxterminal -t "Controller" -e "bash -c 'cd $BASEDIR/controller_project && python3 main.py'" &
else
    cd "$BASEDIR/controller_project"
    nohup python3 main.py &
fi

echo "✅ 모든 서비스 실행 완료"
