"""
launcher.py — 정책사업 사전검토 보고서 시스템 런처
PyInstaller --onefile --noconsole 빌드 전용 진입점

흐름:
  1. APPDATA에서 암호화된 API 키 로드
  2. 키 없으면 tkinter 입력 화면
  3. Flask 서버 → 백그라운드 스레드
  4. Chrome 앱 모드로 자동 실행
  5. 트레이 아이콘 (종료 / 초기화 메뉴)
"""

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


# ── PyInstaller 리소스 경로 ──────────────────────────────────────────────────

def _res(rel: str) -> str:
    """번들 내부 리소스의 절대 경로를 반환한다."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / rel)


# ── 영구 데이터 디렉터리 ────────────────────────────────────────────────────

def _data_dir() -> Path:
    d = Path(os.environ.get("APPDATA", Path.home())) / "GoyangPolicyReport"
    d.mkdir(parents=True, exist_ok=True)
    return d


_KEYS_FILE = _data_dir() / "keys.enc"


# ── 암호화 (머신 바인딩 Fernet) ─────────────────────────────────────────────

def _fernet():
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    seed = (socket.gethostname() + os.environ.get("USERNAME", "user")).encode()
    salt = hashlib.sha256(seed).digest()[:16]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(seed)))


def load_keys() -> dict:
    if not _KEYS_FILE.exists():
        return {}
    try:
        return json.loads(_fernet().decrypt(_KEYS_FILE.read_bytes()).decode())
    except Exception:
        return {}


def save_keys(keys: dict):
    _KEYS_FILE.write_bytes(_fernet().encrypt(json.dumps(keys).encode()))


def apply_keys(keys: dict):
    """os.environ에 API 키를 설정한다. load_dotenv() 보다 먼저 호출해야 한다."""
    mapping = {
        "claude": "ANTHROPIC_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "law":    "LAW_API_KEY",
    }
    for field, env_var in mapping.items():
        if keys.get(field):
            os.environ[env_var] = keys[field]


# ── API 키 입력 다이얼로그 ──────────────────────────────────────────────────

class _KeyDialog(tk.Toplevel):
    result: dict | None = None

    def __init__(self, parent: tk.Tk, existing: dict):
        super().__init__(parent)
        self.title("API 키 설정 — 고양특례시 정책사업 보고서 시스템")
        self.resizable(False, False)
        self.configure(bg="#f5f6fa")

        # 헤더 바
        hdr = tk.Frame(self, bg="#003087", height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr,
            text="  고양특례시  정책사업 사전검토 보고서 시스템",
            bg="#003087",
            fg="white",
            font=("맑은 고딕", 11, "bold"),
        ).pack(side="left", padx=10, pady=12)

        # 본문
        body = tk.Frame(self, bg="#f5f6fa", padx=28, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="API 키는 이 PC에 암호화하여 저장됩니다. 다음 실행부터 자동 로드됩니다.",
            bg="#f5f6fa",
            fg="#6b7280",
            font=("맑은 고딕", 8),
        ).pack(anchor="w", pady=(0, 14))

        def _row(label: str, required: bool, hint: str) -> tk.Entry:
            f = tk.Frame(body, bg="#f5f6fa")
            f.pack(fill="x", pady=4)
            mark = "  *필수" if required else "  (선택)"
            tk.Label(
                f, text=label + mark, bg="#f5f6fa", fg="#374151",
                font=("맑은 고딕", 9, "bold"), width=22, anchor="w",
            ).pack(side="left")
            e = tk.Entry(f, show="*", width=40, font=("맑은 고딕", 9), relief="solid", bd=1)
            e.pack(side="left")
            if hint:
                tk.Label(
                    f, text="  " + hint, bg="#f5f6fa", fg="#9ca3af",
                    font=("맑은 고딕", 8),
                ).pack(side="left")
            return e

        self.e_claude = _row("Claude API 키", required=True,  hint="sk-ant-...")
        self.e_tavily = _row("Tavily API 키", required=False, hint="tvly-...")
        self.e_law    = _row("법령 API 키",   required=False, hint="법령 사용자 ID")

        # 기존 값 표시
        for entry, key in [
            (self.e_claude, "claude"),
            (self.e_tavily, "tavily"),
            (self.e_law,    "law"),
        ]:
            if existing.get(key):
                entry.insert(0, existing[key])

        # 버튼 행
        btn = tk.Frame(body, bg="#f5f6fa")
        btn.pack(fill="x", pady=(16, 0))
        tk.Button(
            btn, text="저장 후 실행", command=self._on_save,
            bg="#003087", fg="white", font=("맑은 고딕", 10, "bold"),
            relief="flat", padx=18, pady=7, cursor="hand2",
        ).pack(side="right")
        tk.Button(
            btn, text="취소", command=self.destroy,
            bg="#e5e7eb", fg="#374151", font=("맑은 고딕", 9),
            relief="flat", padx=14, pady=7, cursor="hand2",
        ).pack(side="right", padx=8)

        self.geometry("580x255")
        self.lift()
        self.focus_force()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_save(self):
        claude = self.e_claude.get().strip()
        if not claude:
            messagebox.showwarning("입력 필요", "Claude API 키는 필수 항목입니다.", parent=self)
            return
        self.result = {
            "claude": claude,
            "tavily": self.e_tavily.get().strip(),
            "law":    self.e_law.get().strip(),
        }
        self.destroy()


def ask_keys(existing: dict) -> dict | None:
    """블로킹 tkinter 다이얼로그. 취소 시 None 반환."""
    root = tk.Tk()
    root.withdraw()
    dlg = _KeyDialog(root, existing)
    root.wait_window(dlg)
    result = dlg.result
    root.destroy()
    return result


# ── Flask 서버 (백그라운드 스레드) ──────────────────────────────────────────

_flask_ready = threading.Event()


def _flask_worker():
    # apply_keys()가 먼저 호출됐으므로 load_dotenv()는 이미 설정된 env 유지
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

    def _reset_keys(_icon, _item):
        if _KEYS_FILE.exists():
            _KEYS_FILE.unlink()
        messagebox.showinfo(
            "API 키 초기화",
            "키 파일이 삭제되었습니다.\n"
            "종료 후 다시 실행하면 키 입력 화면이 표시됩니다.",
        )

    def _quit(_icon, _item):
        _icon.stop()
        os._exit(0)

    icon = pystray.Icon(
        "policy-report",
        _make_icon_image(),
        "정책사업 사전검토 보고서 | 고양특례시",
        menu=pystray.Menu(
            pystray.MenuItem("브라우저 열기", _open_browser, default=True),
            pystray.MenuItem("API 키 초기화", _reset_keys),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", _quit),
        ),
    )
    icon.run()


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    # 1) 저장된 키 로드
    keys = load_keys()

    # 2) Claude 키 없으면 첫 실행 입력 화면
    if not keys.get("claude"):
        keys = ask_keys(keys) or {}
        if not keys.get("claude"):
            sys.exit(0)
        save_keys(keys)

    # 3) 환경변수 적용 (load_dotenv보다 먼저)
    apply_keys(keys)

    # 4) DB를 APPDATA로 고정 (PyInstaller temp 디렉터리에 생성되지 않도록)
    os.environ.setdefault("DB_PATH", str(_data_dir() / "reports.db"))

    # 5) Flask 서버 시작 (daemon 스레드)
    threading.Thread(target=_flask_worker, daemon=True, name="flask").start()

    # 6) 서버 준비 대기 (최대 15초)
    if not _flask_ready.wait(15):
        messagebox.showerror(
            "실행 오류",
            "Flask 서버가 15초 내에 응답하지 않습니다.\n앱을 종료합니다.",
        )
        sys.exit(1)

    # 7) Chrome 앱 모드 열기
    open_chrome("http://localhost:5000")

    # 8) 트레이 아이콘 (메인 스레드 블로킹)
    run_tray()


if __name__ == "__main__":
    main()
