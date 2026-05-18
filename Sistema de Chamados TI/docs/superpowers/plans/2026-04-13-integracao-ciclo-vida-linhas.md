# Integração Ciclo de Vida de Linhas Telefônicas — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Implementar 5 fluxos (desligamento melhorado, onboarding, manutenção, roubo/perda e transferência) que sincronizam o Sistema de Chamados TI com a tabela `linhas` do Gerenciamento de Telefones via PostgreSQL compartilhado.

**Architecture:** O backend (FastAPI) do Chamados já compartilha o banco PostgreSQL com o Gerenciamento de Telefones e já possui `app/services/telefones.py` com lógica de offboarding. Adicionaremos funções para os 4 fluxos restantes nesse serviço, criaremos um novo endpoint `/api/telefones/`, e construiremos as páginas React correspondentes.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy (engine direto via `text()`), React + Material UI, Axios.

---

## Mapa de Arquivos

```
backend/app/
  services/
    telefones.py           ← MODIFICAR: adicionar buscar_linha, atribuir_linha, atualizar_aparelho, roubo_perda, transferir
  schemas/
    telefones.py           ← CRIAR: schemas Pydantic para os 5 fluxos
  api/v1/endpoints/
    telefones.py           ← CRIAR: router com 5 endpoints
  api/v1/
    api.py                 ← MODIFICAR: registrar novo router

frontend/src/
  services/
    api.js                 ← MODIFICAR: adicionar telefonesAPI
  components/
    LinhaCard.jsx          ← CRIAR: card de prévia da linha
    LinhaSearch.jsx        ← CRIAR: campo de busca + card unificado
  pages/
    Onboarding.jsx         ← CRIAR
    ManutencaoAparelho.jsx ← CRIAR
    RouboPerdaLinha.jsx    ← CRIAR
    TransferenciaEquipe.jsx← CRIAR
    Desligamento.jsx       ← MODIFICAR: adicionar campo código + LinhaSearch
  App.jsx                  ← MODIFICAR: adicionar 4 novas rotas
  components/
    Layout.jsx             ← MODIFICAR: adicionar links no menu lateral
```

---

## Task 1: Schemas Pydantic para os fluxos de telefonia

**Files:**
- Create: `backend/app/schemas/telefones.py`

- [ ] **Step 1: Criar o arquivo de schemas**

```python
# backend/app/schemas/telefones.py
from typing import Optional
from pydantic import BaseModel


class LinhaPreview(BaseModel):
    """Dados da linha para prévia antes de confirmar qualquer ação."""
    id: int
    nome: Optional[str] = None
    linha: Optional[str] = None
    equipe: Optional[str] = None
    aparelho: Optional[str] = None
    modelo: Optional[str] = None
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    chip: Optional[str] = None
    operadora: Optional[str] = None
    numero_serie: Optional[str] = None
    patrimonio: Optional[str] = None
    cargo: Optional[str] = None
    setor: Optional[str] = None
    email: Optional[str] = None
    codigo: Optional[str] = None


class BuscarLinhaResponse(BaseModel):
    encontrado: bool
    mensagem: str
    linha: Optional[LinhaPreview] = None


class OnboardingRequest(BaseModel):
    """Dados para atribuir linha a novo colaborador."""
    numero_linha: str                    # número da linha (já sabe de cabeça)
    nome: str
    codigo: Optional[str] = None        # matrícula
    cargo: Optional[str] = None
    setor: Optional[str] = None
    empresa: Optional[str] = None
    equipe: Optional[str] = None
    gestor: Optional[str] = None
    email: Optional[str] = None
    nome_guerra: Optional[str] = None
    substituicao_nome: Optional[str] = None   # nome de quem está sendo substituído (opcional)
    ticket_id: Optional[int] = None


class ManutencaoRequest(BaseModel):
    """Dados para atualizar aparelho durante manutenção (troca por reserva)."""
    linha_id: int
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    aparelho: Optional[str] = None
    numero_serie: Optional[str] = None
    patrimonio: Optional[str] = None
    chip: Optional[str] = None
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class RouboPerdaRequest(BaseModel):
    """
    Roubo/Perda — dois cenários:
    - cenario_a: mesma linha, aparelho novo (nova_linha = None)
    - cenario_b: linha nova + aparelho novo (nova_linha preenchida)
    """
    linha_id: int
    imei_a: Optional[str] = None
    imei_b: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    aparelho: Optional[str] = None
    numero_serie: Optional[str] = None
    patrimonio: Optional[str] = None
    chip: Optional[str] = None
    nova_linha: Optional[str] = None    # preenchido apenas no cenário B
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class TransferenciaRequest(BaseModel):
    """Transferência entre equipes (com ou sem promoção)."""
    linha_id: int
    equipe: str
    setor: str
    gestor: str
    cargo: Optional[str] = None        # preenchido só se for promoção
    empresa: Optional[str] = None      # raramente muda
    observacao: Optional[str] = None
    ticket_id: Optional[int] = None


class TelefonesActionResponse(BaseModel):
    sucesso: bool
    mensagem: str
```

- [ ] **Step 2: Verificar**

```
# Sem comando de teste — verificação visual: arquivo criado sem erros de sintaxe.
# Rode o backend e confirme que importa sem erro:
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI/backend"
python -c "from app.schemas.telefones import LinhaPreview, OnboardingRequest; print('OK')"
```
Esperado: `OK`

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add backend/app/schemas/telefones.py
git commit -m "feat: add telefones schemas (LinhaPreview, Onboarding, Manutencao, RouboPenda, Transferencia)"
```

---

## Task 2: Novas funções de serviço em `telefones.py`

**Files:**
- Modify: `backend/app/services/telefones.py`

> O arquivo já possui `_find_rows_postgres`, `_apply_vacancy_postgres`, `_normalize_key`, `_append_note` e `engine`. Usaremos essas funções existentes.

- [ ] **Step 1: Adicionar `buscar_linha_por_codigo_ou_nome` ao final de `telefones.py`**

```python
# --- ADICIONAR ao final de backend/app/services/telefones.py ---

