@echo off
chcp 65001 >nul
title QuizScanner 课堂答题系统

echo ===================================================
echo           QuizScanner 课堂智能答题系统
echo ===================================================
echo 正在检查 Python 运行环境并启动服务...

python launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [提示] 启动遇到问题，尝试使用默认 Python 启动...
    py launcher.py
)

pause
