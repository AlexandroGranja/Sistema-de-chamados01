"""
Migra usuários de usuarios_app (PostgreSQL) para Keycloak.
Executa UMA VEZ. Usuários recebem email para redefinir senha.

Uso:
  python scripts/migrate_users_to_keycloak.py
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]
KEYCLOAK_ADMIN_USER = os.environ["KEYCLOAK_ADMIN_USER"]
KEYCLOAK_ADMIN_PASS = os.environ["KEYCLOAK_ADMIN_PASSWORD"]
DATABASE_URL = os.environ["DATABASE_URL"]

import psycopg


def get_admin_token(client: httpx.Client) -> str:
    resp = client.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KEYCLOAK_ADMIN_USER,
            "password": KEYCLOAK_ADMIN_PASS,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def list_pg_users() -> list[dict]:
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT username, email, nome_exibicao, is_admin, ativo FROM usuarios_app ORDER BY id"
        ).fetchall()
    return [
        {
            "username": r[0],
            "email": r[1] or "",
            "nome_exibicao": r[2] or r[0],
            "is_admin": r[3],
            "ativo": r[4],
        }
        for r in rows
    ]


def create_keycloak_user(client: httpx.Client, token: str, user: dict) -> str | None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    parts = user["nome_exibicao"].split()
    safe_username = user["username"].replace(" ", ".").lower()
    payload = {
        "username": safe_username,
        "email": user["email"] or f"{safe_username}@prosper.local",
        "firstName": parts[0] if parts else user["username"],
        "lastName": " ".join(parts[1:]) if len(parts) > 1 else "",
        "enabled": user["ativo"],
        "emailVerified": True,
    }
    resp = client.post(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
        json=payload,
        headers=headers,
    )
    if resp.status_code == 409:
        print(f"  SKIP {user['username']} (já existe)")
        return None
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    user_id = location.rstrip("/").split("/")[-1]
    return user_id


def assign_realm_role(client: httpx.Client, token: str, user_id: str, role_name: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    roles_resp = client.get(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/roles",
        headers=headers,
    )
    roles_resp.raise_for_status()
    role = next((r for r in roles_resp.json() if r["name"] == role_name), None)
    if not role:
        print(f"  WARN role '{role_name}' não encontrada")
        return
    client.post(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
        json=[{"id": role["id"], "name": role["name"]}],
        headers=headers,
    )


def send_password_reset(client: httpx.Client, token: str, user_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    client.put(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/execute-actions-email",
        json=["UPDATE_PASSWORD"],
        headers=headers,
    )


def main():
    users = list_pg_users()
    print(f"Encontrados {len(users)} usuários no PostgreSQL.")

    with httpx.Client(timeout=30) as client:
        token = get_admin_token(client)

        for user in users:
            print(f"Migrando: {user['username']} (admin={user['is_admin']}) ...")
            user_id = create_keycloak_user(client, token, user)
            if user_id:
                role = "admin" if user["is_admin"] else "user"
                assign_realm_role(client, token, user_id, role)
                if user["email"]:
                    send_password_reset(client, token, user_id)
                    print(f"  OK — email de reset enviado para {user['email']}")
                else:
                    print(f"  OK — sem email, definir senha manualmente no Admin Console")

    print("\nMigração concluída.")


if __name__ == "__main__":
    main()
