# Setup interativo do PostgreSQL local (Windows)
# Uso: powershell -ExecutionPolicy Bypass -File scripts/setup_banco_local.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup PostgreSQL - Gerenciamento + Chamados" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$psql = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
if (-not (Test-Path $psql)) {
    $found = Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter "psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $psql = $found.FullName } else { throw "psql.exe nao encontrado. Instale PostgreSQL ou ajuste o caminho." }
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$dbName = Read-Host "Nome do banco [gerenciamento_telefones]"
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "gerenciamento_telefones" }

$dbUser = Read-Host "Usuario do app [telefones]"
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "telefones" }

$dbPassPlain = Read-Host "Senha do usuario '$dbUser' (app)" -AsSecureString
$dbPassBstr = [Runtime.InteropServices.Marshal]::SecureStringToBGlobalAllocUnicode($dbPassPlain)
$dbPass = [Runtime.InteropServices.Marshal]::PtrToStringBGlobalAlloc($dbPassBstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBGlobalAllocUnicode($dbPassBstr)

$pgSuper = Read-Host "Usuario superuser PostgreSQL [postgres]"
if ([string]::IsNullOrWhiteSpace($pgSuper)) { $pgSuper = "postgres" }

$pgPassPlain = Read-Host "Senha do superuser '$pgSuper'" -AsSecureString
$pgPassBstr = [Runtime.InteropServices.Marshal]::SecureStringToBGlobalAllocUnicode($pgPassPlain)
$pgPass = [Runtime.InteropServices.Marshal]::PtrToStringBGlobalAlloc($pgPassBstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBGlobalAllocUnicode($pgPassBstr)

$env:PGPASSWORD = $pgPass

Write-Host ""
Write-Host "[1/4] Criando usuario e banco..." -ForegroundColor Yellow

$sql = @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$dbUser') THEN
    CREATE USER $dbUser WITH PASSWORD '$($dbPass -replace "'", "''")';
  ELSE
    ALTER USER $dbUser WITH PASSWORD '$($dbPass -replace "'", "''")';
  END IF;
END
`$`$;

SELECT 'CREATE DATABASE $dbName OWNER $dbUser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$dbName')\gexec

GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;
"@

$sql | & $psql -h localhost -U $pgSuper -d postgres -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    throw "Falha ao criar banco. Verifique a senha do superuser."
}

Write-Host "[OK] Banco '$dbName' pronto." -ForegroundColor Green

Write-Host "[2/4] Gravando .env na raiz..." -ForegroundColor Yellow

$encodedPass = [Uri]::EscapeDataString($dbPass)
$dbUrl = "postgresql://${dbUser}:${encodedPass}@localhost:5432/${dbName}"

$envContent = @"
DATABASE_URL=$dbUrl
APP_TIMEZONE=America/Sao_Paulo
COOKIES_PASSWORD=planilhas_telefones_secret_2024
CHAMADOS_APP_URL=http://localhost:3000
"@

Set-Content -Path (Join-Path $root ".env") -Value $envContent -Encoding UTF8
Write-Host "[OK] .env criado na raiz." -ForegroundColor Green

Write-Host "[3/4] Gravando backend/.env..." -ForegroundColor Yellow

$backendEnvPath = Join-Path $root "Sistema de Chamados TI\backend\.env"
$backendExample = Join-Path $root "Sistema de Chamados TI\backend\env.example"
$backendBase = if (Test-Path $backendExample) { Get-Content $backendExample -Raw } else { "" }
$backendBase = $backendBase -replace '(?m)^DATABASE_URL=.*$', "DATABASE_URL=$dbUrl"
if ($backendBase -notmatch '(?m)^DATABASE_URL=') {
    $backendBase = "DATABASE_URL=$dbUrl`n" + $backendBase
}
Set-Content -Path $backendEnvPath -Value $backendBase -Encoding UTF8
Write-Host "[OK] backend/.env atualizado." -ForegroundColor Green

Write-Host "[4/4] Criando tabelas (init_postgres + alembic)..." -ForegroundColor Yellow

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Criando venv do Gerenciamento..."
    python -m venv (Join-Path $root ".venv")
    & (Join-Path $root ".venv\Scripts\pip.exe") install -r (Join-Path $root "requirements.txt") -q
}

& $py -m scripts.init_postgres
if ($LASTEXITCODE -ne 0) { throw "init_postgres falhou." }

$backendDir = Join-Path $root "Sistema de Chamados TI\backend"
$pyBackend = Join-Path $backendDir "venv\Scripts\python.exe"
if (-not (Test-Path $pyBackend)) {
    Write-Host "Criando venv do backend Chamados..."
    python -m venv (Join-Path $backendDir "venv")
    & (Join-Path $backendDir "venv\Scripts\pip.exe") install -r (Join-Path $backendDir "requirements.txt") -q
}

Push-Location $backendDir
& (Join-Path $backendDir "venv\Scripts\alembic.exe") upgrade head
Pop-Location

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup concluido!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos passos:"
Write-Host "  1. python -m scripts.verificar_banco"
Write-Host "  2. python -m scripts.criar_admin   (primeiro login)"
Write-Host "  3. ativador_completo.bat"
Write-Host ""