def buscar_linha_por_codigo_ou_nome(
    *,
    codigo: str = "",
    nome: str = "",
) -> Optional[dict]:
    """
    Busca uma linha ativa no PostgreSQL.
    Prioridade: codigo (matrícula) > nome.
    Retorna dict com todos os campos de prévia ou None.
    """
    codigo = (codigo or "").strip()
    nome = (nome or "").strip()
    if not codigo and not nome:
        return None

    exclude_names = ("vago", "manutenção", "manutencao")
    select_cols = """
        id, nome, nome_usuario_snapshot, codigo, codigo_usuario_snapshot,
        linha, equipe, equipe_padrao, aparelho, modelo, imei_a, imei_b,
        marca, chip, operadora, numero_serie, patrimonio,
        cargo, setor, email, gestor, empresa, observacao
    """

    with engine.connect() as conn:
        # 1) Por código (matrícula)
        if codigo:
            row = conn.execute(
                text(
                    f"""
                    SELECT {select_cols}
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND (
                          lower(trim(coalesce(codigo, ''))) = lower(trim(:codigo))
                          OR lower(trim(coalesce(codigo_usuario_snapshot, ''))) = lower(trim(:codigo))
                      )
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                      AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"codigo": codigo, "exclude": exclude_names},
            ).mappings().first()
            if row:
                return dict(row)

        # 2) Por nome (direto)
        if nome:
            row = conn.execute(
                text(
                    f"""
                    SELECT {select_cols}
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) = lower(trim(:nome))
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                      AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"nome": nome, "exclude": exclude_names},
            ).mappings().first()
            if row:
                return dict(row)

            # 3) Fallback acento-insensível
            candidates = conn.execute(
                text(
                    f"""
                    SELECT {select_cols}
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND nome IS NOT NULL AND trim(nome) <> ''
                      AND lower(trim(coalesce(nome, nome_usuario_snapshot, ''))) NOT IN :exclude
                      AND lower(coalesce(segmento, '')) NOT LIKE 'manuten%'
                    ORDER BY id DESC
                    LIMIT 500
                    """
                ),
                {"exclude": exclude_names},
            ).mappings().all()
            nome_key = _normalize_key(nome)
            for r in candidates:
                if _normalize_key(r.get("nome") or r.get("nome_usuario_snapshot") or "") == nome_key:
                    return dict(r)

    return None
