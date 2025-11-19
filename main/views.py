# views.py
import json, os, csv, platform, subprocess
import shutil
from typing import Any, Dict

import pandas as pd
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseBadRequest, FileResponse, Http404, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from config.settings import SETTING_PATH,LOG_DIR,SYSLOG_DIR,SETTING_PATH,BASE_DIR
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from .forms import TelofarmSignupForm
import serial


def load_setting_data() -> Dict[str, Any]:
    """공통 설정 파일을 읽어오는 헬퍼 함수."""
    try:
        with open(SETTING_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise Http404("설정 파일을 찾을 수 없습니다.") from exc


def is_local_ip(request: HttpRequest) -> bool:
    ip = request.META.get("REMOTE_ADDR")
    return ip.startswith("127.") or ip.startswith("192.168.") or ip == "localhost"

def logout_view(request):
    logout(request)  # 세션 제거 → sessionid 쿠키도 삭제됨
    return redirect("login_page")

def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard_view")

    if not request.is_secure():
        # HTTP 접속 → localuser 자동 로그인 (로컬 서버 등에서)
        user, created = User.objects.get_or_create(username="localuser")
        user.set_unusable_password()
        user.save()
        login(request, user)
        return redirect("dashboard_view")

    # HTTPS 접근 시 로그인 폼 보여주기
    return render(request, "login.html")

def login_process(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard_view")
        else:
            return render(request, "login.html", {"login_failed": True})

    # ✅ GET 요청이면 login 페이지로 리다이렉트
    return redirect("login_page")

def setting_view(request):
    return render(request, 'settings.html', {
        'setting': load_setting_data()
    })

def signup_view(request):
    if request.method == "POST":
        form = TelofarmSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "회원가입이 완료되었습니다. 로그인 해주세요.")
            return redirect("login_page")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TelofarmSignupForm()
    return render(request, "signup.html", {"form": form})


def system_update(request):
    try:
        os_type = platform.system().lower()
        script_dir = os.path.join(BASE_DIR, 'scripts')

        if os_type == 'windows':
            script_path = os.path.join(script_dir, 'update_windows.bat')
            os.system(f'start "" "{script_path}"')

        elif os_type == 'linux':
            script_path = os.path.join(script_dir, 'update_rpi.sh')
            subprocess.Popen(["bash", script_path], start_new_session=True)


        else:
            return JsonResponse({"status": "error", "message": "Unsupported OS"})

        return JsonResponse({"status": "ok", "message": f"Update script launched for {os_type}"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

def dashboard_view(request):
    setting = load_setting_data()
    now = datetime.now().time()
    today_str = datetime.now().strftime("%Y%m%d")

    irrigation_channels = setting.get("irrigation_channels", {})
    led_channels = setting.get("led_channels", {})
    irrigation_active = [ch for ch, val in irrigation_channels.items() if val]
    led_active = [ch for ch, val in led_channels.items() if val]

    relay_ports = setting.get("irrigationpanel", {}).get("relay_port_mapping", {})
    led_ports = setting.get("ledpanel", {}).get("led_port_mapping", {})
    control_mode = setting.get("irrigationpanel", {}).get("control_mode", {})
    time_table = setting.get("time_control", {})

    def parse_time_str(t_str):
        try:
            return datetime.strptime(t_str, "%H:%M").time()
        except:
            return None

    irrigation_info = []
    for ch in irrigation_active:
        mode = control_mode.get(ch, "timer")
        next_time = "없음"
        count = 0
        last_time = "금일 미시작"
        percent = 0

        log_path = os.path.join(LOG_DIR, str(ch), f"{ch}ch_sensor_log_{today_str}.csv")
        if mode == "timer":
            raw_times = time_table.get(ch, [])
            parsed_times = [parse_time_str(t) for t in raw_times]
            future_times = sorted([t for t in parsed_times if t and t > now])
            next_time = future_times[0].strftime("%H:%M") if future_times else "없음"
            log_path = os.path.join(LOG_DIR, str(ch), f"{ch}_time_log_{today_str}.csv")

        
        if os.path.exists(log_path):
            try:
                df = pd.read_csv(log_path)
                if "action" in df.columns:
                    df_filtered = df[df["action"].str.contains("관수", na=False)]
                    count = len(df_filtered)
                    if count > 0:
                        last_time = pd.to_datetime(df_filtered["Time"].iloc[-1]).strftime("%H:%M")

                if "sumx" in df.columns and "goal" in df.columns and df.iloc[-1]["goal"]:
                    percent = round((df.iloc[-1]["sumx"] / df.iloc[-1]["goal"]) * 100, 2)
            except Exception as e:
                print(f"[ERROR] 로그 처리 실패 (CH{ch}): {e}")

        irrigation_info.append({
            "channel": ch,
            "mode": mode,
            "next_time": next_time,
            "port": relay_ports.get(ch, "?"),
            "count": count,
            "last_time": last_time,
            "percent": percent
        })

    led_times = setting.get("ledpanel", {}).get("led_time", {})
    led_info = []
    for ch in led_active:
        time = led_times.get(ch, {"on": "??:??", "off": "??:??"})
        led_info.append({
            "channel": ch,
            "on": time.get("on", "??:??"),
            "off": time.get("off", "??:??"),
            "port": led_ports.get(ch, "?")
        })

    return render(request, 'dashboard.html', {
        'irrigation_info': irrigation_info,
        'led_info': led_info,
        'irrigation_active': irrigation_active,
        'led_active': led_active
    })

def api_testdata(request):
    ch = request.GET.get("ch", "1").replace("ch", "")
    file_path = os.path.join(LOG_DIR, "test", f"{ch}ch_test.csv")

    if not os.path.exists(file_path):
        return JsonResponse({"error": "데이터가 아직 준비되지 않았습니다."}, status=404)

    try:
        df = pd.read_csv(file_path)
        os.remove(file_path)  # ✅ 항상 삭제

        # ✅ "nodata" CSV 처리 → 200 OK로 응답
        if list(df.columns) == ["status"] and df.shape[0] == 1 and df.iloc[0, 0] == "nodata":
            return JsonResponse({"nodata": True})  # ← 여기 핵심

        # ✅ 정상 처리
        chart_data = make_chart_data(df)
        return JsonResponse(chart_data)

    except Exception as e:
        return JsonResponse({"error": f"처리 실패: {str(e)}"}, status=500)

def api_logdata(request):
    ch_raw = request.GET.get("ch", "1")
    ch = ch_raw.replace("ch", "")
    date = request.GET.get("date")  # yyyy-mm-dd

    try:
        date_str = date.replace("-", "")
        file_path = os.path.join(LOG_DIR, ch, f"{ch}ch_sensor_log_{date_str}.csv")

        if not os.path.exists(file_path):
            return JsonResponse({"error": "파일이 존재하지 않습니다."}, status=404)

        df = pd.read_csv(file_path)
        chart_data = make_chart_data(df)
        return JsonResponse(chart_data)

    except Exception as e:
        return JsonResponse({"error": f"처리 중 오류 발생: {str(e)}"}, status=500)

def make_chart_data(df):
    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time")

    # ✅ 수동 관수 제거
    df_nomanual = df[~df["action"].astype(str).str.contains("수동")]
    
    if not df_nomanual.empty:
        first_time = df_nomanual.iloc[0]["Time"]
        if not (first_time.hour == 0 and first_time.minute == 0):
            dummy_time = first_time.replace(hour=0, minute=0, second=0, microsecond=0)
            dummy_row = pd.DataFrame([{
                "realTime" : dummy_time,
                "Time": dummy_time,
                "svalue": None,
                "sumx": None,
                "dailysumx": None,
                "action": None,
                "goal": None
            }])
            df_nomanual = pd.concat([dummy_row, df_nomanual], ignore_index=True).sort_values("Time").reset_index(drop=True)
            
    # ✅ 라벨은 수동 제외하고 남은 데이터의 Time 컬럼
    labels = list(df_nomanual["Time"])

    # ✅ 마지막 시간 다음날 00:00 추가
    if labels:
        last_time = max(labels)
        next_day = (last_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        labels.append(next_day)

    # ✅ dict 만들기
    def to_time_dict(df, col):
        return {t: v for t, v in zip(df["Time"], df[col]) if pd.notna(v)}

    svalue_dict = to_time_dict(df_nomanual, "svalue")
    sumx_dict = to_time_dict(df_nomanual, "sumx")
    dailysumx_dict = to_time_dict(df_nomanual, "dailysumx")

    goal_points = {}
    manual_goal_points = {}

    for idx, (t, g, a) in enumerate(zip(df["Time"], df["goal"], df["action"])):
        if "관수" in str(a) and "수동" not in str(a):
            if pd.notna(g):
                goal_points[t] = int(g)  # ✅ int로 변환
        elif "수동" in str(a):
            if idx > 0:
                prev_goal = df.iloc[idx - 1]["goal"]
                if pd.notna(prev_goal):
                    manual_goal_points[t] = int(prev_goal)  # ✅ int로 변환
            else:
                if pd.notna(g):
                    manual_goal_points[t] = int(g)  # ✅ int로 변환

    def to_xy_list(d):
        return [{"x": t, "y": v} for t, v in d.items()]

    # ✅ Y축 범위
    svalue_series = df_nomanual["svalue"].dropna()
    s_min = svalue_series.min()
    s_max = svalue_series.max()
    s_range = s_max - s_min
    ymin = s_min - s_range * 0.05
    ymax = s_max + s_range * 0.3

    return {
        "labels": labels,
        "svalue_y": {"min": round(ymin, 4), "max": round(ymax, 4)},
        "datasets": [
            {
                "label": "svalue",
                "data": to_xy_list(svalue_dict),
                "borderColor": "limegreen",
                "tension": 0.4,
                "pointRadius": 0,
                "yAxisID": "y",
                "cubicInterpolationMode": "monotone"
            },
            {
                "label": "dailysumx",
                "data": to_xy_list(dailysumx_dict),
                "borderColor": "blue",
                "tension": 0.1,
                "pointRadius": 0,
                "yAxisID": "y"
            },
            {
                "label": "sumx",
                "data": to_xy_list(sumx_dict),
                "borderColor": "green",
                "tension": 0.1,
                "pointRadius": 0,
                "yAxisID": "y"
            },
            {
                "label": "goal",
                "data": to_xy_list(goal_points),
                "borderColor": "red",
                "pointBackgroundColor": "red",
                "pointRadius": 5,
                "showLine": False,
                "yAxisID": "y"
            },
            {
                "label": "manual_goal",
                "data": to_xy_list(manual_goal_points),
                "borderColor": "blue",
                "pointBackgroundColor": "blue",
                "pointRadius": 5,
                "showLine": False,
                "yAxisID": "y"
            }
        ]
    }


def data_view(request):
    today = datetime.now().strftime("%Y%m%d")
    panels = []
    
    # 설정 로딩
    with open(SETTING_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    irrigation = config.get("irrigation_channels", {})
    control_mode = config.get("irrigationpanel", {}).get("control_mode", {})

    for ch, enabled in irrigation.items():
        if not enabled or control_mode.get(ch) != "sensor":
            continue

        chart_data = None
        filename = os.path.join(LOG_DIR, str(ch), f"{ch}ch_sensor_log_{today}.csv")
        filepath = os.path.join(LOG_DIR, filename)

        try:
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                # realTime 컬럼 제거
                if "realTime" in df.columns:
                    df.drop(columns=["realTime"], inplace=True)
                chart_data = make_chart_data(df)
        except Exception as e:
            print(f"[ERROR] CH{ch} 데이터 처리 실패: {e}")

        panels.append({
            "type": "irrigation",
            "channel": ch,
            "chart_data": chart_data
        })
        
    panels.append({"type": "dummy"})  
    return render(request, "data.html", {"panels": panels})


def log_view(request):
    today = datetime.now().strftime("%Y%m%d")

    try:
        with open(SETTING_PATH, encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}

    irrigation_active = [int(ch) for ch, val in config.get("irrigation_channels", {}).items() if val]
    irrigation_info = []

    for ch in irrigation_active:
        log_path_csv = os.path.join(LOG_DIR, str(ch), f"{ch}ch_sensor_log_{today}.csv")
        log_path_fallback = os.path.join(LOG_DIR, str(ch), f"{ch}_time_log_{today}.csv")

        log_text = ""
        headers, rows = [], []
        is_sensor = False

        try:
            with open(log_path_csv, encoding='utf-8') as f:
                df = pd.read_csv(f)
                if df.shape[1] > 3:
                    is_sensor = True
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0]).dt.strftime("%Y-%m-%d %H:%M:%S")  # realTime
                    df["Time"] = pd.to_datetime(df["Time"]).dt.strftime("%H:%M")  # 축약

                    # 수치 소수점 처리
                    for i in [2, 3, 4]:  # realTime, Time, svalue, sumx, dailysumx 순서 예상
                        if i < df.shape[1]:
                            df.iloc[:, i] = df.iloc[:, i].map(lambda x: f"{x:.2f}" if pd.notnull(x) else x)

                headers = list(df.columns)
                rows = df.values.tolist()

        except:
            try:
                with open(log_path_fallback, encoding='utf-8') as f:
                    df = pd.read_csv(f)
                    headers = list(df.columns)
                    rows = df.values.tolist()
            except:
                headers = []
                rows = []

        irrigation_info.append({
            "channel": ch,
            "headers": headers,
            "rows": rows,
            "is_sensor": is_sensor
        })

    syslog_path = os.path.join(SYSLOG_DIR, f"log_{today}.txt")
    try:
        with open(syslog_path, encoding='utf-8') as f:
            system_log = f.read()
    except:
        system_log = "시스템 로그 없음"

    return render(request, "log.html", {
        "irrigation_info": irrigation_info,
        "system_log": system_log
    })

def log_refresh(request):
    today = datetime.now().strftime("%Y%m%d")

    try:
        with open(SETTING_PATH, encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}

    irrigation_active = [int(ch) for ch, val in config.get("irrigation_channels", {}).items() if val]
    irrigation_info = []

    for ch in irrigation_active:
        log_path_csv = os.path.join(LOG_DIR, str(ch), f"{ch}ch_sensor_log_{today}.csv")
        log_path_fallback = os.path.join(LOG_DIR, str(ch), f"{ch}_time_log_{today}.csv")

        log_text = ""
        headers, rows = [], []
        is_sensor = False

        try:
            with open(log_path_csv, encoding='utf-8') as f:
                df = pd.read_csv(f)
                if df.shape[1] > 3:
                    is_sensor = True
                    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0]).dt.strftime("%m-%d %H:%M")
                    for i in [1, 2, 3]:
                        df.iloc[:, i] = df.iloc[:, i].map(lambda x: f"{x:.2f}" if pd.notnull(x) else x)
                headers = list(df.columns)
                rows = df.values.tolist()
        except:
            try:
                with open(log_path_fallback, encoding='utf-8') as f:
                    df = pd.read_csv(f)
                    headers = list(df.columns)
                    rows = df.values.tolist()
            except:
                headers = []
                rows = []

        irrigation_info.append({
            "channel": ch,
            "headers": headers,
            "rows": rows,
            "is_sensor": is_sensor
        })

    syslog_path = os.path.join(SYSLOG_DIR, f"log_{today}.txt")
    try:
        with open(syslog_path, encoding='utf-8') as f:
            system_log = f.read()
    except:
        system_log = "시스템 로그 없음"

    html = render_to_string("partials/log_content.html", {
        "irrigation_info": irrigation_info,
        "system_log": system_log
    })

    return JsonResponse({"html": html})

def download_log(request, channel):
    today = datetime.now().strftime("%Y%m%d")
    csv_names = [
        f"{channel}ch_sensor_log_{today}.csv",
        f"{channel}_time_log_{today}.csv"
    ]
    for name in csv_names:
        log_path = os.path.join(LOG_DIR, str(channel), name)
        if os.path.exists(log_path):
            return FileResponse(open(log_path, 'rb'), as_attachment=True, filename=name)
    raise Http404("해당 로그 파일이 존재하지 않습니다.")

@csrf_exempt
def update_setting(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")

    try:
        new_data = json.loads(request.body)

        with open(SETTING_PATH, 'r', encoding='utf-8') as f:
            current = json.load(f)

        for key, value in new_data.items():
            if key in ["irrigationpanel", "ledpanel", "sensor_settings", "time_control"]:
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, dict):
                        current[key].setdefault(subkey, {}).update(subvalue)
                    else:
                        current[key][subkey] = subvalue
            else:
                if key.startswith("irrigation_channels_"):
                    ch = key.split("_")[-1]
                    current["irrigation_channels"][ch] = value
                elif key.startswith("led_channels_"):
                    ch = key.split("_")[-1]
                    current["led_channels"][ch] = value
                elif key.startswith("area_infor_"):
                    field = key.replace("area_infor_", "")
                    if field in ["fan", "open", "close", "port"]:   # 숫자 필드
                        try:
                            value = int(value)
                        except ValueError:
                            pass
                    current.setdefault("area_infor", {})[field] = value
                elif key == "irrigation_mix_port":  # 숫자 필드
                    try:
                        current["irrigation_mix_port"] = int(value)
                    except ValueError:
                        current["irrigation_mix_port"] = value
                else:
                    current[key] = value

        with open(SETTING_PATH, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        # ✅ WebSocket 메시지 전송
        from asgiref.sync import async_to_sync
        from main.consumers import active_controller
        import json as js
        
        if active_controller:
            async_to_sync(active_controller.send)(text_data=js.dumps({"cmd": "refresh"}))
        else:
            print("⚠ WebSocket 연결 없음 - 메시지 전송 생략")

        return JsonResponse({"status": "success"})

    except Exception as e:
        return HttpResponseBadRequest(f"Error: {str(e)}")

@csrf_exempt
@require_POST
def overwrite_setting(request):
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    uploaded_file = request.FILES['file']
    temp_path = default_storage.save('temp_uploaded.json', uploaded_file)

    try:
        shutil.move(temp_path, SETTING_PATH)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def download_setting(request):
    if os.path.exists(SETTING_PATH):
        return FileResponse(open(SETTING_PATH, 'rb'), as_attachment=True, filename="setting.json")

def test_port(request):
    port = request.GET.get("port")
    if not port:
        return JsonResponse({"success": False})

    try:
        # 시리얼 포트 열기
        ser = serial.Serial(port, baudrate=9600, timeout=1)

        # 요청 패킷 구성
        data = bytearray([0x02, ord('0'), 0x52, 0x58, 0x5A, 0x54, 0x48, 0x4C, 0x03])
        checksum = 0
        for b in data:
            checksum ^= b
        data.append(checksum)

        # 전송
        ser.write(data)

        # 응답 읽기
        response = ser.read(28)
        ser.close()

        if len(response) < 28:
            return JsonResponse({"success": False})

        # 간단히 디코딩해서 형식 확인
        try:
            decoded = response.decode("utf-8", errors="ignore")
            print("수신된 데이터:", decoded)
        except:
            return JsonResponse({"success": False})

        return JsonResponse({"success": True})

    except Exception as e:
        print("포트 테스트 실패:", e)
        return JsonResponse({"success": False})
    
def weather_data_page(request):
    date_str = request.GET.get("date")
    if not date_str:
        date_str = datetime.today().strftime("%Y-%m-%d")

    path = os.path.join(LOG_DIR,"weather")
    file_path = os.path.join(path, f"{date_str}.csv")

    data = []
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = df.sort_values("Time")
        data = df.to_dict(orient="records")

    return render(request, "weatherdata.html", {
        "today": date_str,
        "weather_data": data
    })
    
    
def download_weather_csv(request):
    date_str = request.GET.get("date")
    if not date_str:
        raise Http404("날짜가 지정되지 않았습니다")
    
    path = os.path.join(LOG_DIR,"weather")
    file_path = os.path.join(path, f"{date_str}.csv")
    
    if not os.path.exists(file_path):
        raise Http404("CSV 파일이 존재하지 않습니다")

    filename = f"{date_str}_weather.csv"
    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename)