from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import platform
import subprocess
import uvicorn
import os
import threading
import time
import re

def clear_screen():
    system_name = platform.system()
    if system_name == 'Windows':
        os.system('cls')  # Lệnh clear trên Windows
    else:
        os.system('clear')  # Lệnh clear trên Linux/macOS

app = FastAPI()

@app.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            cmd = await websocket.receive_text()
            clear_screen()
            print(f"Client gửi lệnh: {cmd.strip()}")

            try:
                # Thực thi lệnh
                result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
            except subprocess.CalledProcessError as e:
                result = f"Lỗi khi thực thi:\n{e.output}"

            await websocket.send_text(result.strip())
    except WebSocketDisconnect:
        clear_screen()
        print("Client đã ngắt kết nối.")

# @app.get("/")
# async def root():
#     return JSONResponse(content={"message": "Server is running on HTTP"})

PORT = int(os.environ.get('PORT', 1997))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, 'output.txt')
ST_FILE = None
for root, dirs, files in os.walk(BASE_DIR):
    if 'stdout.txt' in files:
        candidate = os.path.join(root, 'stdout.txt')
        if os.path.getsize(candidate) > 0:
            ST_FILE = candidate
            break

LS_FILE = os.path.join(BASE_DIR, "ls.txt")

def write_line(line):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def clean_line(line):
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ANSI_ESCAPE.sub('', line.strip())

@app.get("/ls", response_class=HTMLResponse)
async def get_ls():
    try:
        process = subprocess.Popen('bash -c "ls /"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output, _ = process.communicate(timeout=300)

        with open(LS_FILE, "w", encoding="utf-8") as f:
            f.write(output)

        subprocess.Popen('bash -c "tail -f /dev/null"', shell=True)
        return f"<pre>{output}</pre>"
    except subprocess.CalledProcessError as e:
        return HTMLResponse(content=f"<pre>Lỗi khi chạy lệnh ls: {e.output}</pre>", status_code=500)

@app.get("/", response_class=HTMLResponse)
async def show():
    if not ST_FILE or not os.path.exists(ST_FILE):
        return HTMLResponse(content=f"Không tìm thấy file stdout.txt hợp lệ.", status_code=404)

    with open(ST_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        return "Không có dữ liệu trong file."

    pattern = r'STATUS.*?/s'
    matching_parts = []
    for line in lines:
        parts = re.findall(pattern, line.strip())
        matching_parts.extend(parts)

    if not matching_parts:
        return "Không có đoạn dữ liệu thỏa mãn."

    return f"<pre>{matching_parts[-1]}</pre>"

@app.post("/run-command")
async def run_command(request: Request):
    data = await request.json()
    commands = data.get('commands')

    if not commands or not isinstance(commands, list) or len(commands) == 0:
        return PlainTextResponse("ERROR 400", status_code=400)

    with open(OUTPUT_FILE, 'w', encoding='utf-8'):
        pass

    def run_commands():
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)

        write_line("Done.")

    threading.Thread(target=run_commands).start()
    return PlainTextResponse("Done.")
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1997, log_level="critical")