```

- [ ] **Step 2: Adicionar `atribuir_linha` ao final de `telefones.py`**

```python
def atribuir_linha(
    *,
    numero_linha: str,
    nome: str,
    codigo: str = "",
    cargo: str = "",
    setor: str = "",
    empresa: str = "",
    equipe: str = "",
    gestor: str = "",
    email: str = "",
    nome_guerra: str = "",
    ticket_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Onboarding: atribui colaborador a uma linha VAGO.
    Atualiza campos pessoais. Preserva dados do aparelho.
    """
    numero_linha = (numero_linha or "").strip()
    nome = (nome or "").strip()
    if not numero_linha or not nome:
        return False, "Número da linha e nome do colaborador são obrigatórios."

    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Linha atribuída via onboarding a {nome}{ticket_suffix}."

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text(
                    """
                    SELECT id, observacao
                    FROM linhas
                    WHERE modo = 'ativas'
                      AND (
                          lower(trim(coalesce(numero_linha, ''))) = lower(trim(:nl))
                          OR lower(trim(coalesce(linha, ''))) = lower(trim(:nl))
                      )
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                {"nl": numero_linha},
            ).mappings().first()

        if not row:
            return False, f"Linha '{numero_linha}' não encontrada no banco de telefones."

        new_obs = _append_note(row.get("observacao"), note)

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE linhas
                    SET
                        nome = :nome,
                        nome_usuario_snapshot = :nome,
                        nome_guerra = :nome_guerra,
                        codigo = :codigo,
                        codigo_usuario_snapshot = :codigo,
                        cargo = :cargo,
                        setor = :setor,
                        empresa = :empresa,
                        equipe = CASE WHEN :equipe <> '' THEN :equipe ELSE equipe END,
                        gestor = CASE WHEN :gestor <> '' THEN :gestor ELSE gestor END,
                        email = :email,
                        observacao = :obs
                    WHERE id = :id
                    """
                ),
                {
                    "nome": nome,
                    "nome_guerra": nome_guerra or nome,
                    "codigo": codigo or "",
                    "cargo": cargo or "",
                    "setor": setor or "",
                    "empresa": empresa or "",
                    "equipe": equipe or "",
                    "gestor": gestor or "",
                    "email": email or "",
                    "obs": new_obs,
                    "id": row["id"],
                },
            )
        return True, f"Linha '{numero_linha}' atribuída a '{nome}' com sucesso."
    except Exception as exc:
        logger.exception("Falha no onboarding de linha")
        return False, f"Falha ao atribuir linha [{exc.__class__.__name__}]: {exc}"
```

- [ ] **Step 3: Adicionar `atualizar_aparelho` ao final de `telefones.py`**

```python
def atualizar_aparelho(
    *,
    linha_id: int,
    imei_a: str = "",
    imei_b: str = "",
    marca: str = "",
    modelo: str = "",
    aparelho: str = "",
    numero_serie: str = "",
    patrimonio: str = "",
    chip: str = "",
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Manutenção/Troca: atualiza apenas os campos do aparelho.
    Preserva todos os campos do colaborador e da linha.
    """
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Aparelho atualizado (manutenção/troca){ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        new_obs = _append_note(row.get("observacao"), note)

        # Só atualiza campos que foram enviados (não-vazios)
        updates = {"obs": new_obs, "id": linha_id}
        set_parts = ["observacao = :obs"]

        field_map = {
            "imei_a": imei_a,
            "imei_b": imei_b,
            "marca": marca,
            "modelo": modelo,
            "aparelho": aparelho,
            "numero_serie": numero_serie,
            "patrimonio": patrimonio,
            "chip": chip,
        }
        for col, val in field_map.items():
            if (val or "").strip():
                set_parts.append(f"{col} = :{col}")
                updates[col] = val.strip()

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        return True, "Dados do aparelho atualizados com sucesso."
    except Exception as exc:
        logger.exception("Falha ao atualizar aparelho")
        return False, f"Falha ao atualizar aparelho [{exc.__class__.__name__}]: {exc}"
```

- [ ] **Step 4: Adicionar `registrar_roubo_perda` ao final de `telefones.py`**

```python
def registrar_roubo_perda(
    *,
    linha_id: int,
    imei_a: str = "",
    imei_b: str = "",
    marca: str = "",
    modelo: str = "",
    aparelho: str = "",
    numero_serie: str = "",
    patrimonio: str = "",
    chip: str = "",
    nova_linha: str = "",    # vazio = cenário A; preenchido = cenário B
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Roubo/Perda:
    - Cenário A: mesma linha, novo aparelho → atualiza só campos do aparelho
    - Cenário B: nova linha + novo aparelho → atualiza aparelho + campo `linha`/`numero_linha`
    """
    nova_linha = (nova_linha or "").strip()
    cenario = "B" if nova_linha else "A"
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Roubo/Perda — cenário {cenario}{ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        new_obs = _append_note(row.get("observacao"), note)

        updates = {"obs": new_obs, "id": linha_id}
        set_parts = ["observacao = :obs"]

        field_map = {
            "imei_a": imei_a,
            "imei_b": imei_b,
            "marca": marca,
            "modelo": modelo,
            "aparelho": aparelho,
            "numero_serie": numero_serie,
            "patrimonio": patrimonio,
            "chip": chip,
        }
        for col, val in field_map.items():
            if (val or "").strip():
                set_parts.append(f"{col} = :{col}")
                updates[col] = val.strip()

        # Cenário B: atualiza também o número da linha
        if nova_linha:
            set_parts.append("linha = :nova_linha")
            set_parts.append("numero_linha = :nova_linha")
            updates["nova_linha"] = nova_linha

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        msg = (
            f"Roubo/Perda cenário {cenario} registrado. "
            + (f"Nova linha: {nova_linha}." if nova_linha else "Linha mantida.")
        )
        return True, msg
    except Exception as exc:
        logger.exception("Falha ao registrar roubo/perda")
        return False, f"Falha ao registrar roubo/perda [{exc.__class__.__name__}]: {exc}"
```

- [ ] **Step 5: Adicionar `transferir_colaborador` ao final de `telefones.py`**

```python
def transferir_colaborador(
    *,
    linha_id: int,
    equipe: str,
    setor: str,
    gestor: str,
    cargo: str = "",         # preenchido só se for promoção
    empresa: str = "",       # raramente muda
    observacao_extra: str = "",
    ticket_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Transferência: atualiza equipe, setor, gestor e opcionalmente cargo/empresa.
    Preserva todos os dados do colaborador e do aparelho.
    """
    ticket_suffix = f" [ticket_id={ticket_id}]" if ticket_id else ""
    note = f"Transferência de equipe para '{equipe}'{ticket_suffix}."
    if observacao_extra:
        note = f"{note} {observacao_extra}"

    try:
        with engine.connect() as read_conn:
            row = read_conn.execute(
                text("SELECT id, observacao FROM linhas WHERE id = :id"),
                {"id": linha_id},
            ).mappings().first()

        if not row:
            return False, f"Linha id={linha_id} não encontrada."

        new_obs = _append_note(row.get("observacao"), note)

        updates = {
            "equipe": equipe,
            "equipe_padrao": equipe,
            "setor": setor,
            "gestor": gestor,
            "obs": new_obs,
            "id": linha_id,
        }
        set_parts = [
            "equipe = :equipe",
            "equipe_padrao = :equipe_padrao",
            "setor = :setor",
            "gestor = :gestor",
            "observacao = :obs",
        ]

        if (cargo or "").strip():
            set_parts.append("cargo = :cargo")
            updates["cargo"] = cargo.strip()

        if (empresa or "").strip():
            set_parts.append("empresa = :empresa")
            updates["empresa"] = empresa.strip()

        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE linhas SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
        return True, f"Colaborador transferido para equipe '{equipe}' com sucesso."
    except Exception as exc:
        logger.exception("Falha na transferência")
        return False, f"Falha na transferência [{exc.__class__.__name__}]: {exc}"
```

- [ ] **Step 6: Verificar importações**

Confirme que `Optional` já está importado no topo do arquivo (já está: `from typing import Optional, Tuple`).

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI/backend"
python -c "from app.services.telefones import buscar_linha_por_codigo_ou_nome, atribuir_linha, atualizar_aparelho, registrar_roubo_perda, transferir_colaborador; print('OK')"
```
Esperado: `OK`

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add backend/app/services/telefones.py
git commit -m "feat: add buscar_linha, atribuir_linha, atualizar_aparelho, roubo_perda, transferir to telefones service"
```

---

## Task 3: Endpoint `/api/telefones/`

**Files:**
- Create: `backend/app/api/v1/endpoints/telefones.py`

- [ ] **Step 1: Criar o arquivo de endpoints**

```python
# backend/app/api/v1/endpoints/telefones.py
"""
Endpoints de integração com a tabela `linhas` do Gerenciamento de Telefones.
Todos exigem autenticação de técnico ou admin.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.dependencies import get_current_technician_or_admin
from app.models.user import User
from app.schemas.telefones import (
    BuscarLinhaResponse,
    LinhaPreview,
    OnboardingRequest,
    ManutencaoRequest,
    RouboPerdaRequest,
    TransferenciaRequest,
    TelefonesActionResponse,
)
from app.services.telefones import (
    buscar_linha_por_codigo_ou_nome,
    atribuir_linha,
    atualizar_aparelho,
    registrar_roubo_perda,
    transferir_colaborador,
)

router = APIRouter()


@router.get("/buscar-linha", response_model=BuscarLinhaResponse)
async def buscar_linha(
    codigo: str = "",
    nome: str = "",
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Busca linha por código (matrícula) com fallback por nome.
    Retorna dados para prévia antes de qualquer ação.
    """
    if not codigo.strip() and not nome.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe código ou nome para buscar.",
        )
    row = buscar_linha_por_codigo_ou_nome(codigo=codigo, nome=nome)
    if not row:
        return BuscarLinhaResponse(
            encontrado=False,
            mensagem=f"Nenhuma linha ativa encontrada para código='{codigo}' / nome='{nome}'.",
        )
    preview = LinhaPreview(
        id=row["id"],
        nome=row.get("nome") or row.get("nome_usuario_snapshot"),
        linha=row.get("linha"),
        equipe=row.get("equipe") or row.get("equipe_padrao"),
        aparelho=row.get("aparelho"),
        modelo=row.get("modelo"),
        imei_a=row.get("imei_a"),
        imei_b=row.get("imei_b"),
        marca=row.get("marca"),
        chip=row.get("chip"),
        operadora=row.get("operadora"),
        numero_serie=row.get("numero_serie"),
        patrimonio=row.get("patrimonio"),
        cargo=row.get("cargo"),
        setor=row.get("setor"),
        email=row.get("email"),
        codigo=row.get("codigo") or row.get("codigo_usuario_snapshot"),
    )
    return BuscarLinhaResponse(encontrado=True, mensagem="Linha encontrada.", linha=preview)


@router.post("/onboarding", response_model=TelefonesActionResponse)
async def onboarding_linha(
    body: OnboardingRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Atribui novo colaborador a uma linha VAGO."""
    ok, msg = atribuir_linha(
        numero_linha=body.numero_linha,
        nome=body.nome,
        codigo=body.codigo or "",
        cargo=body.cargo or "",
        setor=body.setor or "",
        empresa=body.empresa or "",
        equipe=body.equipe or "",
        gestor=body.gestor or "",
        email=body.email or "",
        nome_guerra=body.nome_guerra or "",
        ticket_id=body.ticket_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/manutencao", response_model=TelefonesActionResponse)
async def manutencao_aparelho(
    body: ManutencaoRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Atualiza dados do aparelho (troca por reserva). Preserva dados do colaborador."""
    ok, msg = atualizar_aparelho(
        linha_id=body.linha_id,
        imei_a=body.imei_a or "",
        imei_b=body.imei_b or "",
        marca=body.marca or "",
        modelo=body.modelo or "",
        aparelho=body.aparelho or "",
        numero_serie=body.numero_serie or "",
        patrimonio=body.patrimonio or "",
        chip=body.chip or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/roubo-perda", response_model=TelefonesActionResponse)
async def roubo_perda_linha(
    body: RouboPerdaRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """
    Registra roubo/perda.
    Cenário A: mesmo número, novo aparelho.
    Cenário B: nova linha + novo aparelho (preencher nova_linha).
    """
    ok, msg = registrar_roubo_perda(
        linha_id=body.linha_id,
        imei_a=body.imei_a or "",
        imei_b=body.imei_b or "",
        marca=body.marca or "",
        modelo=body.modelo or "",
        aparelho=body.aparelho or "",
        numero_serie=body.numero_serie or "",
        patrimonio=body.patrimonio or "",
        chip=body.chip or "",
        nova_linha=body.nova_linha or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)


@router.post("/transferencia", response_model=TelefonesActionResponse)
async def transferencia_equipe(
    body: TransferenciaRequest,
    current_user: User = Depends(get_current_technician_or_admin),
):
    """Transfere colaborador de equipe. Atualiza equipe, setor, gestor e opcionalmente cargo/empresa."""
    ok, msg = transferir_colaborador(
        linha_id=body.linha_id,
        equipe=body.equipe,
        setor=body.setor,
        gestor=body.gestor,
        cargo=body.cargo or "",
        empresa=body.empresa or "",
        observacao_extra=body.observacao or "",
        ticket_id=body.ticket_id,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return TelefonesActionResponse(sucesso=True, mensagem=msg)
```

- [ ] **Step 2: Registrar o router em `api.py`**

Modificar `backend/app/api/v1/api.py`:

```python
# Adicionar import:
from app.api.v1.endpoints import auth, users, desligamento, tickets, telefones

# Adicionar linha ao final de api.py:
api_router.include_router(telefones.router, prefix="/telefones", tags=["linhas telefônicas"])
```

- [ ] **Step 3: Verificar que o backend sobe sem erro**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir `http://localhost:8000/api/docs` e verificar que o grupo **"linhas telefônicas"** aparece com 5 endpoints:
- `GET /api/telefones/buscar-linha`
- `POST /api/telefones/onboarding`
- `POST /api/telefones/manutencao`
- `POST /api/telefones/roubo-perda`
- `POST /api/telefones/transferencia`

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add backend/app/api/v1/endpoints/telefones.py backend/app/api/v1/api.py
git commit -m "feat: add /api/telefones endpoints (buscar-linha, onboarding, manutencao, roubo-perda, transferencia)"
```

---

## Task 4: Extensão do `api.js` no frontend

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Adicionar `telefonesAPI` ao final de `api.js` (antes do `export default api`)**

```javascript
export const telefonesAPI = {
  buscarLinha: (codigo, nome) =>
    api
      .get('/telefones/buscar-linha', { params: { codigo: codigo || '', nome: nome || '' } })
      .then((res) => res.data),

  onboarding: (data) =>
    api.post('/telefones/onboarding', data).then((res) => res.data),

  manutencao: (data) =>
    api.post('/telefones/manutencao', data).then((res) => res.data),

  rouboPenda: (data) =>
    api.post('/telefones/roubo-perda', data).then((res) => res.data),

  transferencia: (data) =>
    api.post('/telefones/transferencia', data).then((res) => res.data),
}
```

- [ ] **Step 2: Verificar**

Abra o navegador com o frontend rodando e confirme no console do browser que não há erros de importação.

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/services/api.js
git commit -m "feat: add telefonesAPI to api.js (buscarLinha, onboarding, manutencao, rouboPenda, transferencia)"
```

---

## Task 5: Componente `LinhaCard.jsx` e `LinhaSearch.jsx`

**Files:**
- Create: `frontend/src/components/LinhaCard.jsx`
- Create: `frontend/src/components/LinhaSearch.jsx`

- [ ] **Step 1: Criar `LinhaCard.jsx`**

```jsx
// frontend/src/components/LinhaCard.jsx
import { Box, Typography, Chip, Divider } from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'

const LinhaCard = ({ linha }) => {
  if (!linha) return null
  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'success.main',
        borderRadius: 2,
        p: 2,
        bgcolor: 'success.50',
        mt: 1,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <CheckCircleIcon color="success" fontSize="small" />
        <Typography variant="subtitle2" color="success.dark" fontWeight={600}>
          Linha encontrada
        </Typography>
      </Box>
      <Divider sx={{ mb: 1.5 }} />
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
        {[
          ['Colaborador', linha.nome],
          ['Linha', linha.linha],
          ['Equipe', linha.equipe],
          ['Cargo', linha.cargo],
          ['Setor', linha.setor],
          ['Código', linha.codigo],
        ].map(([label, val]) =>
          val ? (
            <Typography key={label} variant="body2">
              <strong>{label}:</strong> {val}
            </Typography>
          ) : null
        )}
      </Box>
      {(linha.aparelho || linha.modelo || linha.marca) && (
        <>
          <Divider sx={{ my: 1 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <PhoneAndroidIcon fontSize="small" color="action" />
            <Typography variant="caption" color="text.secondary">
              Aparelho
            </Typography>
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
            {[
              ['Modelo', linha.modelo || linha.aparelho],
              ['Marca', linha.marca],
              ['IMEI A', linha.imei_a],
              ['Patrimônio', linha.patrimonio],
            ].map(([label, val]) =>
              val ? (
                <Typography key={label} variant="body2">
                  <strong>{label}:</strong> {val}
                </Typography>
              ) : null
            )}
          </Box>
        </>
      )}
    </Box>
  )
}

export default LinhaCard
```

- [ ] **Step 2: Criar `LinhaSearch.jsx`**

```jsx
// frontend/src/components/LinhaSearch.jsx
import { useState } from 'react'
import { Box, TextField, Button, Alert, CircularProgress } from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import LinhaCard from './LinhaCard'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const LinhaSearch = ({ onLinhaFound, onLinhaClear }) => {
  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState(null)   // null | { encontrado, linha }
  const [buscado, setBuscado] = useState(false)

  const buscar = async () => {
    if (!codigo.trim() && !nome.trim()) {
      toast.error('Informe o código ou nome para buscar.')
      return
    }
    setLoading(true)
    try {
      const data = await telefonesAPI.buscarLinha(codigo, nome)
      setResultado(data)
      setBuscado(true)
      if (data.encontrado && onLinhaFound) {
        onLinhaFound(data.linha)
      } else if (!data.encontrado && onLinhaClear) {
        onLinhaClear()
      }
    } catch (err) {
      toast.error('Erro ao buscar linha.')
    } finally {
      setLoading(false)
    }
  }

  const limpar = () => {
    setCodigo('')
    setNome('')
    setResultado(null)
    setBuscado(false)
    if (onLinhaClear) onLinhaClear()
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <TextField
          label="Código (matrícula)"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          size="small"
          sx={{ width: 180 }}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
        />
        <TextField
          label="Nome completo (fallback)"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          size="small"
          sx={{ flex: 1, minWidth: 220 }}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
        />
        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
          onClick={buscar}
          disabled={loading}
          size="small"
        >
          Buscar linha
        </Button>
        {buscado && (
          <Button variant="text" size="small" onClick={limpar}>
            Limpar
          </Button>
        )}
      </Box>

      {buscado && !resultado?.encontrado && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          Linha não localizada — você pode prosseguir sem atualizar o Gerenciamento de Telefones.
        </Alert>
      )}

      {resultado?.encontrado && <LinhaCard linha={resultado.linha} />}
    </Box>
  )
}

export default LinhaSearch
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/components/LinhaCard.jsx frontend/src/components/LinhaSearch.jsx
git commit -m "feat: add LinhaCard and LinhaSearch reusable components"
```

---

## Task 6: Melhorar `Desligamento.jsx` — adicionar código + LinhaSearch

**Files:**
- Modify: `frontend/src/pages/Desligamento.jsx`

> O formulário já tem `ticketEmployeeName`. Adicionamos `ticketEmployeeCode` e o componente `LinhaSearch` logo abaixo do campo de nome.

- [ ] **Step 1: Adicionar import e estado**

No topo de `Desligamento.jsx`, adicionar os imports:
```jsx
import LinhaSearch from '../components/LinhaSearch'
```

Dentro do componente `Desligamento`, adicionar o estado:
```jsx
const [ticketEmployeeCode, setTicketEmployeeCode] = useState('')
const [linhaEncontrada, setLinhaEncontrada] = useState(null)
```

- [ ] **Step 2: Adicionar campo código e LinhaSearch após o campo "Nome do colaborador"**

Localizar o `TextField` de `ticketEmployeeName` (buscar por `"Nome do colaborador"` no JSX) e adicionar logo abaixo:

```jsx
<TextField
  label="Código / Matrícula"
  value={ticketEmployeeCode}
  onChange={(e) => setTicketEmployeeCode(e.target.value)}
  size="small"
  sx={{ width: 200 }}
  placeholder="Ex: 12345"
/>

<Box sx={{ mt: 2 }}>
  <Typography variant="subtitle2" gutterBottom>Linha Telefônica</Typography>
  <LinhaSearch
    onLinhaFound={(linha) => setLinhaEncontrada(linha)}
    onLinhaClear={() => setLinhaEncontrada(null)}
  />
</Box>
```

- [ ] **Step 3: Verificar visualmente**

Iniciar o frontend (`npm run dev` em `frontend/`) e acessar `/desligamento`. Confirmar que:
- Campo "Código / Matrícula" aparece abaixo do nome
- Componente `LinhaSearch` aparece com os campos de busca
- Ao buscar por código/nome, o card de prévia aparece corretamente

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/pages/Desligamento.jsx
git commit -m "feat: add codigo field and LinhaSearch section to Desligamento page"
```

---

## Task 7: Página `Onboarding.jsx`

**Files:**
- Create: `frontend/src/pages/Onboarding.jsx`

- [ ] **Step 1: Criar a página**

```jsx
// frontend/src/pages/Onboarding.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, Checkbox, FormControlLabel,
} from '@mui/material'
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const Onboarding = () => {
  const [form, setForm] = useState({
    numero_linha: '',
    nome: '',
    codigo: '',
    cargo: '',
    empresa: '',
    equipe: '',
    gestor: '',
    setor: '',
    email: '',
    nome_guerra: '',
    substituicao_nome: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!form.numero_linha.trim() || !form.nome.trim()) {
      toast.error('Número da linha e nome são obrigatórios.')
      return
    }
    setSubmitting(true)
    try {
      const data = await telefonesAPI.onboarding(form)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Linha atribuída com sucesso!')
      setForm({
        numero_linha: '', nome: '', codigo: '', cargo: '',
        empresa: '', equipe: '', gestor: '', setor: '',
        email: '', nome_guerra: '', substituicao_nome: '',
      })
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao atribuir linha.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <PersonAddIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Onboarding — Novo Colaborador
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Atribui o novo colaborador a uma linha VAGO. Preencha os dados do email de admissão.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Linha</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3 }}>
          <TextField
            required label="Número da Linha" value={form.numero_linha}
            onChange={handleChange('numero_linha')} size="small" sx={{ width: 200 }}
            placeholder="21999990000"
          />
          <TextField
            label="Substituição (nome de quem saiu)" value={form.substituicao_nome}
            onChange={handleChange('substituicao_nome')} size="small" sx={{ flex: 1 }}
            placeholder="Nome do colaborador substituído (opcional)"
          />
        </Box>

        <Divider sx={{ mb: 2 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Dados do Colaborador</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField required label="Nome Completo" value={form.nome}
            onChange={handleChange('nome')} size="small" />
          <TextField label="Código / Matrícula" value={form.codigo}
            onChange={handleChange('codigo')} size="small" />
          <TextField label="Nome de Guerra" value={form.nome_guerra}
            onChange={handleChange('nome_guerra')} size="small" />
          <TextField label="Cargo" value={form.cargo}
            onChange={handleChange('cargo')} size="small" />
          <TextField label="Empresa" value={form.empresa}
            onChange={handleChange('empresa')} size="small" />
          <TextField label="Equipe" value={form.equipe}
            onChange={handleChange('equipe')} size="small" />
          <TextField label="Setor" value={form.setor}
            onChange={handleChange('setor')} size="small" />
          <TextField label="Gestor" value={form.gestor}
            onChange={handleChange('gestor')} size="small" />
          <TextField label="E-mail" value={form.email}
            onChange={handleChange('email')} size="small" type="email" />
        </Box>

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" size="large" onClick={handleSubmit}
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <PersonAddIcon />}
          >
            Confirmar Onboarding
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default Onboarding
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/pages/Onboarding.jsx
git commit -m "feat: add Onboarding page"
```

---

## Task 8: Página `ManutencaoAparelho.jsx`

**Files:**
- Create: `frontend/src/pages/ManutencaoAparelho.jsx`

- [ ] **Step 1: Criar a página**

```jsx
// frontend/src/pages/ManutencaoAparelho.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider,
} from '@mui/material'
import BuildIcon from '@mui/icons-material/Build'
import LinhaSearch from '../components/LinhaSearch'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const ManutencaoAparelho = () => {
  const [linhaId, setLinhaId] = useState(null)
  const [form, setForm] = useState({
    imei_a: '', imei_b: '', marca: '', modelo: '',
    aparelho: '', numero_serie: '', patrimonio: '', chip: '', observacao: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!linhaId) {
      toast.error('Busque e selecione uma linha antes de prosseguir.')
      return
    }
    setSubmitting(true)
    try {
      const data = await telefonesAPI.manutencao({ ...form, linha_id: linhaId })
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Aparelho atualizado com sucesso!')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao atualizar aparelho.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <BuildIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Manutenção / Troca de Aparelho
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Atualiza os dados do aparelho reserva. Preserva todos os dados do colaborador.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Buscar Colaborador</Typography>
        <LinhaSearch
          onLinhaFound={(l) => setLinhaId(l.id)}
          onLinhaClear={() => setLinhaId(null)}
        />

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Dados do Aparelho Reserva
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField label="IMEI A" value={form.imei_a} onChange={handleChange('imei_a')} size="small" />
          <TextField label="IMEI B" value={form.imei_b} onChange={handleChange('imei_b')} size="small" />
          <TextField label="Marca" value={form.marca} onChange={handleChange('marca')} size="small" />
          <TextField label="Modelo" value={form.modelo} onChange={handleChange('modelo')} size="small" />
          <TextField label="Aparelho (descrição)" value={form.aparelho} onChange={handleChange('aparelho')} size="small" />
          <TextField label="Número de Série" value={form.numero_serie} onChange={handleChange('numero_serie')} size="small" />
          <TextField label="Patrimônio" value={form.patrimonio} onChange={handleChange('patrimonio')} size="small" />
          <TextField label="Chip" value={form.chip} onChange={handleChange('chip')} size="small" />
          <TextField label="Observação" value={form.observacao} onChange={handleChange('observacao')}
            size="small" multiline rows={2} sx={{ gridColumn: '1 / -1' }} />
        </Box>

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" size="large" onClick={handleSubmit} disabled={submitting || !linhaId}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <BuildIcon />}
          >
            Confirmar Troca
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default ManutencaoAparelho
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/pages/ManutencaoAparelho.jsx
git commit -m "feat: add ManutencaoAparelho page"
```

---

## Task 9: Página `RouboPerdaLinha.jsx`

**Files:**
- Create: `frontend/src/pages/RouboPerdaLinha.jsx`

- [ ] **Step 1: Criar a página**

```jsx
// frontend/src/pages/RouboPerdaLinha.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, RadioGroup, FormControlLabel,
  Radio, FormLabel,
} from '@mui/material'
import ReportProblemIcon from '@mui/icons-material/ReportProblem'
import LinhaSearch from '../components/LinhaSearch'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const RouboPerdaLinha = () => {
  const [linhaId, setLinhaId] = useState(null)
  const [cenario, setCenario] = useState('A')  // 'A' | 'B'
  const [form, setForm] = useState({
    imei_a: '', imei_b: '', marca: '', modelo: '',
    aparelho: '', numero_serie: '', patrimonio: '', chip: '',
    nova_linha: '', observacao: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!linhaId) {
      toast.error('Busque e selecione uma linha antes de prosseguir.')
      return
    }
    if (cenario === 'B' && !form.nova_linha.trim()) {
      toast.error('Informe o novo número da linha para o cenário B.')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        linha_id: linhaId,
        nova_linha: cenario === 'B' ? form.nova_linha : '',
      }
      const data = await telefonesAPI.rouboPenda(payload)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Roubo/Perda registrado com sucesso!')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao registrar roubo/perda.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <ReportProblemIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Roubo e Perda
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Registra substituição de aparelho por roubo ou perda.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Buscar Colaborador</Typography>
        <LinhaSearch
          onLinhaFound={(l) => setLinhaId(l.id)}
          onLinhaClear={() => setLinhaId(null)}
        />

        <Divider sx={{ my: 3 }} />
        <FormLabel component="legend" sx={{ mb: 1, fontWeight: 600 }}>Cenário</FormLabel>
        <RadioGroup row value={cenario} onChange={(e) => setCenario(e.target.value)}>
          <FormControlLabel value="A" control={<Radio />} label="A — Mesma linha, aparelho novo" />
          <FormControlLabel value="B" control={<Radio />} label="B — Linha nova + aparelho reserva" />
        </RadioGroup>

        {cenario === 'B' && (
          <TextField
            label="Novo número de linha" value={form.nova_linha}
            onChange={handleChange('nova_linha')} size="small"
            sx={{ mt: 1, width: 220 }} placeholder="21999990000"
          />
        )}

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Dados do Novo Aparelho</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField label="IMEI A" value={form.imei_a} onChange={handleChange('imei_a')} size="small" />
          <TextField label="IMEI B" value={form.imei_b} onChange={handleChange('imei_b')} size="small" />
          <TextField label="Marca" value={form.marca} onChange={handleChange('marca')} size="small" />
          <TextField label="Modelo" value={form.modelo} onChange={handleChange('modelo')} size="small" />
          <TextField label="Aparelho (descrição)" value={form.aparelho} onChange={handleChange('aparelho')} size="small" />
          <TextField label="Número de Série" value={form.numero_serie} onChange={handleChange('numero_serie')} size="small" />
          <TextField label="Patrimônio" value={form.patrimonio} onChange={handleChange('patrimonio')} size="small" />
          <TextField label="Chip" value={form.chip} onChange={handleChange('chip')} size="small" />
          <TextField label="Observação" value={form.observacao} onChange={handleChange('observacao')}
            size="small" multiline rows={2} sx={{ gridColumn: '1 / -1' }} />
        </Box>

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" color="warning" size="large"
            onClick={handleSubmit} disabled={submitting || !linhaId}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <ReportProblemIcon />}
          >
            Confirmar Roubo/Perda
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default RouboPerdaLinha
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/pages/RouboPerdaLinha.jsx
git commit -m "feat: add RouboPerdaLinha page (cenario A and B)"
```

---

## Task 10: Página `TransferenciaEquipe.jsx`

**Files:**
- Create: `frontend/src/pages/TransferenciaEquipe.jsx`

- [ ] **Step 1: Criar a página**

```jsx
// frontend/src/pages/TransferenciaEquipe.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, Checkbox, FormControlLabel,
} from '@mui/material'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import LinhaSearch from '../components/LinhaSearch'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const TransferenciaEquipe = () => {
  const [linhaId, setLinhaId] = useState(null)
  const [isPromocao, setIsPromocao] = useState(false)
  const [form, setForm] = useState({
    equipe: '', setor: '', gestor: '', cargo: '', empresa: '', observacao: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!linhaId) {
      toast.error('Busque e selecione uma linha antes de prosseguir.')
      return
    }
    if (!form.equipe.trim() || !form.setor.trim() || !form.gestor.trim()) {
      toast.error('Equipe, setor e gestor são obrigatórios.')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        linha_id: linhaId,
        cargo: isPromocao ? form.cargo : '',
      }
      const data = await telefonesAPI.transferencia(payload)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Transferência registrada com sucesso!')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao registrar transferência.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <SwapHorizIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Transferência entre Equipes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Atualiza equipe, setor e gestor. Todos os outros dados do colaborador e aparelho são preservados.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Buscar Colaborador</Typography>
        <LinhaSearch
          onLinhaFound={(l) => setLinhaId(l.id)}
          onLinhaClear={() => setLinhaId(null)}
        />

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Nova Equipe</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField required label="Equipe" value={form.equipe}
            onChange={handleChange('equipe')} size="small" />
          <TextField required label="Setor" value={form.setor}
            onChange={handleChange('setor')} size="small" />
          <TextField required label="Gestor" value={form.gestor}
            onChange={handleChange('gestor')} size="small" />
          <TextField label="Empresa (se mudar)" value={form.empresa}
            onChange={handleChange('empresa')} size="small" />
        </Box>

        <FormControlLabel
          sx={{ mt: 2 }}
          control={<Checkbox checked={isPromocao} onChange={(e) => setIsPromocao(e.target.checked)} />}
          label="É promoção? (alterar cargo)"
        />

        {isPromocao && (
          <TextField label="Novo Cargo" value={form.cargo}
            onChange={handleChange('cargo')} size="small"
            sx={{ ml: 4, width: 280 }} />
        )}

        <TextField label="Observação" value={form.observacao}
          onChange={handleChange('observacao')} size="small"
          fullWidth multiline rows={2} sx={{ mt: 2 }} />

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" size="large" onClick={handleSubmit}
            disabled={submitting || !linhaId}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <SwapHorizIcon />}
          >
            Confirmar Transferência
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default TransferenciaEquipe
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/pages/TransferenciaEquipe.jsx
git commit -m "feat: add TransferenciaEquipe page"
```

---

## Task 11: Rotas em `App.jsx` e links no `Layout.jsx`

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Layout.jsx`

- [ ] **Step 1: Adicionar imports e rotas em `App.jsx`**

Adicionar imports no topo:
```jsx
import Onboarding from './pages/Onboarding'
import ManutencaoAparelho from './pages/ManutencaoAparelho'
import RouboPerdaLinha from './pages/RouboPerdaLinha'
import TransferenciaEquipe from './pages/TransferenciaEquipe'
```

Dentro do bloco de rotas privadas (após a rota `desligamento`), adicionar:
```jsx
<Route path="onboarding" element={<Onboarding />} />
<Route path="manutencao-aparelho" element={<ManutencaoAparelho />} />
<Route path="roubo-perda" element={<RouboPerdaLinha />} />
<Route path="transferencia" element={<TransferenciaEquipe />} />
```

- [ ] **Step 2: Adicionar links no menu lateral de `Layout.jsx`**

Ler o arquivo `Layout.jsx` para identificar onde ficam os links de navegação (geralmente em uma lista com `ListItem` ou `Button`).

Adicionar os novos links na seção "Telefonia" (criar seção se não existir):

```jsx
// Seção Telefonia — adicionar junto aos links de navegação existentes
<ListSubheader>Telefonia</ListSubheader>
<ListItemButton component={Link} to="/onboarding">
  <ListItemIcon><PersonAddIcon /></ListItemIcon>
  <ListItemText primary="Onboarding" />
</ListItemButton>
<ListItemButton component={Link} to="/manutencao-aparelho">
  <ListItemIcon><BuildIcon /></ListItemIcon>
  <ListItemText primary="Manutenção" />
</ListItemButton>
<ListItemButton component={Link} to="/roubo-perda">
  <ListItemIcon><ReportProblemIcon /></ListItemIcon>
  <ListItemText primary="Roubo e Perda" />
</ListItemButton>
<ListItemButton component={Link} to="/transferencia">
  <ListItemIcon><SwapHorizIcon /></ListItemIcon>
  <ListItemText primary="Transferência" />
</ListItemButton>
```

Adicionar os imports dos ícones necessários ao topo do `Layout.jsx`:
```jsx
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import BuildIcon from '@mui/icons-material/Build'
import ReportProblemIcon from '@mui/icons-material/ReportProblem'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
```

- [ ] **Step 3: Verificar navegação**

Iniciar frontend e verificar que:
- Os 4 novos links aparecem no menu lateral
- Cada rota renderiza a página correta
- O `LinhaSearch` funciona em todas as páginas (busca retorna prévia)

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/TI02/Desktop/Sistema de Chamados TI"
git add frontend/src/App.jsx frontend/src/components/Layout.jsx
git commit -m "feat: add routes and nav links for Onboarding, Manutencao, RouboPerca, Transferencia"
```

---

## Checklist de Cobertura do Spec

| Requisito do Design | Task |
|---|---|
| Busca por código (matrícula) como prioridade | Task 2 (`buscar_linha_por_codigo_ou_nome`) |
| Fallback por nome | Task 2 (mesmo função) |
| Prévia da linha antes de qualquer ação | Task 5 (`LinhaSearch` + `LinhaCard`) |
| Desligamento: campo código + prévia | Task 6 |
| Onboarding: atribuir linha VAGO | Tasks 2, 3, 7 |
| Manutenção: atualizar só aparelho | Tasks 2, 3, 8 |
| Roubo/Perda: cenário A e B | Tasks 2, 3, 9 |
| Transferência: equipe/setor/gestor/cargo | Tasks 2, 3, 10 |
| Auditoria via campo `observacao` | Todas as funções de serviço (Task 2) |
| Gerenciamento de Telefones sem alteração | Confirmado — apenas `linhas` é escrita |

---

## Execução

Plano completo e salvo. Duas opções:

**1. Subagent-Driven (recomendado)** — Um subagente por task, revisão entre tasks, iteração rápida.

**2. Inline Execution** — Execute as tasks nesta sessão com checkpoints.

Qual abordagem prefere?
