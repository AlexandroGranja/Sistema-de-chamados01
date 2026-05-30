# Gerenciamento de Telefones — Sistema Interno TI

Painel de controle de linhas telefônicas por equipe, integrado ao Sistema de Chamados TI.  
Backend PostgreSQL compartilhado entre os dois sistemas, com SSO e auditoria completa.

---

## Visão geral

| Componente | Tecnologia | Porta padrão |
|---|---|---|
| Gerenciamento (painel) | Python + Streamlit | 8501 |
| API de Chamados | Python + FastAPI | 8000 |
| Banco de dados | PostgreSQL 14+ | 5432 |

---

## Pré-requisitos

- Python 3.10+
- PostgreSQL 14+
- `pip` e `venv`

---

## Instalação rápida

**Windows:** dê duplo clique em `ativador.bat` — instala dependências e inicia o sistema.  
**Linux/Servidor:** `chmod +x ativador.sh && ./ativador.sh`

---

## Instalação manual

### 1. Clonar e preparar ambiente

```bash
git clone <url-do-repositorio>
cd "Planilhas Telefones"

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` e preencha todos os campos. **Nunca commite o `.env`** — ele está no `.gitignore`.

Para gerar chaves seguras:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

| Variável | Obrigatório | Descrição |
|---|---|---|
| `DATABASE_URL` | Sim | URL de conexão PostgreSQL |
| `COOKIES_PASSWORD` | Sim | Chave de criptografia dos cookies de sessão |
| `JWT_SECRET` | Sim | Chave de assinatura dos tokens JWT |
| `CHAMADOS_APP_URL` | Sim | URL do frontend React do sistema de chamados |
| `ALLOWED_ORIGINS` | Produção | Origens permitidas no CORS (separadas por vírgula) |
| `FORCE_HTTPS` | Produção | `true` quando SSL estiver ativo no servidor |
| `ENV` | Produção | `production` desabilita `/docs` da API |

### 3. Inicializar o banco de dados

```bash
python scripts/init_postgres.py
```

Migração do SQLite legado (se existir):
```bash
python scripts/migrate_sqlite_to_postgres.py
```

### 4. Criar o primeiro administrador

```bash
python scripts/criar_admin.py
```

### 5. Executar

**Painel Streamlit:**
```bash
python run.py
```
Acesse: http://localhost:8501

**API de Chamados (FastAPI):**
```bash
cd "Sistema de Chamados TI/backend"
python run.py
```
Docs (apenas `ENV=development`): http://localhost:8000/docs

---

## Deploy em produção (Linux + Nginx + SSL)

### Systemd — Painel Streamlit

Crie `/etc/systemd/system/gerenciamento-tel.service`:

```ini
[Unit]
Description=Gerenciamento de Telefones (Streamlit)
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/gerenciamento-telefones
EnvironmentFile=/var/www/gerenciamento-telefones/.env
ExecStart=/var/www/gerenciamento-telefones/.venv/bin/python run.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Systemd — API de Chamados

Crie `/etc/systemd/system/chamados-api.service`:

```ini
[Unit]
Description=Sistema de Chamados TI - API (FastAPI)
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/gerenciamento-telefones/Sistema de Chamados TI/backend
EnvironmentFile=/var/www/gerenciamento-telefones/.env
ExecStart=/var/www/gerenciamento-telefones/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ativar os serviços:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gerenciamento-tel chamados-api
sudo systemctl status gerenciamento-tel chamados-api
```

### Nginx + SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com.br
```

Bloco de configuração (`/etc/nginx/sites-available/gerenciamento`):

```nginx
server {
    listen 443 ssl;
    server_name seu-dominio.com.br;

    ssl_certificate     /etc/letsencrypt/live/seu-dominio.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com.br/privkey.pem;

    # Painel Streamlit
    location / {
        proxy_pass         http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # API de Chamados
    location /api/ {
        proxy_pass       http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name seu-dominio.com.br;
    return 301 https://$host$request_uri;
}
```

Com SSL ativo, adicione ao `.env`:
```
FORCE_HTTPS=true
ALLOWED_ORIGINS=https://seu-dominio.com.br
ENV=production
```

---

## Segurança

| Item | Status |
|---|---|
| `.env` protegido pelo `.gitignore` | Implementado |
| Sem secrets hardcoded no código | Implementado |
| Senhas com bcrypt (cost 12) + rehash automático | Implementado |
| Cookies de sessão criptografados (AES) | Implementado |
| JWT HS256 com `exp`, `jti`, `type` | Implementado |
| SSO de uso único (token hex-64, expira em 5 min) | Implementado |
| Rotas da API protegidas por JWT | Implementado |
| CORS com origens restritas | Implementado |
| Security headers HTTP (X-Frame-Options, etc.) | Implementado |
| SQL parametrizado (sem concatenação de input) | Implementado |
| Auditoria completa de ações no banco | Implementado |
| Documentação da API desabilitada em produção | Implementado |

---

## Integração com Chamados (parâmetros de URL)

O painel aceita parâmetros de URL para vincular automaticamente a um chamado aberto:

```
http://localhost:8501/?chamado_id=123&linha=11999999999&segmento_chamado=Alimento&return_url=https://sistema.exemplo/chamados/123
```

Parâmetros suportados: `chamado_id`, `id_chamado`, `ticket_id`, `chamado`, `linha`, `segmento_chamado`, `equipe_chamado`, `return_url`

---

## Estrutura do projeto

```
.
├── app.py                          # Aplicação Streamlit principal
├── run.py                          # Entry point Streamlit
├── requirements.txt
├── .env.example                    # Modelo de configuração
├── .gitignore
├── src/
│   ├── components/sidebar.py       # Sidebar + CSS + temas claro/escuro
│   ├── core/config.py              # Constantes e variáveis de ambiente
│   ├── db/
│   │   ├── repository.py           # Acesso ao banco (PostgreSQL/SQLite)
│   │   └── migrations.py           # Migrações de schema
│   └── pages/config_admin.py       # Página de administração
├── Sistema de Chamados TI/
│   └── backend/
│       ├── run.py
│       └── app/
│           ├── main.py             # FastAPI: CORS, headers, routers
│           ├── api/
│           │   ├── deps.py         # verify_token (JWT auth)
│           │   └── v1/endpoints/
│           │       ├── auth.py     # POST /api/auth/sso-exchange
│           │       └── telefones.py # 5 fluxos ciclo de vida de linhas
│           └── services/telefones_service.py
├── scripts/
│   ├── init_postgres.py
│   ├── criar_admin.py
│   └── migrate_sqlite_to_postgres.py
└── docs/
```

---

## Manutenção

```bash
# Ver logs em tempo real
sudo journalctl -u gerenciamento-tel -f
sudo journalctl -u chamados-api -f

# Reiniciar após atualização
sudo systemctl restart gerenciamento-tel chamados-api

# Backup do banco
pg_dump -U postgres gerenciamento_telefones > backup_$(date +%Y%m%d).sql
```
