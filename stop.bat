@echo off
REM Stop all services

echo Stopping all services...
docker-compose down

echo.
echo All services stopped.
echo.
echo To remove volumes as well, use:
echo    docker-compose down -v
echo.
pause
