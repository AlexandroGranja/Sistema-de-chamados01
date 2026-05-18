"""
Estado da integração Snipe-IT definido na subida da aplicação (lifespan).
O endpoint snipe-status usa este valor para evitar divergência com o worker.
"""
snipe_configured_at_startup: bool = False
