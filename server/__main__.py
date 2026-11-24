"""python -m server 로 실행한다. 웹 화면은 web/dist(npm run build 결과)를 같이 내보낸다.
같은 와이파이의 휴대폰에서 접속하려면: python -m server --host 0.0.0.0"""
import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="에버그로우 스마트팜 서버")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"EverGrow 서버: http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}  (끄려면 Ctrl + C)")
    uvicorn.run("server.main:app", host=args.host, port=args.port)
