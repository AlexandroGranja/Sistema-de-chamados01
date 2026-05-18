# 🗺️ MAPAMENTAL - Sistema de Chamados TI

## 📋 Visão Geral do Sistema

Sistema completo de gestão de chamados para o setor de TI, desenvolvido com arquitetura moderna, permitindo gerenciamento eficiente de solicitações, incidentes e manutenções.

---

## 🏗️ ARQUITETURA DO SISTEMA

### Stack Tecnológica

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  - Interface responsiva (Desktop + Mobile)                   │
│  - Dashboard interativo                                      │
│  - Notificações em tempo real                                │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                 BACKEND (Python - FastAPI)                   │
│  - API RESTful completa                                      │
│  - Autenticação JWT                                          │
│  - Validação de dados                                        │
│  - Lógica de negócio                                         │
└─────────────────────────────────────────────────────────────┘
                            ↕ ORM
┌─────────────────────────────────────────────────────────────┐
│              BANCO DE DADOS (PostgreSQL)                     │
│  - Dados relacionais                                         │
│  - Índices otimizados                                        │
│  - Backup automático                                         │
└─────────────────────────────────────────────────────────────┘
                            ↕ SMTP
┌─────────────────────────────────────────────────────────────┐
│          SERVIDOR DE EMAIL (email-ssl.com.br)                │
│  - Envio de notificações                                     │
│  - Alertas de procedimentos                                  │
│  - Confirmações de chamados                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 MÓDULOS DO SISTEMA

### 1. 🔐 MÓDULO DE AUTENTICAÇÃO E AUTORIZAÇÃO

#### 1.1 Autenticação
- **Login/Logout**
  - Autenticação via email/senha
  - Tokens JWT (JSON Web Tokens)
  - Refresh tokens para renovação automática
  - Recuperação de senha via email
  - Sessões seguras

#### 1.2 Níveis de Acesso (Roles)
- **Administrador (Admin)**
  - Acesso total ao sistema
  - Gerenciamento de usuários
  - Configurações do sistema
  - Relatórios completos
  
- **Técnico TI (Technician)**
  - Visualizar todos os chamados
  - Atribuir chamados a si mesmo
  - Atualizar status de chamados
  - Adicionar comentários e resoluções
  - Acessar dashboard técnico
  
- **Usuário Final (User)**
  - Criar novos chamados
  - Visualizar apenas seus próprios chamados
  - Adicionar comentários em seus chamados
  - Anexar arquivos
  - Receber notificações por email

- **Supervisor (Supervisor)** [Opcional]
  - Visualizar todos os chamados da equipe
  - Aprovar/rejeitar solicitações
  - Gerar relatórios da equipe

#### 1.3 Permissões Granulares
- Controle de permissões por funcionalidade
- Permissões customizáveis por role
- Auditoria de ações (log de quem fez o quê)

---

### 2. 👥 MÓDULO DE GERENCIAMENTO DE USUÁRIOS

#### 2.1 Painel Admin de Usuários
- **CRUD Completo de Usuários**
  - Criar usuário
  - Editar dados do usuário
  - Desativar/Ativar usuário
  - Excluir usuário (soft delete)
  
- **Campos do Usuário**
  - Nome completo
  - Email (único, usado para login)
  - Senha (criptografada)
  - Telefone
  - Departamento/Setor
  - Cargo
  - Nível de acesso (Role)
  - Data de cadastro
  - Último acesso
  - Status (Ativo/Inativo)
  - Foto de perfil (opcional)

#### 2.2 Funcionalidades Adicionais
- Busca e filtros avançados
- Importação em lote (CSV/Excel)
- Exportação de lista de usuários
- Histórico de alterações
- Reset de senha pelo admin
- Atribuição de múltiplos técnicos a departamentos

---

### 3. 🎫 MÓDULO DE CHAMADOS

#### 3.1 Tipos de Chamado
- **Incidente**
  - Problema que interrompe serviço
  - Prioridade: Crítica, Alta, Média, Baixa
  - SLA baseado na prioridade
  
- **Solicitação**
  - Requisição de serviço/equipamento
  - Aprovação necessária (opcional)
  - Prazo de atendimento
  
- **Manutenção**
  - Manutenção preventiva/corretiva
  - Agendamento
  - Checklist de procedimentos
  
- **Problema**
  - Problema recorrente
  - Vinculação a múltiplos incidentes
  - Análise de causa raiz

