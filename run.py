"""에버그로우 실행 진입점: python run.py (Windows는 start.bat 더블클릭)

처음이면 필요한 것을 알아서 준비한 뒤 서버를 켜고 브라우저를 연다.
  1. 파이썬 패키지(fastapi·uvicorn)가 없으면 requirements.txt로 설치
  2. 웹 화면 패키지(web/node_modules)가 없으면 npm install
  3. 빌드된 화면(web/dist)이 없거나 소스보다 오래됐으면 npm run build
  4. 빈 포트(8000부터)를 골라 서버를 켜고, 준비되면 브라우저로 연다

옵션: --port 8000  --host 0.0.0.0(같은 와이파이의 휴대폰에서 접속)  --no-browser  --no-build
"""
import argparse
import importlib
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DIST = WEB / "dist" / "index.html"
NODE_URL = "https://nodejs.org/"


def say(msg):
    print(f"[에버그로우] {msg}", flush=True)


def ensure_python_packages():
    try:
        importlib.import_module("fastapi")
        importlib.import_module("uvicorn")
        return
    except ImportError:
        pass
    say("서버 패키지를 설치합니다 (처음 한 번만)…")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    importlib.invalidate_caches()


def newest_source_time():
    files = [WEB / "index.html", WEB / "package.json", WEB / "vite.config.js"]
    files += [p for p in (WEB / "src").rglob("*") if p.is_file()]
    files += [p for p in (WEB / "public").rglob("*") if p.is_file()]
    return max(p.stat().st_mtime for p in files if p.exists())


def ensure_web_build():
    """화면이 빌드돼 있지 않거나 소스가 더 새로우면 빌드한다. Node.js가 없으면 있는 빌드를 그대로 쓴다."""
    stale = not DIST.exists() or DIST.stat().st_mtime < newest_source_time()
    if not stale:
        return
    npm = shutil.which("npm")
    if not npm:
        if DIST.exists():
            say("Node.js가 없어 화면을 새로 빌드하지 못했습니다. 예전 빌드로 실행합니다.")
            return
        sys.exit(f"[에버그로우] 화면을 빌드하려면 Node.js가 필요합니다. {NODE_URL} 에서 LTS를 설치한 뒤 다시 실행하세요.")
    if not (WEB / "node_modules").exists():
        say("화면 패키지를 설치합니다 (처음 한 번만, 1~2분)…")
        subprocess.run([npm, "install"], cwd=WEB, check=True)
    say("화면을 빌드합니다…")
    subprocess.run([npm, "run", "build"], cwd=WEB, check=True)


def free_port(host, start):
    """start부터 비어 있는 포트를 찾는다 (이미 다른 서버가 쓰고 있을 수 있어서)."""
    for port in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    sys.exit(f"[에버그로우] {start}~{start + 19}번 포트가 모두 사용 중입니다. --port로 다른 번호를 주세요.")


def open_when_ready(url):
    """서버가 응답하기 시작하면 브라우저를 연다."""
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=0.5)
            webbrowser.open(url)
            return
        except OSError:
            time.sleep(0.2)
    say(f"서버가 늦게 켜집니다. 직접 {url} 을 열어 주세요.")


def main():
    parser = argparse.ArgumentParser(description="에버그로우 스마트팜 실행")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0이면 같은 와이파이의 휴대폰에서도 접속")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="브라우저를 열지 않는다")
    parser.add_argument("--no-build", action="store_true", help="화면 빌드를 건너뛴다")
    args = parser.parse_args()

    ensure_python_packages()
    if not args.no_build:
        ensure_web_build()
    port = free_port(args.host, args.port)
    url = f"http://127.0.0.1:{port}"
    say(f"서버를 켭니다: {url}  (끄려면 이 창에서 Ctrl + C)")
    if args.host == "0.0.0.0":
        say(f"휴대폰에서는 http://(이 컴퓨터 IP):{port} 로 접속하세요.")
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()

    import uvicorn
    uvicorn.run("server.main:app", host=args.host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
