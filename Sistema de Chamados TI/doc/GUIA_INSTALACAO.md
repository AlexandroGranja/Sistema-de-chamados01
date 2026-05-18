# 🚀 Guia de Instalação - Sistema de Chamados TI

Este guia irá ajudá-lo a configurar o sistema completo em seu ambiente local.

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **PostgreSQL 14+** - [Download](https://www.postgresql.org/download/)
- **Git** (opcional) - [Download](https://git-scm.com/)

## 🔧 Instalação do Backend

### 1. Navegar para a pasta do backend

```bash
cd backend
```

### 2. Criar ambiente virtual

```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### 3. Ativar ambiente virtual

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

### 5. Configurar banco de dados PostgreSQL

#### 5.1. Criar banco de dados

Abra o PostgreSQL (pgAdmin ou linha de comando) e execute:

```sql
CREATE DATABASE chamados_ti;
```

Ou via linha de comando:

```bash
createdb chamados_ti
```

#### 5.2. Configurar variáveis de ambiente

Copie o arquivo de exemplo:

```bash
# Windows
copy env.example .env

# Linux/Mac
cp env.example .env
```

Edite o arquivo `.env` e configure:

```env
# Database - Ajuste com suas credenciais
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/chamados_ti

# JWT - Gere uma chave secreta forte
SECRET_KEY=sua-chave-secreta-aqui-mude-em-producao

# Email - Configure com suas credenciais do email-ssl.com.br
SMTP_HOST=email-ssl.com.br
SMTP_PORT=587
SMTP_USER=seu-email@promio.com.br
SMTP_PASSWORD=sua-senha-email
SMTP_FROM=noreply@promio.com.br
SMTP_USE_TLS=True

# Application
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
DEBUG=True
ENVIRONMENT=development

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 6. Executar migrations

```bash
# Criar as tabelas no banco de dados
alembic upgrade head
```

### 7. Criar usuário administrador inicial

```bash
python scripts/create_admin.py
```

Isso criará um usuário admin com:
- **Email**: `admin@promio.com.br`
- **Senha**: `admin123`

⚠️ **IMPORTANTE**: Altere a senha após o primeiro login!

### 8. Iniciar servidor backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Ou:

```bash
python -m app.main
```

O backend estará disponível em: `http://localhost:8000`

Documentação da API: `http://localhost:8000/api/docs`

---

## 🎨 Instalação do Frontend

### 1. Abrir novo terminal e navegar para a pasta do frontend

```bash
cd frontend
```

### 2. Instalar dependências

```bash
npm install
```

### 3. Configurar variáveis de ambiente (opcional)

Crie um arquivo `.env` na pasta `frontend`:

```env
VITE_API_URL=http://localhost:8000
```

### 4. Iniciar servidor de desenvolvimento

```bash
npm run dev
```

O frontend estará disponível em: `http://localhost:3000`

---

## ✅ Verificação da Instalação

### Testar Backend

1. Acesse: `http://localhost:8000/api/docs`
2. Você deve ver a documentação interativa da API
3. Teste o endpoint `/health` - deve retornar `{"status": "healthy"}`

### Testar Frontend

1. Acesse: `http://localhost:3000`
2. Você deve ser redirecionado para a página de login
3. Faça login com:
   - Email: `admin@promio.com.br`
   - Senha: `admin123`

### Testar Autenticação

1. No frontend, faça login
2. Você deve ser redirecionado para o dashboard
3. Verifique se seu nome aparece no dashboard

---

## 🐛 Solução de Problemas

### Erro: "Module not found"

**Solução**: Certifique-se de que o ambiente virtual está ativado e todas as dependências foram instaladas.

```bash
pip install -r requirements.txt
```

### Erro: "Could not connect to database"

**Solução**: 
1. Verifique se o PostgreSQL está rodando
2. Confirme as credenciais no arquivo `.env`
3. Teste a conexão:

```bash
psql -U seu_usuario -d chamados_ti
```

### Erro: "Port already in use"

**Solução**: Altere a porta no arquivo de configuração ou encerre o processo que está usando a porta.

### Erro no frontend: "Cannot connect to API"

**Solução**:
1. Verifique se o backend está rodando
2. Confirme a URL da API no arquivo `.env` do frontend
3. Verifique as configurações de CORS no backend

### Erro: "Alembic migration failed"

**Solução**:
1. Verifique se o banco de dados existe
2. Confirme a URL do banco no `.env`
3. Tente recriar as migrations:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## 📝 Próximos Passos

Após a instalação bem-sucedida:

1. ✅ Altere a senha do usuário admin
2. ✅ Configure as credenciais de email corretamente
3. ✅ Crie mais usuários através do painel admin (quando disponível)
4. ✅ Explore a documentação da API em `/api/docs`
5. ✅ Comece a usar o sistema!

---

## 🔒 Segurança

⚠️ **IMPORTANTE PARA PRODUÇÃO**:

1. Altere o `SECRET_KEY` para uma chave forte e aleatória
2. Altere a senha do admin
3. Configure `DEBUG=False` em produção
4. Use HTTPS em produção
5. Configure firewall adequadamente
6. Faça backup regular do banco de dados
7. Mantenha as dependências atualizadas

---

## 📞 Suporte

Se encontrar problemas durante a instalação:

1. Verifique os logs do backend no terminal
2. Verifique o console do navegador (F12) para erros do frontend
3. Consulte a documentação do mapamental
4. Verifique se todos os pré-requisitos estão instalados corretamente

---

**Boa sorte com a instalação! 🚀**

