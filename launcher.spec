# launcher.spec — PyInstaller 단일 exe 빌드 설정
# 빌드 명령: pyinstaller launcher.spec
# 결과물:    dist/정책사업보고서.exe

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Flask 템플릿 / 정적 파일
        ("templates",          "templates"),
        ("static",             "static"),
        # 단일 HTML 버전 (Flask /standalone 라우트용)
        ("policy-report.html", "."),
        # Python 소스 모듈 (frozen 후 import 대상)
        ("app.py",             "."),
        ("agents.py",          "."),
        ("db.py",              "."),
        ("key_store.py",       "."),
        ("law_search.py",      "."),
        ("tavily_search.py",   "."),
        ("word_export.py",     "."),
        # 환경변수 예시 (참고용)
        (".env.example",       "."),
    ],
    hiddenimports=[
        # Flask / Werkzeug
        "flask",
        "flask.templating",
        "jinja2",
        "jinja2.ext",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.debug",
        # Anthropic SDK
        "anthropic",
        "anthropic._models",
        "httpx",
        "httpcore",
        # 트레이 아이콘
        "pystray",
        "pystray._win32",
        # Pillow
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL._imagingtk",
        # 암호화
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        # 기타
        "tavily",
        "requests",
        "docx",
        "dotenv",
        "sqlite3",
        "tkinter",
        "tkinter.messagebox",
        "tkinter.ttk",
        "xml.etree.ElementTree",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 사용하지 않는 대형 패키지 제외 (빌드 크기 최적화)
    excludes=["matplotlib", "numpy", "pandas", "scipy", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="정책사업보고서",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,    # cmd 창 숨김
    windowed=True,    # 윈도우 앱 모드
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,        # .ico 파일 경로로 교체 가능 (예: icon="icon.ico")
)
