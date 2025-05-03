BASEDIR="$HOME"

echo "🔄 Django(daphne) 종료..."
pkill -f daphne

echo "🔄 controller(main.py) 종료..."
pkill -f main.py

echo "🔄 cloudflared 종료..."
pkill -f cloudflared

echo "📥 Django pull"
cd "$BASEDIR/telofarmer_django"
git pull

echo "📥 Controller pull"
cd "$BASEDIR/controller_project"
git pull

echo "🚀 cloudflared 실행"
cd "$BASEDIR/telofarmer_django"
nohup cloudflared tunnel --url http://localhost:8000 --hostname gwanak.telofarm.net &

echo "🌀 daphne 실행"
nohup daphne config.asgi:application &

echo "🐍 controller 실행"
cd "$BASEDIR/controller_project"
nohup python3 main.py &

echo "✅ 모든 구성요소 실행 완료"