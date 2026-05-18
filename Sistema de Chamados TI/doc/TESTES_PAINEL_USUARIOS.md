# Testes do painel de usuários (admin)

## Problema corrigido: e-mail não atualizava

Na rota `PUT /api/users/{id}`, a verificação de **e-mail duplicado** buscava qualquer usuário com o mesmo e-mail **sem excluir o próprio id**. Ao salvar uma alteração de e-mail, o backend encontrava **o próprio registro** e respondia `400 Email já cadastrado`, sem aplicar a mudança.

**Correção:** comparação **case-insensitive** e `User.id != user_id` na busca de duplicata.

Além disso, a lista e o retorno de criação **não devem** alterar `user.email` no objeto ORM só para exibição (risco de estado inconsistente). Agora usa-se `_user_schema_response()` com `model_copy` apenas na resposta JSON.

## Como testar manualmente

1. Suba o backend (`uvicorn`) e faça login como **admin** no app.
2. Abra **Usuários**, **Editar** em um usuário da equipe, altere o **e-mail**, **Salvar** — deve aparecer sucesso e a tabela deve mostrar o novo e-mail após recarregar.
3. **Criar** usuário (admin/técnico e, se quiser, tipo “só abre chamado”).
4. **Redefinir senha** e tentar login com o usuário editado.
5. **Excluir** outro usuário (não o seu): escolha **Só desativar** ou **Excluir do banco** (remoção permanente; bloqueada se houver chamados no PostgreSQL unificado para esse solicitante).

## API

- `DELETE /api/users/{id}` — apenas inativa (`is_active=false`).
- `DELETE /api/users/{id}?permanent=true` — remove o registro e dependências (e `usuarios_app` quando aplicável).

## Teste rápido via API (PowerShell)

Substitua `TOKEN` pelo JWT do admin (`access_token` após login).

```powershell
$TOKEN = "SEU_JWT"
$base = "http://localhost:8000/api"

# Listar
Invoke-RestMethod -Uri "$base/users?limit=50" -Headers @{ Authorization = "Bearer $TOKEN" }

# Atualizar e-mail do usuário id 2 (exemplo)
$body = '{"name":"Nome","email":"novo.email@empresa.com.br","department":"TI","is_active":true,"role":"admin","position":"Administrador"}'
Invoke-RestMethod -Uri "$base/users/2" -Method PUT -Headers @{ Authorization = "Bearer $TOKEN" } -ContentType "application/json" -Body $body
```

Se retornar `200` com o novo `email` no JSON, o fluxo com banco está ok.
