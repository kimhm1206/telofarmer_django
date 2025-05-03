# main/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime, timedelta
import json

# ✅ 연결된 WebSocket을 전역에 저장할 변수
active_controller = None
active_clients = set()
last_running_time = None
last_internet_state = None
last_data = None

class ControlConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        global active_controller
        await self.accept()
        active_controller = self  # ✅ 연결 저장

    async def disconnect(self, close_code):
        global active_controller
        if active_controller == self:
            active_controller = None

    async def receive(self, text_data):
        global last_running_time, last_internet_state
        data = json.loads(text_data)
        print(f"📨 수신 메시지: {data}")
        if data.get("cmd") == "running":
            last_running_time = datetime.now()
            last_internet_state = data.get("internet")
        

  
class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        active_clients.add(self)

        # 새 클라이언트 접속 시 → 상태 판단해서 즉시 전송
        global last_running_time, last_internet_state,last_data
        now = datetime.now()

        if last_running_time and (now - last_running_time < timedelta(minutes=20)):
            await self.send(text_data=json.dumps({
                "cmd": "running",
                "internet": last_internet_state
            }))
        else:
            await self.send(text_data=json.dumps({
                "cmd": "die",
                "internet": "die"
            }))
        if last_data:    
            await self.send(text_data=last_data)

    async def disconnect(self, close_code):
        active_clients.discard(self)
        
        
    async def receive(self, text_data):
        global last_running_time, last_internet_state,last_data

        data = json.loads(text_data)
        print(f"📨 Notify 메시지 수신됨: {data}")

        if data.get("cmd") == "running":
            last_running_time = datetime.now()
            last_internet_state = data.get("internet")
        
        elif data.get("cmd") == "data":
            last_data = text_data

        if data.get("cmd") == "manual" or data.get("cmd") == "emergency" or data.get("cmd") == "testdata": 
            global active_controller
            
            if active_controller:
                await active_controller.send(text_data=text_data)
            else:
                print("⚠ WebSocket 연결 없음 - 메시지 전송 생략")
                
        else:    
            for client in active_clients:
                if client != self:
                    await client.send(text_data=text_data)