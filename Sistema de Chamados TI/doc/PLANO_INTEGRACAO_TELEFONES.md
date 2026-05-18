# Plano de Integracao - Sistema de Chamados Prosper x Gerenciamento de Telefones

Este documento registra o plano para a proxima etapa do projeto: integrar o Sistema de Chamados Prosper com o sistema de Gerenciamento de Telefones.

## Objetivo da integracao

Permitir que o Sistema de Chamados consulte dados de linhas e aparelhos do Gerenciamento de Telefones para:

- localizar aparelho/linha por colaborador, patrimonio, serie ou numero de linha;
- preencher automaticamente informacoes em chamados;
- padronizar dados de equipe, segmento e status operacional;
- reduzir erros manuais no fluxo de abertura e encerramento de chamados.

## Contexto tecnico levantado

Projeto externo analisado: `C:\Users\TI02\Desktop\Planilhas Telefones`

Principais pontos:

- Aplicacao principal em `Streamlit` (`app.py`);
- Banco local `SQLite` em `data/db/gerenciamento_telefones.db`;
- Tabela principal: `linhas`;
- Dados alimentados por planilhas e regras via `scripts/sync_db.py`;
- Nao ha API REST pronta atualmente (somente app + acesso SQLite).

## Campos relevantes para a integracao

Tabela `linhas` (fonte principal):

- identificacao: `linha`, `codigo`, `nome`, `equipe_padrao`, `segmento`, `modo`;
- aparelho: `aparelho`, `modelo`, `imei_a`, `imei_b`, `patrimonio`, `numero_serie`, `operadora`;
- organizacao: `gestor`, `supervisor`, `grupo_equipe`, `localidade`;
- status de uso: `modo` (`ativas` / `desativadas`).

## Estrategia recomendada (fase 1)

Integracao por leitura direta do banco SQLite do Gerenciamento de Telefones, no backend do Sistema de Chamados.

Motivo:

- menor tempo de entrega;
- evita depender de API nova no outro sistema neste momento;
- facilita prototipar e validar fluxo com dados reais.

## Fases de implementacao

### Fase 1 - Backend de consulta

- Criar servico no backend do chamados para leitura em modo somente-leitura do banco de telefones;
- Criar endpoints internos para busca por:
  - linha;
  - nome;
  - patrimonio;
  - numero de serie;
- Retornar dados normalizados para o frontend.

### Fase 2 - Uso no frontend

- Na abertura de chamado, permitir busca de linha/aparelho;
- Auto preencher modelo, patrimonio, serie e equipe quando encontrado;
- Exibir alerta quando houver inconsistencias (ex.: linha desativada).

### Fase 3 - Historico e auditoria

- Salvar snapshot dos dados de telefone no metadata do chamado;
- Registrar origem da informacao (`gerenciamento_telefones`) para rastreabilidade.

## Decisoes em aberto (para confirmar antes de codar)

- Caminho fixo ou configuravel do banco `gerenciamento_telefones.db` no ambiente de producao;
- Frequencia de sincronizacao das planilhas no sistema de telefones;
- Regras quando houver divergencia entre dados do chamado e dados do gerenciamento;
- Permissoes: quais perfis poderao consultar dados de telefone.

## Riscos e cuidados

- Dependencia de arquivo local SQLite (conectividade e permissao em servidor);
- Banco sem sincronizacao recente pode gerar dados desatualizados;
- Necessidade de fallback quando o banco externo estiver indisponivel.

## Checklist para iniciar a integracao (proxima etapa)

- [ ] Definir caminho oficial do banco de telefones no servidor;
- [ ] Adicionar variavel de ambiente no backend de chamados para este caminho;
- [ ] Implementar servico de leitura e endpoints de consulta;
- [ ] Integrar tela de abertura de chamados com busca de telefone/aparelho;
- [ ] Validar com casos reais (ativos, inativos, manutencao, sem patrimonio);
- [ ] Atualizar README com passo a passo de configuracao da integracao.

---

Documento criado para retomada da integracao apos as proximas alteracoes do sistema.
