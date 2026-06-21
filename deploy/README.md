# Lokalator Self-Managed Deployment

Recommended target: an Always Free Oracle Cloud Infrastructure Ampere A1 VM,
or any small VPS that can run Docker Compose. This stack also imports cleanly
into Coolify/Dokploy as a Docker Compose application.

## Why This Path

This project has a real Python backend with FastAPI, SQLite, PyMuPDF, python-docx,
optional ChromaDB, and optional sentence-transformers RAG. Those parts do not fit
well in static hosts or edge runtimes. A Docker Compose deployment preserves the
application shape and keeps deployment management under your control.

## Files

- `compose.yaml` runs Caddy, Next.js, and FastAPI.
- `deploy/Caddyfile` routes `/api/*` to FastAPI and everything else to Next.js.
- `backend/Dockerfile` builds the Python API.
- `frontend/Dockerfile` builds the Next.js standalone server.
- `deploy/.env.deploy.example` documents required environment variables.

## Local Smoke Test

```bash
cp deploy/.env.deploy.example deploy/.env.deploy
docker compose --env-file deploy/.env.deploy up --build
```

Open:

```text
http://localhost:8080
```

## Production Setup

1. Create an Ubuntu VM.
2. Install Docker and Docker Compose.
3. Point your domain `A` record to the VM public IP.
4. Copy `deploy/.env.deploy.example` to `deploy/.env.deploy`.
5. Set:

```bash
LOKALATOR_SITE_ADDRESS=lokalator.com
ALLOWED_ORIGINS=https://lokalator.com
ALLOWED_HOSTS=lokalator.com,www.lokalator.com
GEMINI_API_KEY=your_key
NEXT_PUBLIC_API_BASE_URL=
```

6. Run:

```bash
docker compose --env-file deploy/.env.deploy up -d --build
```

Caddy will request and renew HTTPS certificates automatically when ports 80 and
443 are open and the domain points to the server.

## RAG

`GEMINI_USE_RAG=0` is the production default because RAG pulls heavy dependencies
and builds a local ChromaDB index. To test RAG on a VM with enough memory:

```bash
GEMINI_USE_RAG=1
```

The Chroma data persists in the `lokalator_data` Docker volume via
`RAG_PERSIST_DIR=/data/chroma_db`.

The backend Dockerfile preinstalls CPU-only PyTorch before installing
`sentence-transformers` so the image does not pull unnecessary CUDA packages.
If your target architecture cannot resolve that wheel, override the build arg:

```bash
docker compose build --build-arg TORCH_INDEX_URL=https://pypi.org/simple backend
```

## Notes

- `lokalator_data` stores SQLite and Chroma data.
- `lokalator_uploads` and `lokalator_outputs` store temporary document files.
- Keep `deploy/.env.deploy` private. Do not commit it.
