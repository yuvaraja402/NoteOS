# Frontend

React and Next.js notes workspace, served on port `3050`.

From this directory:

```bash
cp .env.example .env.local
npm ci
npm run dev
```

Start FastAPI using [the backend instructions](../backend/README.md), then open
http://localhost:3050. Local `/api/*` requests go through the Next.js proxy to
`API_INTERNAL_URL`. This variable is server-side configuration, not a secret;
credentials must never be added to it or to `NEXT_PUBLIC_*` variables.

```bash
npm run lint
npm run build
npm start
```

From the repository root, build the standalone runtime image with:

```bash
docker build -t noteos-web ./frontend
```

In AWS, the ALB sends `/api/*` directly to FastAPI and other paths to Next.js.
The frontend needs no SSM permissions or database credentials.
