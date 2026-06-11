@chcp 65001 > nul
@echo off
cd /d "%~dp0"

set PYTHON="C:\Users\shw09\AppData\Local\Programs\Python\Python314\python.exe"
set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
set URL=http://localhost:5000

echo.
echo  ====================================================
echo   정책사업 사전검토 보고서 자동 생성 시스템
echo   고양특례시
echo  ====================================================
echo.

:: .env 파일 확인
if not exist ".env" (
    echo  [경고] .env 파일이 없습니다. .env.example 을 복사합니다.
    copy ".env.example" ".env" > nul
    echo  .env 파일에 ANTHROPIC_API_KEY 를 입력한 후 다시 실행하세요.
    notepad ".env"
    pause
    exit /b 1
)

:: 기존 5000 포트 프로세스 종료
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr "0.0.0.0:5000 "') do (
    taskkill /F /PID %%a > nul 2>&1
)

:: Python 실행 파일 확인
if not exist %PYTHON% (
    echo  [오류] Python 을 찾을 수 없습니다.
    echo  경로: %PYTHON%
    echo  Python 3.11 이상 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

:: Flask 서버 실행
echo  서버 시작 중...
start /b %PYTHON% app.py

:: 3초 대기
timeout /t 3 /nobreak > nul

:: 브라우저 열기
echo  브라우저를 엽니다 --^> %URL%
echo.

if exist %CHROME% (
    start "" %CHROME% %URL%
) else (
    start "" %URL%
)

echo  서버가 실행 중입니다.
echo  종료하려면 이 창을 닫으세요.
echo  (창을 닫으면 서버도 함께 종료됩니다)
echo.
pause > nul

:: 창 닫힐 때 서버 종료
taskkill /F /IM python.exe > nul 2>&1