#### 3.2 Status do Chamado
- **Aberto** - Chamado recém-criado
- **Em Análise** - Técnico analisando
- **Em Andamento** - Sendo resolvido
- **Aguardando Usuário** - Aguardando resposta do usuário
- **Aguardando Terceiros** - Aguardando fornecedor/terceiro
- **Resolvido** - Solução aplicada, aguardando confirmação
- **Fechado** - Chamado finalizado
- **Cancelado** - Chamado cancelado

#### 3.3 Campos do Chamado
- **Informações Básicas**
  - ID único (numeração sequencial)
  - Título/Assunto
  - Descrição detalhada
  - Tipo de chamado
  - Categoria (Hardware, Software, Rede, Email, etc.)
  - Subcategoria
  - Prioridade
  - Urgência
  - Impacto
  
- **Atribuição**
  - Solicitante (usuário que criou)
  - Técnico responsável
  - Grupo de atendimento
  - Departamento
  
- **Datas e Prazos**
  - Data de abertura
  - Data prevista de resolução (SLA)
  - Data de início do atendimento
  - Data de resolução
  - Data de fechamento
  - Tempo de resposta
  - Tempo de resolução
  
- **Informações Adicionais**
  - Tags/Etiquetas
  - Localização/Filial
  - Equipamento relacionado
  - Observações internas (visível apenas para TI)

#### 3.4 Funcionalidades do Chamado
- **Criação**
  - Formulário intuitivo
  - Validação de campos obrigatórios
  - Sugestão de chamados similares
  - Upload de anexos (múltiplos arquivos)
  
- **Visualização**
  - Timeline de eventos
  - Histórico completo
  - Comentários públicos e privados
  - Anexos organizados
  - Informações de SLA
  
- **Atualização**
  - Adicionar comentários
  - Alterar status
  - Reatribuir técnico
  - Alterar prioridade
  - Adicionar resolução
  - Anexar arquivos
  
- **Busca e Filtros**
  - Busca por texto (título, descrição, ID)
  - Filtros por status, tipo, prioridade, técnico, data
  - Filtros salvos (favoritos)
  - Ordenação por diversos critérios

---

### 4. 💬 MÓDULO DE COMENTÁRIOS E INTERAÇÕES

#### 4.1 Comentários
- Comentários públicos (visível para solicitante)
- Comentários privados (apenas para TI)
- Menções de usuários (@usuario)
- Formatação de texto (rich text)
- Edição e exclusão de comentários próprios

#### 4.2 Timeline/Histórico
- Registro automático de todas as ações
- Quem fez, quando fez, o que fez
- Mudanças de status
- Atribuições
- Alterações de prioridade
- Visualização cronológica

---

### 5. 📎 MÓDULO DE ANEXOS

#### 5.1 Upload de Arquivos
- Múltiplos arquivos por chamado
- Tipos permitidos configuráveis
- Tamanho máximo configurável
- Validação de tipo e tamanho
- Armazenamento seguro

#### 5.2 Gerenciamento
- Visualização de anexos
- Download de arquivos
- Exclusão de anexos
- Preview de imagens
- Organização por data/tipo

---

### 6. 📊 MÓDULO DE DASHBOARD E RELATÓRIOS

#### 6.1 Dashboard Principal
- **Métricas Gerais**
  - Total de chamados abertos
  - Chamados em andamento
  - Chamados resolvidos (hoje/semana/mês)
  - Tempo médio de resolução
  - Taxa de satisfação
  
- **Gráficos**
  - Chamados por status (pizza)
  - Chamados por tipo (barras)
  - Chamados por prioridade
  - Chamados por categoria
  - Tendência temporal (linha)
  - Chamados por técnico
  - SLA compliance
  
- **Widgets Personalizáveis**
  - Meus chamados abertos
  - Chamados atribuídos a mim
  - Chamados críticos
  - Chamados próximos do SLA
  - Atividades recentes

#### 6.2 Dashboard do Técnico
- Chamados atribuídos
- Chamados em andamento
- Próximas ações
- Estatísticas pessoais
- Performance individual

#### 6.3 Dashboard do Usuário
- Meus chamados abertos
- Status dos meus chamados
- Histórico recente

#### 6.4 Relatórios
- **Relatórios Padrão**
  - Relatório de chamados por período
  - Relatório por técnico
  - Relatório por departamento
  - Relatório de SLA
  - Relatório de satisfação
  - Relatório de categorias
  
- **Exportação**
  - PDF
  - Excel (XLSX)
  - CSV
  
- **Agendamento**
  - Relatórios automáticos por email
  - Configuração de frequência

---

### 7. 📧 MÓDULO DE INTEGRAÇÃO DE EMAIL

#### 7.1 Configuração SMTP
- Servidor: email-ssl.com.br
- Porta SSL/TLS
- Autenticação
- Email remetente configurável
- Templates de email personalizáveis

