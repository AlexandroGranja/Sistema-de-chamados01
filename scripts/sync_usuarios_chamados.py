"""Sincroniza `usuarios_app` (Gerenciamento) → `users` (Chamados React).

Encapsula o script do backend FastAPI para uso no Streamlit e em `criar_admin`.

Uso:
    python -m scripts.sync_usuarios_chamados
    python -m scripts.sync_usuarios_chamados --dry-run
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "Sistema de Chamados TI" / "backend"
SYNC_SCRIPT = BACKEND / "scripts" / "sync_users_from_usuarios_app.py"


def _python_backend() -> Path:
    candidates = [
        BACKEND / "venv" / "Scripts" / "python.exe",
        BACKEND / "venv" / "bin" / "python",
        Path(sys.executable),
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return Path(sys.executable)


def executar_sync(*, dry_run: bool = False, timeout: int = 120) -> tuple[bool, str]:
    """
    Executa sync_users_from_usuarios_app.py no venv do backend.
    Retorna (sucesso, mensagem_resumida).
    """
    if not SYNC_SCRIPT.is_file():
        return False, f"Script não encontrado: {SYNC_SCRIPT}"

    py = _python_backend()
    cmd = [str(py), str(SYNC_SCRIPT)]
    cmd.append("--dry-run" if dry_run else "--yes")

    env = os.environ.copy()
    backend_env = BACKEND / ".env"
    if backend_env.is_file():
        env.setdefault("DOTENV_PATH", str(backend_env))

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, "Sync expirou (timeout)."
    except OSError as exc:
        return False, f"Falha ao executar sync: {exc}"

    output = "\n".join(part for part in (proc.stdout or "", proc.stderr or "") if part).strip()
    if proc.returncode != 0:
        tail = output[-600:] if output else f"exit code {proc.returncode}"
        return False, tail

    if dry_run:
        return True, output or "Dry-run concluído (nenhuma alteração)."
    last_line = (output.splitlines() or ["Sync concluído."])[-1]
    return True, last_line


def main() -> int:
    dry = "--dry-run" in sys.argv
    ok, msg = executar_sync(dry_run=dry)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
