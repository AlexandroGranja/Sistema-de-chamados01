@echo off
setlocal
title Ativador Completo - Sistema de Chamados Prosper

REM Sempre partir da pasta do script
cd /d "%~dp0"

echo ============================================================
echo   Ativador Completo - Sistema de Chamados Prosper
echo ============================================================
echo.

REM ------------------------------------------------------------------
REM 1) Verificacoes basicas
REM ------------------------------------------------------------------

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale Python 3.10+ e tente novamente.
  goto :fail
)

where node >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Node.js nao encontrado no PATH.
  echo Instale Node.js 18+ e tente novamente.
  goto :fail
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERRO] npm nao encontrado no PATH.
  goto :fail
)

REM ------------------------------------------------------------------
REM 2) Backend - criar/atualizar venv e instalar dependencias
REM ------------------------------------------------------------------

echo [1/5] Preparando backend...
if not exist "backend\venv\Scripts\python.exe" (
  echo     Criando ambiente virtual do backend com Python 3.10...
  if exist "C:\Users\TI02\AppData\Local\Programs\Python\Python310\python.exe" (
    "C:\Users\TI02\AppData\Local\Programs\Python\Python310\python.exe" -m venv "backend\venv"
  ) else (
    python -m venv "backend\venv"
  )
  if errorlevel 1 (
    echo [ERRO] Falha ao criar venv do backend.
    goto :fail
  )
)

call "backend\venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERRO] Falha ao ativar venv do backend.
  goto :fail
)

echo [2/5] Instalando/atualizando dependencias do backend...
python -m pip install --upgrade pip
pip install -r "backend\requirements.txt"
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias do backend.
  goto :fail
)

echo.
set /p CREATE_ADMIN="Deseja criar/atualizar o usuario admin agora? (S/N): "
if /I "%CREATE_ADMIN%"=="S" (
  echo Executando scripts\create_admin.py...
  python "backend\scripts\create_admin.py"
  if errorlevel 1 (
    echo [AVISO] create_admin.py retornou erro. Verifique backend\.env e configuracao do banco.
  )
)

call deactivate >nul 2>&1

REM ------------------------------------------------------------------
REM 3) Frontend - instalar dependencias
REM ------------------------------------------------------------------

echo.
echo [3/5] Preparando frontend...
if not exist "frontend\node_modules\.bin\vite.cmd" (
  echo     Dependencias frontend ausentes. Instalando...
  pushd "frontend"
  npm install
  if errorlevel 1 (
    popd
    echo [ERRO] Falha ao instalar dependencias do frontend.
    goto :fail
  )
  popd
) else (
  echo     Frontend OK - dependencias ja instaladas.
)

REM ------------------------------------------------------------------
REM 4) Iniciar backend e frontend
REM ------------------------------------------------------------------

echo.
echo [4/5] Iniciando backend...
start "Backend - Sistema de Chamados Prosper" cmd /k "cd /d backend && call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [5/5] Iniciando frontend...
start "Frontend - Sistema de Chamados Prosper" cmd /k "cd /d frontend && npm run dev"

echo.
echo Servicos iniciados com sucesso.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Aguarde alguns segundos para os servicos terminarem de subir.
pause
exit /b 0

:fail
echo.
echo Ativacao interrompida.
pause
exit /b 1

