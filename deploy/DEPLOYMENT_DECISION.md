# Deployment Decision

Chosen path: self-managed Docker Compose on a small VM, preferably Oracle Cloud
Infrastructure Always Free Ampere A1. The same Compose stack can also be
imported into Coolify or Dokploy.

## Why This Is The Best Fit

Lokalator is not just a static site. The project includes:

- Next.js frontend
- FastAPI backend
- SQLite analytics
- PDF/DOCX processing through PyMuPDF and python-docx
- optional RAG through ChromaDB and sentence-transformers
- Gemini API calls through backend environment variables

Static hosting and edge/serverless runtimes require too many rewrites for this
shape. A Docker Compose stack keeps the current application intact and gives the
owner direct control over logs, env vars, volumes, reverse proxy, SSL, and
rollback.

## Options Considered

### Oracle Cloud Always Free VM + Docker Compose

Best fit for the current requirement: free, long-lasting, self-managed, and able
to run normal Python containers.

Important official limits:

- Always Free resources are available for the life of the account.
- Ampere A1 Always Free gives 2 OCPUs and 12 GB memory total.
- Always Free Block Volume includes 200 GB total storage.
- Idle Always Free compute instances may be reclaimed by Oracle.

Source: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

### Coolify / Dokploy / CapRover

These are not hosting providers by themselves. They are self-hosted deployment
panels that run on a server you control. They are useful if the VM should have a
dashboard instead of pure SSH + Docker Compose.

Sources:

- https://coolify.io/docs/
- https://coolify.io/pricing
- https://docs.dokploy.com/docs/core
- https://caprover.com/

### Cloudflare Workers

Not chosen for the full backend. The free Worker limits are too tight for the
current Python dependency graph: 10 ms CPU, 128 MB memory, and 3 MB compressed
Worker size.

Source: https://developers.cloudflare.com/workers/platform/limits/

### GitHub Pages

Useful only for static frontend hosting. It cannot run the FastAPI backend or
protect Gemini keys by itself.

Source: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

### Google Apps Script

Technically possible for a small JavaScript rewrite of the API, but not suitable
for preserving the existing Python backend, RAG, PDF/DOCX processing, and local
SQLite behavior.

Source: https://developers.google.com/apps-script/guides/services/quotas

### Google Cloud Run

Good fallback if Oracle Cloud capacity is unavailable. It runs containers and
has a free tier, but it is more managed and requires stricter cost controls.

Source: https://cloud.google.com/run/pricing
