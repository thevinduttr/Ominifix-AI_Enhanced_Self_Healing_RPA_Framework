@echo off
REM Check status of all services

echo Service Status:
echo ================
docker-compose ps

echo.
echo Resource Usage:
echo ================
docker stats --no-stream

echo.
pause
