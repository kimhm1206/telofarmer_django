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

echo "🚀 시스템 업데이트 완료, Telofarm 서비스 시작"

# start.sh를 완전히 백그라운드에서 실행
nohup bash "$BASEDIR/scripts/start.sh" >/dev/null 2>&1 &

echo "✅ 모든 서비스 실행 완료"
