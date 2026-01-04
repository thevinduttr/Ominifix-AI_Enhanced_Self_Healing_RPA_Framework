<#
Start RabbitMQ for local development.

This script does:
- checks for `docker` on PATH
- if `docker compose` is available, runs `docker compose up -d`
- otherwise falls back to `docker run` to start a rabbitmq:3-management container

Usage (PowerShell):
  powershell -ExecutionPolicy Bypass -File .\scripts\start_rabbitmq.ps1

If Docker is not available, the script prints next steps to start Docker Desktop.
#>

function Write-Note($msg){ Write-Host "[note] $msg" -ForegroundColor Cyan }
function Write-Err($msg){ Write-Host "[error] $msg" -ForegroundColor Red }

Write-Note "Checking for Docker..."
$docker = & where.exe docker 2>$null
if (-not $docker) {
    Write-Err "Docker CLI not found on PATH. Please start Docker Desktop or install Docker."
    Write-Host "- Open Docker Desktop and wait until 'Docker is running'"
    Write-Host "- Or install Docker Desktop: https://docs.docker.com/desktop/"
    exit 1
}

Write-Note "Docker CLI found: $docker"

Write-Note "Checking for docker compose support..."
$composeTest = & docker compose version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Note "Using 'docker compose' to bring up services"
    Push-Location ..\
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to run 'docker compose up -d'. Check Docker Desktop and compose version."
        Pop-Location
        exit 2
    }
    Pop-Location
    Write-Note "RabbitMQ should be up. Management UI: http://localhost:15672 (guest/guest)"
    exit 0
}

Write-Note "'docker compose' not available. Falling back to 'docker run'..."

# Run rabbitmq container if not already running
$existing = docker ps --filter "name=ominifix_rabbitmq" --format "{{.Names}}"
if ($existing -eq 'ominifix_rabbitmq') {
    Write-Note "RabbitMQ container 'ominifix_rabbitmq' already running"
    exit 0
}

Write-Note "Starting rabbitmq:3-management container..."
docker run -d --name ominifix_rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=guest -e RABBITMQ_DEFAULT_PASS=guest -v ominifix_rabbitmq_data:/var/lib/rabbitmq rabbitmq:3-management
if ($LASTEXITCODE -ne 0) {
    Write-Err "docker run failed. Ensure Docker Desktop is running and you have permissions."
    exit 3
}

Write-Note "Started RabbitMQ container. Management UI: http://localhost:15672 (guest/guest)"
exit 0