#### 7.2 Notificações Automáticas
- **Ao Criar Chamado**
  - Confirmação para o solicitante
  - Notificação para técnicos do grupo
  - Notificação para supervisor (se configurado)
  
- **Ao Atualizar Status**
  - Notificação ao solicitante
  - Notificação ao técnico responsável
  
- **Ao Adicionar Comentário**
  - Notificação ao solicitante (se comentário público)
  - Notificação ao técnico (se comentário privado)
  
- **Ao Reatribuir**
  - Notificação ao novo técnico
  - Notificação ao técnico anterior
  
- **Ao Resolver**
  - Solicitação de confirmação ao usuário
  - Formulário de satisfação
  
- **Alertas de SLA**
  - Aviso quando próximo do prazo (ex: 80% do tempo)
  - Alerta quando SLA expirado
  - Notificação diária de chamados críticos

#### 7.3 Avisos de Procedimentos
- **Envio Manual**
  - Interface para criar e enviar avisos
  - Seleção de destinatários (todos, departamento, grupo)
  - Templates de procedimentos
  
- **Envio Automático**
  - Avisos baseados em eventos
  - Lembretes periódicos
  - Notificações de manutenções programadas

#### 7.4 Templates de Email
- Template de criação de chamado
- Template de atualização
- Template de resolução
- Template de aviso de procedimento
- Template de recuperação de senha
- Templates customizáveis (HTML)

---

### 8. 🔔 MÓDULO DE NOTIFICAÇÕES

#### 8.1 Notificações em Tempo Real
- WebSocket para notificações instantâneas
- Badge de notificações não lidas
- Notificações push no navegador
- Som de notificação (opcional)

#### 8.2 Tipos de Notificação
- Novo chamado atribuído
- Comentário em chamado
- Mudança de status
- Aproximação de SLA
- Mensagens do sistema

---

### 9. ⚙️ MÓDULO DE CONFIGURAÇÕES

#### 9.1 Configurações Gerais
- Nome do sistema
- Logo personalizado
- Cores do tema
- Idioma (português inicialmente)
- Fuso horário
- Formato de data/hora

#### 9.2 Configurações de SLA
- Tempos de SLA por prioridade
- Horários de funcionamento
- Dias úteis
- Feriados
- Regras de cálculo de SLA

#### 9.3 Configurações de Email
- Servidor SMTP
- Porta
- Credenciais
- Templates padrão
- Assinatura de email

#### 9.4 Configurações de Categorias
- Categorias de chamados
- Subcategorias
- Itens de configuração (CI)
- Grupos de atendimento

#### 9.5 Configurações de Anexos
- Tipos de arquivo permitidos
- Tamanho máximo
- Local de armazenamento

---

### 10. 🔍 MÓDULO DE BUSCA AVANÇADA

#### 10.1 Busca Global
- Busca em todos os chamados
- Busca em comentários
- Busca em anexos (nomes)
- Busca por ID, título, descrição

#### 10.2 Filtros Avançados
- Múltiplos filtros combinados
- Filtros por data (range)
- Filtros por técnico, departamento, categoria
- Filtros salvos
- Exportação de resultados filtrados

---

### 11. 📱 MÓDULO DE RESPONSIVIDADE

#### 11.1 Interface Mobile
- Layout adaptativo
- Menu hambúrguer
- Formulários otimizados para mobile
- Touch-friendly
- Visualização otimizada de chamados

#### 11.2 Interface Desktop
- Layout completo
- Múltiplas colunas
- Atalhos de teclado
- Drag and drop
- Visualização expandida

---

## 🗄️ ESTRUTURA DO BANCO DE DADOS

### Tabelas Principais

#### users (Usuários)
```sql
- id (PK)
- name
- email (unique)
- password_hash
- phone
- department
- position
- role (admin, technician, user, supervisor)
- avatar_url
- is_active
- created_at
- updated_at
- last_login
```

#### tickets (Chamados)
```sql
- id (PK)
- ticket_number (unique, sequencial)
- title
- description
- ticket_type (incident, request, maintenance, problem)
- category
- subcategory
- priority (critical, high, medium, low)
- urgency
- impact
- status
- requester_id (FK -> users)
- assigned_technician_id (FK -> users, nullable)
- group_id (FK -> groups, nullable)
- department_id (FK -> departments, nullable)
- location
- equipment_id (FK -> equipment, nullable)
- sla_due_date
- resolved_at
- closed_at
- created_at
- updated_at
```

