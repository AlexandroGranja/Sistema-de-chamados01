"""Serviço SMTP centralizado. Usado por Streamlit e FastAPI."""
from __future__ import annotations

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # segundos entre tentativas


def _smtp_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "email.locaweb.com.br").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "from_addr": os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")).strip(),
    }


def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
) -> bool:
    """
    Envia e-mail via SMTP Locaweb com STARTTLS.
    Retorna True se enviado, False se falhou (falha silenciosa — não quebra fluxo).
    """
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("SMTP não configurado — e-mail não enviado.")
        return False

    recipients = [to] if isinstance(to, str) else to
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(recipients)

    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_addr"], recipients, msg.as_string())
            logger.info("E-mail enviado para %s", recipients)
            return True
        except Exception as exc:
            logger.warning("Tentativa %d/%d falhou: %s", attempt, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)

    logger.error("Falha ao enviar e-mail para %s após %d tentativas.", recipients, _MAX_RETRIES)
    return False


def send_reset_email(to: str, reset_url: str) -> bool:
    """Envia e-mail de reset de senha para admin."""
    subject = "Redefinição de senha — Gerenciamento de Telefones"
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;">
    <h2 style="color:#111827;">Redefinição de senha</h2>
    <p>Você solicitou a redefinição da sua senha de administrador.</p>
    <p>Clique no botão abaixo para criar uma nova senha. O link é válido por <strong>1 hora</strong> e pode ser usado apenas uma vez.</p>
    <p style="margin:24px 0;">
        <a href="{reset_url}" style="background:#f2c230;color:#111827;padding:12px 24px;
           border-radius:6px;text-decoration:none;font-weight:700;">
           Redefinir minha senha
        </a>
    </p>
    <p style="color:#666;font-size:0.85em;">Se você não solicitou este e-mail, ignore-o. Sua senha não será alterada.</p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#999;font-size:0.8em;">Prosper Distribuidora — Sistema de Gerenciamento de Telefones</p>
    </body></html>
    """
    body_text = (
        f"Redefinição de senha\n\n"
        f"Acesse o link abaixo (válido por 1 hora):\n{reset_url}\n\n"
        f"Se não solicitou, ignore este e-mail."
    )
    return send_email(to, subject, body_html, body_text)


def send_chamado_notification(
    admins_emails: list[str],
    numero_chamado: str,
    titulo: str,
    solicitante: str,
    aberto_em: str,
    descricao: str = "",
) -> bool:
    """Notifica admins quando novo chamado é aberto."""
    subject = f"[Chamado #{numero_chamado}] {titulo}"
    desc_html = f"<p><strong>Descrição:</strong> {descricao}</p>" if descricao else ""
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;">
    <h2 style="color:#111827;">Novo chamado aberto</h2>
    <table style="border-collapse:collapse;width:100%;max-width:600px;">
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;width:140px;">Número</td>
          <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">#{numero_chamado}</td></tr>
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;">Título</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{titulo}</td></tr>
      <tr><td style="padding:8px;border-bottom:1px solid #eee;color:#666;">Solicitante</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{solicitante}</td></tr>
      <tr><td style="padding:8px;color:#666;">Aberto em</td>
          <td style="padding:8px;">{aberto_em}</td></tr>
    </table>
    {desc_html}
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
    <p style="color:#999;font-size:0.8em;">Prosper Distribuidora — Sistema de Chamados TI</p>
    </body></html>
    """
    return send_email(admins_emails, subject, body_html)
