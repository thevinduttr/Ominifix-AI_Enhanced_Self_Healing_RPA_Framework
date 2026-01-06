@echo off
REM Deploy Script for Ominifix AI Enhanced Self-Healing RPA Framework
REM This script builds and starts all Docker containers

echo ==========================================
echo Ominifix AI Self-Healing RPA Deployment
echo ==========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo X Error: Docker is not running. Please start Docker Desktop and try again.
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo X Error: docker-compose not found. Please install docker-compose.
    exit /b 1
)

echo [OK] docker-compose is available
echo.

REM Stop any existing containers
echo [*] Stopping existing containers...
docker-compose down
echo.

REM Build images
echo [*] Building Docker images (this may take several minutes)...
docker-compose build --no-cache
if errorlevel 1 (
    echo X Build failed!
    exit /b 1
)
echo.

REM Start services
echo [*] Starting services...
docker-compose up -d
if errorlevel 1 (
    echo X Failed to start services!
    exit /b 1
)
echo.

REM Wait for services to be ready
echo [*] Waiting for services to initialize...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo [*] Service Status:
docker-compose ps

echo.
echo [OK] Deployment completed!
echo.
echo [*] Access Points:
echo    - Orchestrator Dashboard: http://localhost:8000
echo    - RabbitMQ Management:    http://localhost:15672 (guest/guest)
echo    - Model Server:           http://localhost:8002
echo    - AI Healing Engine:      http://localhost:5001
echo    - AI Element Locator:     http://localhost:8001
echo.
echo [*] View logs:
echo    docker-compose logs -f
echo.
echo [*] Stop services:
echo    docker-compose down
echo.
pause
