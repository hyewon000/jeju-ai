@chcp 65001 > nul
@echo off

:: ============================================================
::  정책사업 보고서 시스템  exe 빌드 스크립트
::  실행 전: pip install -r requirements.txt
:: ============================================================

cd /d "%~dp0"

:: PATH에서 python 자동 탐색 (개인 경로 하드코딩 없음)
set PYTHON=python

echo.
echo  ====================================================
echo   정책사업 사전검토 보고서  exe 빌드
echo  ====================================================
echo.

:: Python 확인
%PYTHON% --version > nul 2>&1
if errorlevel 1 (
    echo  [오류] Python 을 찾을 수 없습니다.
    echo  Python 3.11 이상 설치 후 PATH 에 등록하세요.
    pause
    exit /b 1
)

:: PyInstaller 설치 확인
%PYTHON% -m PyInstaller --version > nul 2>&1
if errorlevel 1 (
    echo  [설치] PyInstaller 를 설치합니다...
    %PYTHON% -m pip install pyinstaller>=6.0.0 pystray>=0.19.5 Pillow>=10.0.0 cryptography>=42.0.0
)

:: 이전 빌드 정리
if exist dist\정책사업보고서.exe (
    echo  [정리] 이전 빌드를 삭제합니다...
    del /f dist\정책사업보고서.exe
)
if exist build (
    rmdir /s /q build
)

:: 빌드 실행
echo  [빌드] PyInstaller 실행 중...
echo.
%PYTHON% -m PyInstaller launcher.spec

echo.
if exist "dist\정책사업보고서.exe" (
    echo  ====================================================
    echo   빌드 완료!
    echo   결과물: dist\정책사업보고서.exe
    echo  ====================================================
    echo.
    echo  더블클릭하면 바로 실행됩니다.
    echo  첫 실행 시 API 키 입력 화면이 표시됩니다.
    echo.
    explorer dist
) else (
    echo  [오류] 빌드에 실패했습니다. 위 메시지를 확인하세요.
)

pause
