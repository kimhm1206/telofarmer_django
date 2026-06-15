@chcp 65001 >nul
@echo off

echo 🛑 cloudflared 종료
taskkill /f /im cloudflared.exe >nul 2>&1
if %errorlevel%==0 (
    echo ✅ cloudflared 종료됨
) else (
    echo ⚠️ cloudflared 프로세스 없음
)

echo 🛑 main.py 종료 시도 중...

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Output '✅ main.py 종료됨' }"

if %errorlevel% neq 0 (
    echo ⚠️ main.py 프로세스를 찾을 수 없거나 이미 종료됨
)

echo 🛑 daphne 종료
for /f "tokens=2 delims=," %%i in ('tasklist /v /fo csv ^| findstr /i "daphne"') do (
    taskkill /f /pid %%i >nul
    echo ✅ daphne 종료됨
)

setlocal

:: 기준 디렉토리 설정
set "BASEDIR=%USERPROFILE%\Documents"

echo 📥 telofarmer_django pull
cd "%BASEDIR%\telofarmer_django" || (
    echo ❌ 디렉토리 없음
    exit /b 1
)
git pull

echo 📥 controller_project pull
cd "%BASEDIR%\controller_project" || (
    echo ❌ 디렉토리 없음
    exit /b 1
)
git pull

echo 📥 scripts pull
cd "%BASEDIR%\scripts" || (
    echo ❌ 디렉토리 없음
    exit /b 1
)
git pull

echo 📦 Python requirements 업데이트
python -m pip install -r "%BASEDIR%\telofarmer_django\requirements.txt"
if %errorlevel% neq 0 exit /b 1
python -m pip install -r "%BASEDIR%\controller_project\requirements.txt"
if %errorlevel% neq 0 exit /b 1

echo ✅ 모든 프로젝트 최신 상태로 업데이트 완료

timeout /t 2 >nul

echo ▶ scripts/start_windows.bat 실행 중...
start "" "%BASEDIR%\scripts\start_windows.bat"
