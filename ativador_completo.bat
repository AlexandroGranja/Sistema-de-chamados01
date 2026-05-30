@echo off
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo   INICIADOR COMPLETO - Gerenciamento + Chamados
echo ============================================
echo.

set "ROOT=%~dp0"
set "CHAMADOS_DIR=%ROOT%Sistema de Chamados TI"
set "BACKEND_DIR=%CHAMADOS_DIR%\backend"
set "FRONTEND_DIR=%CHAMADOS_DIR%\frontend"

REM Evita conflito de porta
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000"') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":3000"') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8501"') do taskkill /F /PID %%p >nul 2>&1

REM =======================
REM BACKEND Chamados - porta 8000
REM =======================
echo [1/3] Backend Chamados...
set "PY_BACKEND=%BACKEND_DIR%\venv\Scripts\python.exe"
if not exist "%PY_BACKEND%" (
  pushd "%BACKEND_DIR%"
  echo Criando venv backend...
  python -m venv venv
  call venv\Scripts\pip.exe install --upgrade pip
  call venv\Scripts\pip.exe install -r requirements.txt
  popd
)

pushd "%BACKEND_DIR%"
echo Iniciando API na porta 8000...
start "Chamados-API" /MIN /D "%BACKEND_DIR%" cmd /c "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
popd

timeout /t 4 /nobreak >nul

REM =======================
REM FRONTEND Chamados - porta 3000
REM =======================
echo [2/3] Frontend Chamados...
pushd "%FRONTEND_DIR%"
if not exist "node_modules" (
  echo Instalando dependencias frontend - primeira vez pode demorar...
  call npm install
  if errorlevel 1 (
    echo [ERRO] npm install falhou.
    popd
    pause
    exit /b 1
  )
)
echo Iniciando Web na porta 3000...
start "Chamados-Web" /MIN /D "%FRONTEND_DIR%" cmd /c "npm run dev -- --host 0.0.0.0 --port 3000"
popd

timeout /t 4 /nobreak >nul

REM =======================
REM GERENCIAMENTO - porta 8501
REM =======================
echo [3/3] Gerenciamento de Telefones...

set "PY_GER=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PY_GER%" (
  pushd "%ROOT%"
  echo Criando ambiente virtual do Gerenciamento...
  python -m venv .venv
  call .venv\Scripts\pip.exe install --upgrade pip
  call .venv\Scripts\pip.exe install -r requirements.txt
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do Gerenciamento.
    popd
    pause
    exit /b 1
  )
  popd
) else (
  "%PY_GER%" -c "import streamlit" >nul 2>&1
  if errorlevel 1 (
    echo Instalando dependencias faltantes do Gerenciamento...
    pushd "%ROOT%"
    call .venv\Scripts\pip.exe install -r requirements.txt
    popd
  )
)

pushd "%ROOT%"
echo Iniciando Streamlit na porta 8501...
start "Gerenciamento-Telefones" /MIN /D "%ROOT%" cmd /c ".venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port 8501"
popd

timeout /t 3 /nobreak >nul

echo.
echo Servicos iniciados em janelas minimizadas.
echo.
echo - Gerenciamento: http://localhost:8501
echo - Chamados web: http://localhost:3000
echo - Chamados API: http://localhost:8000/docs
echo.
echo Se alguma URL nao abrir, aguarde ~30s e tente de novo.
echo Para encerrar, feche as janelas Chamados-API, Chamados-Web e Gerenciamento-Telefones.
echo.
pause