#### comments (Comentários)
```sql
- id (PK)
- ticket_id (FK -> tickets)
- user_id (FK -> users)
- content
- is_private
- created_at
- updated_at
```

#### attachments (Anexos)
```sql
- id (PK)
- ticket_id (FK -> tickets)
- user_id (FK -> users)
- filename
- original_filename
- file_path
- file_size
- mime_type
- created_at
```

#### ticket_history (Histórico)
```sql
- id (PK)
- ticket_id (FK -> tickets)
- user_id (FK -> users)
- action_type (created, updated, status_changed, etc.)
- field_name
- old_value
- new_value
- created_at
```

#### notifications (Notificações)
```sql
- id (PK)
- user_id (FK -> users)
- ticket_id (FK -> tickets, nullable)
- type
- title
- message
- is_read
- created_at
```

#### groups (Grupos de Atendimento)
```sql
- id (PK)
- name
- description
- email
- is_active
- created_at
- updated_at
```

#### departments (Departamentos)
```sql
- id (PK)
- name
- description
- manager_id (FK -> users, nullable)
- created_at
- updated_at
```

#### categories (Categorias)
```sql
- id (PK)
- name
- description
- parent_id (FK -> categories, nullable)
- sla_hours
- is_active
- created_at
- updated_at
```

#### equipment (Equipamentos)
```sql
- id (PK)
- name
- asset_number
- serial_number
- type
- brand
- model
- location
- assigned_to (FK -> users, nullable)
- status
- created_at
- updated_at
```

#### email_templates (Templates de Email)
```sql
- id (PK)
- name
- subject
- body_html
- body_text
- type
- is_active
- created_at
- updated_at
```

#### settings (Configurações)
```sql
- id (PK)
- key (unique)
- value
- type (string, integer, boolean, json)
- description
- updated_at
```

---

## 🔌 API REST - ENDPOINTS PRINCIPAIS

### Autenticação
```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
POST   /api/auth/forgot-password
POST   /api/auth/reset-password
GET    /api/auth/me
```

### Usuários
```
GET    /api/users
GET    /api/users/:id
POST   /api/users
PUT    /api/users/:id
DELETE /api/users/:id
GET    /api/users/:id/tickets
PUT    /api/users/:id/password
```

### Chamados
```
GET    /api/tickets
GET    /api/tickets/:id
POST   /api/tickets
PUT    /api/tickets/:id
DELETE /api/tickets/:id
GET    /api/tickets/:id/history
POST   /api/tickets/:id/assign
POST   /api/tickets/:id/status
POST   /api/tickets/:id/resolve
POST   /api/tickets/:id/close
GET    /api/tickets/:id/comments
POST   /api/tickets/:id/comments
GET    /api/tickets/:id/attachments
POST   /api/tickets/:id/attachments
DELETE /api/tickets/:id/attachments/:attachment_id
```

### Comentários
```
GET    /api/comments
GET    /api/comments/:id
POST   /api/comments
PUT    /api/comments/:id
DELETE /api/comments/:id
```

### Dashboard
```
GET    /api/dashboard/stats
GET    /api/dashboard/charts
GET    /api/dashboard/my-tickets
GET    /api/dashboard/assigned-tickets
```

### Relatórios
```
GET    /api/reports/tickets
GET    /api/reports/technicians
GET    /api/reports/sla
GET    /api/reports/satisfaction
POST   /api/reports/export
```

### Notificações
```
GET    /api/notifications
PUT    /api/notifications/:id/read
PUT    /api/notifications/read-all
GET    /api/notifications/unread-count
```

### Configurações
```
GET    /api/settings
PUT    /api/settings/:key
GET    /api/settings/categories
POST   /api/settings/categories
GET    /api/settings/groups
POST   /api/settings/groups
```

### Email
```
POST   /api/email/send-procedure-notice
POST   /api/email/test
GET    /api/email/templates
POST   /api/email/templates
PUT    /api/email/templates/:id
```

---

## 🎨 INTERFACE DO USUÁRIO (React)

### Componentes Principais

#### Layout
- Header (com menu de usuário)
- Sidebar (navegação)
- Main Content Area
- Footer

#### Páginas
- Login
- Dashboard
- Lista de Chamados
- Detalhes do Chamado
- Criar Chamado
- Gerenciar Usuários
- Configurações
- Relatórios
- Perfil do Usuário

#### Componentes Reutilizáveis
- Modal
- Toast/Notification
- Table (com paginação, ordenação, filtros)
- Form Inputs
- Date Picker
- File Upload
- Rich Text Editor
- Charts/Graphs
- Status Badge
- Priority Badge
- Avatar
- Dropdown Menu
- Tabs
- Accordion

