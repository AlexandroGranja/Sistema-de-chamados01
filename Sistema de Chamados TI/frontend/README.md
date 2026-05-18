# Frontend - Sistema de Chamados TI

Aplicacao React (Vite) para uso do sistema de chamados.

## Requisitos

- Node.js 18+
- npm

## Subir local (Windows/PowerShell)

```powershell
cd "c:\Users\TI02\Desktop\Sistema de Chamados TI\frontend"
npm install
npm run dev
```

URL local:
- `http://localhost:3000` (ou porta exibida no terminal)

## Variaveis de ambiente (`frontend/.env`)

Opcao 1 - proxy do Vite (recomendado local):

```env
VITE_API_URL=
```

Opcao 2 - URL direta do backend:

```env
VITE_API_URL=http://localhost:8000
```

Sempre reinicie o `npm run dev` apos alterar o `.env`.

## Comandos uteis

```bash
npm run dev
npm run build
npm run preview
```

## Build para servidor

```bash
npm ci
npm run build
```

O build final fica em `frontend/dist` para publicacao via Nginx/Apache.

