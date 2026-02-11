#!/usr/bin/env python3
"""AITranscriber - 启动入口"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def main():
    import uvicorn
    from app.config import HOST, PORT

    print(f"\n{'='*50}")
    print(f"  AITranscriber 语音转录工具")
    print(f"  访问地址: http://{HOST}:{PORT}")
    print(f"{'='*50}\n")

    frozen = getattr(sys, 'frozen', False)

    # 打包环境下自动打开浏览器
    if frozen:
        import threading, webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=not frozen)

if __name__ == "__main__":
    main()
