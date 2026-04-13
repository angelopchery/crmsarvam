@echo off
REM CRMSarvam Docker Startup Script (Windows)
REM This script helps with initial setup and startup

echo ==========================================
echo    CRMSarvam Docker Startup Script
echo ==========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please create .env from .env.example:
    echo   copy .env.example .env
    echo Then edit .env with your configuration
    exit /b 1
)

echo [INFO] Configuration file found: .env

REM Stop existing containers
echo [INFO] Stopping existing containers...
docker-compose down

REM Remove old volumes if requested
if "%1"=="--clean" (
    echo [WARN] Removing old volumes (this will delete all data)...
    docker-compose down -v
)

REM Clean build cache
echo [INFO] Cleaning build cache...
docker builder prune -af

REM Build images
echo [INFO] Building Docker images...
docker-compose build --no-cache

REM Start services
echo [INFO] Starting services...
docker-compose up -d

REM Wait for services to be ready
echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ==========================================
echo    Startup Complete!
echo ==========================================
echo.
echo [INFO] Services are running:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/docs
echo.
echo [INFO] Useful commands:
echo   View logs:       docker-compose logs -f
echo   View backend:    docker-compose logs -f backend
echo   View frontend:   docker-compose logs -f frontend
echo   Stop all:        docker-compose down
echo   Restart:         docker-compose restart
echo.
echo [INFO] To create an admin user, run:
echo   docker-compose exec backend python scripts/create_admin.py --username admin --password admin123
echo.
