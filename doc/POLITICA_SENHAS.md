# Política de senhas — Gerenciamento + Chamados

## Fonte da verdade

| Tabela | App | Função |
|--------|-----|--------|
| **`usuarios_app`** | Gerenciamento (Streamlit) + login unificado | Senha real do operador |
| **`users`** | Chamados (React) | Espelho para FK/JWT; senha bcrypt é **placeholder** quando o usuário veio do Gerenciamento |

**Regra prática:** altere a senha no **Gerenciamento** (Configuração → usuários). Essa senha vale para os dois apps após sync.

---

## Como a senha é armazenada

### Gerenciamento (`usuarios_app`)

- Algoritmo: **SHA256(salt + senha)** com salt aleatório por usuário.
- Mínimo: **4 caracteres** (validação do app).

### Chamados (`users`)

- Usuários sincronizados do Gerenciamento recebem hash bcrypt **aleatório** (não usado no login normal).
- Usuários cadastrados só no portal Chamados usam bcrypt real em `users`.

---

## Login no Chamados (React)

Ordem de validação (PostgreSQL unificado):

1. Busca em **`usuarios_app`** → valida SHA256+salt (**mesma senha do Streamlit**).
2. Se falhar, tenta bcrypt em **`users`** vinculado (`snipe_user_id`) — ex.: admin alterou senha só no painel Chamados antigo.
3. Contas só em `users` (portal) seguem fluxo bcrypt.

Por isso pode parecer haver “duas senhas”: o caminho correto é **sempre a senha do Gerenciamento** após sync.

---

## Sincronização de usuários (B5)

Após **criar** ou **redefinir** usuário no Gerenciamento, rode o sync para espelhar em `users`:

```powershell
python -m scripts.sync_usuarios_chamados
# ou inspecionar antes:
python -m scripts.sync_usuarios_chamados --dry-run
```

Também disponível em **Configuração → Sincronização com Chamados** no Streamlit (admin).

O sync automático roda após **Criar usuário** no admin quando PostgreSQL está configurado.

---

## Redefinir senha

| Onde | Comando / tela |
|------|----------------|
| Streamlit (admin) | Configuração → Gerenciar usuários → Alterar senha |
| CLI emergência | `python -m scripts.redefinir_senha` |
| Chamados isolado | Evitar — prefira Gerenciamento + sync |

Após redefinir no Streamlit, **não** é necessário sync só por troca de senha (login lê `usuarios_app`).

---

## SSO

O botão **📌 Chamados** no Streamlit abre o React com `sso_code` — **não usa senha** naquele momento. O usuário precisa existir em `usuarios_app` e, preferencialmente, espelhado em `users`.

---

*Fase B5 — maio/2026. Ver também [BANCO_UNIFICADO.md](../Sistema%20de%20Chamados%20TI/doc/BANCO_UNIFICADO.md).*
