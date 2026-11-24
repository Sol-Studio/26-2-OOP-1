@echo off
rem 에버그로우 스마트팜 실행: 더블클릭하면 서버가 켜지고 브라우저가 열립니다.
chcp 65001 >nul
cd /d "%~dp0"
python run.py %*
if errorlevel 1 pause
