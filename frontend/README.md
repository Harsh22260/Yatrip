# Yatrip frontend

React 19 + Vite 8 single-page app for the Yatrip platform: hotels, rentals,
food, attractions, transport and the AI assistant.

See the [root README](../README.md) for the full architecture, the API
reference and backend setup.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

The app runs on <http://localhost:5173> and expects the API on
`http://localhost:8000/api`.

> Vite inlines every `VITE_*` variable into the client bundle at build time.
> Never put a secret in `frontend/.env` - only the backend talks to model
> providers, Pinecone or the database.

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | dev server with HMR |
| `npm run build` | production bundle into `dist/` |
| `npm run preview` | serve the built bundle locally |
| `npm run lint` | ESLint over the whole project |

## Layout

```
src/
  components/     Navbar, Footer, cards, modals, shared UI
  pages/          one folder per feature area, with its own .css
  services/       api.js (fetch wrapper) + one module per domain
  hooks/          data fetching hooks
  context/        auth and session providers
  styles/         theme.css design tokens
  utils/          transport and place helpers
```

## API paths

All requests go through `src/services/api.js`, which normalises the base URL
and joins paths. Do not hard-code URLs elsewhere.

Path shape is **not** uniform, which is the most common source of 404s:

- **hotels is nested** - `api/hotels/hotels/`, `api/hotels/bookings/`
- **accounts, chatbot** - `api/accounts/`, `api/chatbot/`
- **food, attractions** - `api/food/`, `api/attractions/`
- **rentals, transport** are mounted under a prefix but register an empty
  basename, so they are `api/rentals/`, `api/transport/`

## Current state

`npm run build` passes. `npm run lint` currently reports unused-import and
`no-unused-vars` errors across several pages; these are pre-existing and do not
block the build.