@echo off

REM 기준 경로 설정 (모든 코드가 여기에 있다고 가정)
set BASEDIR=%USERPROFILE%

echo 🔄 프로세스 종료
taskkill /f /im cloudflared.exe >nul 2>&1
taskkill /f /im daphne.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1

echo 📥 Django pull
cd /d "%BASEDIR%\telofarmer_django"
git pull

echo 📥 Controller pull
cd /d "%BASEDIR%\controller_project"
git pull

echo 📥 scripts pull
cd /d "%BASEDIR%\scripts"
git pull

echo 🚀 cloudflared 실행 (새 창 + 로그 보기)
start "cloudflared" cmd /k "cd /d %BASEDIR%\telofarmer_django && cloudflared tunnel run --url http://localhost:8000 gbatunnel"

timeout /t 1 > nul

echo 🌀 daphne 실행 (새 창 + 로그 보기)
start "daphne" cmd /k "cd /d %BASEDIR%\telofarmer_django && daphne config.asgi:application"

timeout /t 1 > nul

echo 🐍 controller main.py 실행 (새 창 + 로그 보기)
start "main.py" cmd /k "cd /d %BASEDIR%\controller_project && python main.py"

echo ✅ All components launched. 창들을 확인하세요.
pause