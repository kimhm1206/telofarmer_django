# weather/context_processors.py

import os
import pandas as pd
from datetime import datetime, timedelta
from config.settings import LOG_DIR


def latest_weather_context(request):
    print("🌦 context processor 실행됨")
    today_str = datetime.today().strftime("%Y-%m-%d")
    path = os.path.join(LOG_DIR,"weather")
    file_path = os.path.join(path, f"{today_str}.csv")

    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df = df.sort_values("Time")
            latest = df.iloc[-1]

            latest_time = pd.to_datetime(latest["Time"])
            now = datetime.now()

            if (now - latest_time) <= timedelta(minutes=15):
                return {
                    "latest_weather": {
                        "time": latest["Time"],
                        "temp": latest["Temp"],
                        "humi": latest["Humi"]
                    }
                }
    except Exception as e:
        print("기상 로그 파싱 오류:", e)

    return {"latest_weather": None}