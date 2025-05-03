# main/ws.py
from .consumers import active_controller
import asyncio
import json

async def send_refresh_command():
    if active_controller:
        await active_controller.send(text_data=json.dumps({"cmd": "refresh"}))
    else:
        print("⚠ controller가 아직 연결되지 않음")