---

## 🔒 SEGURANÇA

### Autenticação
- JWT tokens com expiração
- Refresh tokens
- Senhas criptografadas (bcrypt)
- Rate limiting
- CORS configurado

### Autorização
- Middleware de verificação de roles
- Permissões por endpoint
- Validação de propriedade de recursos

### Dados
- Sanitização de inputs
- Validação de dados
- Proteção contra SQL Injection (ORM)
- Proteção contra XSS
- Upload seguro de arquivos

### Auditoria
- Log de todas as ações importantes
- Histórico de alterações
- Rastreabilidade completa

---

## 📦 DEPENDÊNCIAS PRINCIPAIS

### Backend (Python)
- FastAPI (framework web)
- SQLAlchemy (ORM)
- Alembic (migrations)
- Pydantic (validação)
- JWT (autenticação)
- python-jose (tokens)
- passlib (hash de senhas)
- python-multipart (upload)
- aiosmtplib (email assíncrono)
- python-dotenv (variáveis de ambiente)
- psycopg2 (driver PostgreSQL)

### Frontend (React)
- React 18+
- React Router (navegação)
- Axios (HTTP client)
- React Query / SWR (data fetching)
- React Hook Form (formulários)
- Material-UI / Ant Design / Chakra UI (componentes)
- Recharts / Chart.js (gráficos)
- Socket.io-client (WebSocket)
- React Hot Toast (notificações)
- Date-fns (manipulação de datas)

---

## 🚀 DEPLOY E INFRAESTRUTURA

### Servidor Local
- Sistema operacional: Windows Server / Linux
- Python 3.10+
- Node.js 18+ (para build do frontend)
- PostgreSQL 14+
- Nginx (reverse proxy, opcional)

### Processo de Deploy
1. Build do frontend (React)
2. Servir frontend estático via Nginx ou FastAPI
3. Executar backend (FastAPI com Uvicorn)
4. Configurar banco de dados
5. Configurar variáveis de ambiente
6. Executar migrations
7. Configurar serviço do sistema (systemd/Windows Service)

### Variáveis de Ambiente
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/chamados_ti

# JWT
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Email
SMTP_HOST=email-ssl.com.br
SMTP_PORT=587
SMTP_USER=your-email@promio.com.br
SMTP_PASSWORD=your-password
SMTP_FROM=noreply@promio.com.br

# Application
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
DEBUG=False
```

---

## 📈 ROADMAP DE IMPLEMENTAÇÃO

### Fase 1: Fundação (Semanas 1-2)
- [ ] Setup do projeto (backend + frontend)
- [ ] Configuração do banco de dados
- [ ] Estrutura básica da API
- [ ] Autenticação e autorização
- [ ] CRUD de usuários (admin)

### Fase 2: Core do Sistema (Semanas 3-4)
- [ ] CRUD completo de chamados
- [ ] Sistema de comentários
- [ ] Upload de anexos
- [ ] Histórico de alterações
- [ ] Dashboard básico

### Fase 3: Funcionalidades Avançadas (Semanas 5-6)
- [ ] Integração de email (SMTP)
- [ ] Notificações em tempo real
- [ ] Sistema de SLA
- [ ] Relatórios
- [ ] Busca avançada

### Fase 4: Refinamento (Semanas 7-8)
- [ ] Interface responsiva completa
- [ ] Templates de email
- [ ] Configurações do sistema
- [ ] Testes
- [ ] Documentação
- [ ] Deploy

---

## 📝 OBSERVAÇÕES IMPORTANTES

1. **Migração do Sistema Antigo**: Dados do sistema antigo podem ser migrados se necessário
2. **Backup**: Implementar backup automático do banco de dados
3. **Monitoramento**: Considerar logs e monitoramento de erros
4. **Performance**: Otimizar queries e implementar cache quando necessário
5. **Escalabilidade**: Arquitetura permite crescimento futuro
6. **Documentação**: Manter documentação da API atualizada
7. **Testes**: Implementar testes unitários e de integração
8. **Versionamento**: Usar Git para controle de versão

---

## 🎯 PRÓXIMOS PASSOS

1. **Revisar este mapamental** e validar requisitos
2. **Definir prioridades** das funcionalidades
3. **Criar repositório Git** para o projeto
4. **Iniciar desenvolvimento** pela Fase 1
5. **Definir ambiente de desenvolvimento** e staging
6. **Coletar credenciais** de email e banco de dados
7. **Definir design system** para o frontend

---

**Documento criado em:** [Data]
**Versão:** 1.0
**Autor:** Sistema de Chamados TI

