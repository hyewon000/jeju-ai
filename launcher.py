"""
launcher.py — 정책사업 사전검토 보고서 시스템 런처
PyInstaller --onefile --noconsole 빌드 전용 진입점

흐름:
  1. APPDATA 에서 암호화된 API 키 로드 → os.environ 적용
  2. Flask 서버 백그라운드 시작
  3. 키 없으면 /settings 페이지, 있으면 / 페이지로 Chrome 오픈
  4. 트레이 아이콘 (환경설정 / 종료)
"""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import key_store


# ── PyInstaller 리소스 경로 ──────────────────────────────────────────────────

def _res(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / rel)


# ── Flask 서버 (백그라운드 스레드) ──────────────────────────────────────────

_flask_ready = threading.Event()


def _flask_worker():
    import app as flask_app  # noqa: PLC0415

    def _poll():
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
                    pass
                _flask_ready.set()
                return
            except OSError:
                time.sleep(0.3)

    threading.Thread(target=_poll, daemon=True).start()
    flask_app.app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


# ── Chrome 앱 모드 실행 ─────────────────────────────────────────────────────

_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def open_chrome(url: str):
    chrome = next((p for p in _CHROME_PATHS if Path(p).exists()), None)
    if chrome:
        subprocess.Popen(
            [chrome, f"--app={url}", "--disable-extensions", "--no-first-run"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        import webbrowser
        webbrowser.open(url)


# ── 트레이 아이콘 ───────────────────────────────────────────────────────────

def _make_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), "#003087")
    draw = ImageDraw.Draw(img)
    m = 8
    draw.ellipse([m, m, size - m, size - m], outline="white", width=4)
    cx, cy = size // 2, size // 2
    draw.line([(cx - 11, cy), (cx + 11, cy)], fill="white", width=4)
    draw.line([(cx, cy - 11), (cx, cy + 11)], fill="white", width=4)
    return img


def run_tray():
    import pystray

    def _open_browser(_icon, _item):
        open_chrome("http://localhost:5000")

    def _open_settings(_icon, _item):
        open_chrome("http://localhost:5000/settings")

    def _quit(_icon, _item):
        _icon.stop()
        os._exit(0)

    icon = pystray.Icon(
        "policy-report",
        _make_icon_image(),
        "정책사업 사전검토 보고서 | 고양특례시",
        menu=pystray.Menu(
            pystray.MenuItem("브라우저 열기", _open_browser, default=True),
            pystray.MenuItem("환경설정", _open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", _quit),
        ),
    )
    icon.run()


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    # 1) 저장된 키 로드 → os.environ 적용
    keys = key_store.load_keys()
    key_store.apply_keys(keys)

    # 2) DB 를 APPDATA 로 고정 (PyInstaller temp 에 생성되지 않도록)
    os.environ.setdefault(
        "DB_PATH",
        str(key_store._data_dir() / "reports.db"),
    )

    # 3) Flask 서버 시작 (daemon 스레드)
    threading.Thread(target=_flask_worker, daemon=True, name="flask").start()

    # 4) 서버 준비 대기 (최대 15초)
    if not _flask_ready.wait(15):
        import tkinter
        from tkinter import messagebox
        tkinter.Tk().withdraw()
        messagebox.showerror(
            "실행 오류",
            "Flask 서버가 15초 내에 응답하지 않습니다.\n앱을 종료합니다.",
        )
        sys.exit(1)

    # 5) Claude 키 없으면 설정 페이지, 있으면 메인 페이지
    start_url = (
        "http://localhost:5000/settings"
        if not keys.get("claude")
        else "http://localhost:5000"
    )
    open_chrome(start_url)

    # 6) 트레이 아이콘 (메인 스레드 블로킹)
    run_tray()


if __name__ == "__main__":
    main()
