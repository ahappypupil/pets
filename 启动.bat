@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   孩子宠物养成系统 - 本地启动
echo ============================================
echo.
echo   MySQL 需已启动（root / 123321，pets 库）
echo   首次运行会自动建库（幂等，不会覆盖已有数据）
echo.
python -c "from pet_system.db import init_db; init_db(); print('数据库已就绪')"
if errorlevel 1 (
  echo 数据库初始化失败，请检查 MySQL 是否运行、.env 配置是否正确
  pause
  exit /b 1
)
echo.
echo   启动后打开浏览器访问：http://127.0.0.1:5000
echo   孩子端 PIN：1234      家长端：admin / admin123
echo   按 Ctrl+C 停止
echo.
python app.py
pause
