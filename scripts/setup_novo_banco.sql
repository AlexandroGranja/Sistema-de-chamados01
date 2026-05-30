-- Execute no pgAdmin: conectado ao banco "postgres" (Query Tool)
-- Cria o banco compartilhado Gerenciamento + Chamados TI

-- 1) Banco (ajuste o nome se quiser outro)
CREATE DATABASE gerenciamento_telefones
    WITH OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Portuguese_Brazil.1252'
    LC_CTYPE = 'Portuguese_Brazil.1252'
    TEMPLATE = template0;

-- 2) Opcional: usuario dedicado (descomente e troque a senha)
-- CREATE USER telefones WITH PASSWORD 'sua_senha_segura';
-- ALTER DATABASE gerenciamento_telefones OWNER TO telefones;
-- GRANT ALL PRIVILEGES ON DATABASE gerenciamento_telefones TO telefones;

-- Depois de criar o banco, rode no terminal do projeto:
--   python -m scripts.init_postgres
--   cd "Sistema de Chamados TI/backend" && alembic upgrade head
--   python -m scripts.verificar_banco
