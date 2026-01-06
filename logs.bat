@echo off
REM View logs from all services or specific service

if "%1"=="" (
    echo Viewing logs from all services...
    echo Press Ctrl+C to stop
    echo.
    docker-compose logs -f
) else (
    echo Viewing logs from %1...
    echo Press Ctrl+C to stop
    echo.
    docker-compose logs -f %1
)
