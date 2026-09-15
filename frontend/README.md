# Contract Review AI — Frontend

React + TypeScript + Tailwind CSS frontend for the Contract Review AI system.

## Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Set `VITE_API_BASE_URL` in `.env` to your backend URL (default:
`http://localhost:8000`).

## Run locally

```bash
npm run dev
```

Visit http://localhost:5173.

## Build

```bash
npm run build     # type-checks and produces dist/
npm run preview   # preview the production build locally
```

## Pages

- `/login` — sign in or create an account
- `/dashboard` — list of past reviews
- `/upload` — upload a contract + reference policy and run a review
- `/reviews/:reviewId` — full review report with risk cards and clause table

## Deploying to Vercel

1. Push this repo to GitHub.
2. In Vercel, import the project and set the **root directory** to
   `frontend/`.
3. Framework preset: Vite.
4. Add the environment variable `VITE_API_BASE_URL` pointing to your
   deployed Render backend URL.
5. Deploy. Update the backend's `CORS_ORIGINS` env var to include your
   Vercel domain.
