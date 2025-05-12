#!/bin/bash

BASEDIR="/home/telofarm"

echo "📥 Django 코드 업데이트"
cd "$BASEDIR/telofarmer_django" || { echo "❌ 디렉토리 이동 실패 (telofarmer_django)"; exit 1; }
git pull || { echo "❌ git pull 실패 (Django)"; exit 1; }

echo "📥 Controller 코드 업데이트"
cd "$BASEDIR/controller_project" || { echo "❌ 디렉토리 이동 실패 (controller_project)"; exit 1; }
git pull || { echo "❌ git pull 실패 (Controller)"; exit 1; }

echo "📥 Scripts 폴더 업데이트"
cd "$BASEDIR/scripts" || { echo "❌ 디렉토리 이동 실패 (scripts)"; exit 1; }
git pull || { echo "❌ git pull 실패 (Scripts)"; exit 1; }

echo "🔁 Daphne 서비스 재시작"
sudo systemctl restart telofarm-daphne

echo "🔁 Controller 서비스 재시작"
sudo systemctl restart telofarm-controller

echo "✅ 전체 코드 업데이트 및 서비스 재시작 완료 (cloudflared는 건드리지 않음)"
