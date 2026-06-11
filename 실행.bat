@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo.
echo  ====================================================
echo   정책사업 사전검토 보고서 자동 생성 시스템
echo   고양특례시
echo  ====================================================
echo.

:: 이미 5000 포트를 사용 중인 프로세스 종료
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000 "') do (
    taskkill /F /PID %%a > nul 2>&1
)

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo  [오류] Python이 설치되지 않았거나 PATH에 없습니다.
    echo  https://www.python.org 에서 Python 3.11 이상을 설치하세요.
    pause
    exit /b 1
)

:: .env 파일 확인
if not exist ".env" (
    echo  [경고] .env 파일이 없습니다. .env.example 을 복사합니다.
    copy ".env.example" ".env" > nul
    echo  .env 파일에 ANTHROPIC_API_KEY 를 입력한 후 다시 실행하세요.
    start notepad ".env"
    pause
    exit /b 1
)

:: Flask 서버 백그라운드 실행
echo  서버 시작 중...
start /b python app.py > nul 2>&1

:: 서버 기동 대기 (최대 10초)
set /a count=0
:wait_loop
timeout /t 1 /nobreak > nul
set /a count+=1
curl -s http://localhost:5000 > nul 2>&1
if not errorlevel 1 goto server_ready
if %count% geq 10 goto timeout_error
goto wait_loop

:server_ready
echo  서버 준비 완료!
echo.
echo  브라우저를 엽니다 → http://localhost:5000
echo.
start http://localhost:5000
echo  종료하려면 이 창을 닫으세요.
echo  (창을 닫으면 서버도 함께 종료됩니다)
echo.
pause > nul
taskkill /F /IM python.exe > nul 2>&1
exit /b 0

:timeout_error
echo  [오류] 서버가 10초 내에 응답하지 않습니다.
echo  app.py 또는 requirements.txt 를 확인하세요.
pause
exit /b 1
