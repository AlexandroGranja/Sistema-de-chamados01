-- Remove autenticação local substituída pelo Keycloak
-- Executar APÓS confirmar que todos usuários migraram e Keycloak funciona

BEGIN;

-- Remove SSO bridge (Keycloak gerencia SSO via cookie de sessão)
DROP TABLE IF EXISTS sso_codes CASCADE;

-- Remove sessões locais (Keycloak gerencia sessões)
DROP TABLE IF EXISTS sessoes CASCADE;

-- Remove tokens de reset de senha (Keycloak gerencia password reset)
DROP TABLE IF EXISTS password_reset_tokens CASCADE;

-- Remove colunas de autenticação local da tabela de usuários
-- Manter: username, is_admin, email, auth_provider, ativo (FKs e auditoria)
ALTER TABLE usuarios_app
  DROP COLUMN IF EXISTS password_hash,
  DROP COLUMN IF EXISTS salt;

-- Marcar todos como autenticados via keycloak
UPDATE usuarios_app SET auth_provider = 'keycloak' WHERE auth_provider = 'local' OR auth_provider IS NULL;

COMMIT;
