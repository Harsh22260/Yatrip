# Yatrip

Travel platform with hotels, rentals, food, attractions, transport and an AI
assistant. Django + DRF + PostGIS on the backend, React 19 + Vite on the
frontend.

The interesting part is the **MCP tool server**: instead of the chatbot
scraping sources in-process, catalogue and open-data lookups are exposed as
MCP tools, and the agent discovers them over stdio. A settings-driven
**provider chain** sits underneath, so one exhausted free-tier quota does not
take the assistant offline.

---

## Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running the services](#running-the-services)
- [MCP tools](#mcp-tools)
- [API reference](#api-reference)
- [Data ingestion & RAG](#data-ingestion--rag)
- [Booking concurrency model](#booking-concurrency-model)
- [Chat session security](#chat-session-security)
- [Housekeeping task](#housekeeping-task)
- [Testing & verification](#testing--verification)
- [Troubleshooting](#troubleshooting)
- [Known gaps](#known-gaps)

---

## Architecture

```
┌──────────────────────┐
│  React 19 + Vite     │   frontend/
│  :5173               │
└──────────┬───────────┘
           │  REST (JWT) + multipart
┌──────────▼───────────┐
│  Django 5.2 + DRF    │   yatrip/
│  :8000               │
│                      │
│  accounts hotels     │
│  rentals  food       │
│  attractions reviews │
│  transport chatbot   │
└──────────┬───────────┘
           │  stdio
┌──────────▼───────────┐
│  MCP server          │   yatrip/yatrip/mcp_server.py
│  15 catalogue +      │
│  open-data tools     │
└──────────┬───────────┘
           │
    OpenStreetMap / Overpass / Nominatim / OSRM / Open-Meteo / Pinecone
```

```
┌──────────────┐   providers in order    ┌──────────────┐
│  LangGraph   │ ──────────────────────► │    Gemini    │
│  agent       │      (skip if out of    ├──────────────┤
│  + MCP tools │       quota / no key)   │     Groq     │
│  + RAG       │ ──────────────────────► ├──────────────┤
└──────────────┘                          │ OpenRouter   │
                                          └──────────────┘
```

Apps live at `yatrip/<app>/` as top-level Django apps; the project package is
`yatrip/yatrip/`. So imports read `from chatbot import rag`, not
`from yatrip.chatbot import rag`.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | verified on 3.10.10 |
| Node.js | 20.19+ or 22.12+ | this is the `engines` floor Vite 8 enforces |
| PostgreSQL | 14+ | **with PostGIS and pgvector** |
| GDAL + GEOS | any recent | needed by `django.contrib.gis` |

`pgvector` is in `INSTALLED_APPS` as `pgvector.django`, so the database needs
the extension:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

GDAL and GEOS cannot be pip-installed, especially on Windows. Point
`GDAL_LIBRARY_PATH` / `GEOS_LIBRARY_PATH` at your install (OSGeo4W on Windows,
`brew install gdal geos` or `apt install libgdal-dev libgeos-dev` elsewhere).

---

## Quick start

### 1. Backend

```bash
cd yatrip
python -m venv ../venv
source ../venv/Scripts/activate   # Windows PowerShell
# source ../venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create the database, then configure the environment:

```bash
cp .env.example .env
# edit .env - at minimum set SECRET_KEY, DB_* and PINECONE_API_KEY
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app is then on <http://localhost:5173> and the API on
<http://localhost:8000/api>.

> Vite inlines every `VITE_*` variable into the client bundle. Keep secrets out
> of `frontend/.env`; only the backend talks to model providers, Pinecone or
> the database.

---

## Configuration

Everything is environment-driven. `yatrip/.env.example` documents every
variable; `.env` is gitignored and must never be committed.

### Required

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing key |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | PostgreSQL |
| `PINECONE_API_KEY` | RAG vector store |

### Recommended

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | - | primary model provider |
| `GROQ_API_KEY` | - | second link in the chain |
| `DEBUG` | `False` | |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | comma separated |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,...` | must match Vite origin |

### The provider chain

```
LLM_PROVIDER_CHAIN=gemini:gemini-3.8-flash,groq:openai/gpt-oss-120b
```

Comma-separated `provider:model` pairs, tried in order. Supported providers:
`gemini`, `groq`, `openai`, `openrouter`. Entries whose API key is missing are
skipped automatically, so it is safe to list a provider before adding its key.
See `yatrip/chatbot/llm.py`.

> **Why this matters:** Gemini's free tier is capped at roughly 20
> `generateContent` requests per day per model. A single provider with a daily
> cap is not a production dependency. Add `GROQ_API_KEY` and the agent
> transparently walks to the next provider. When a provider reports a daily
> quota exhaustion it is tripped in a circuit breaker and skipped for the rest
> of the process lifetime instead of being retried into a timeout.

---

## Running the services

```bash
cd yatrip
python manage.py runserver                 # API on :8000
python manage.py mcp_server                # MCP server on stdio
python manage.py mcp_server --transport streamable-http --port 8001
```

The chatbot spawns the MCP server itself over stdio (`python -m
yatrip.mcp_server`, see `MCP_SERVER_MODULE`); you only need to run it manually
when testing tools in isolation.

`ingest_data` is an alias for `sync_rag` - it pushes catalogue rows into Pinecone
so the agent can answer from retrieval. It is not an image pipeline; for that see
[image backfill](#image-backfill).

### Image backfill

Attraction and food images are filled from Wikimedia Commons, which is
attribution-friendly. Each command is resumable and only fills rows that have no
image yet.

```bash
python manage.py backfill_attraction_images --city Bengaluru
python manage.py backfill_food_images                  # all categories
python manage.py backfill_food_images --place "Truffles" # one row
python manage.py backfill_food_images --all-categories
```

`backfill_attraction_images` has `--limit` and `--refresh`; `backfill_food_images`
has `--place` and `--refresh`. `--refresh` re-looks-up rows that already have an
image.

---

## MCP tools

15 tools, verified live over stdio. Catalogue tools read the local database;
open-data tools call OSM/Overpass/Nominatim/OSRM/Open-Meteo.

| Tool | Does |
|---|---|
| `search_hotels` | hotel search with filters |
| `get_hotel_details` | single hotel with rooms and rates |
| `check_room_availability` | live room availability for a date range |
| `search_attractions` | attraction search |
| `search_food` | food place search |
| `search_rentals` | rental / PG search |
| `find_transport_nodes` | transport nodes near a point |
| `nearby_transport_nodes` | closest N transport nodes |
| `geocode_place` | place name → coordinates |
| `reverse_geocode` | coordinates → address |
| `search_nearby_places` | Overpass POI search |
| `get_weather` | forecast via Open-Meteo |
| `get_directions` | OSRM road route with GeoJSON |
| `web_search` | optional web search |
| `search_knowledge_base` | Pinecone RAG search |

Verify them yourself:

```bash
cd yatrip
python -c "
import asyncio, django; django.setup()
from chatbot import mcp_client
tools = asyncio.run(mcp_client.get_tools(force_refresh=True))
print(len(tools), 'tools')
"
```

---

## API reference

Base URL `http://localhost:8000/api`. Auth is JWT (`Bearer <access>`); refresh
at `accounts/token/refresh/`.

### Accounts

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `accounts/register/` | no | `is_owner` + `business_name` / `business_type` / `business_address` / `contact_number` creates the `OwnerProfile` in the same transaction |
| POST | `accounts/login/` | no | returns `access` + `refresh` |
| POST | `accounts/token/refresh/` | no | |
| POST | `accounts/logout/` | yes | blacklists the refresh token |
| GET/PATCH | `accounts/profile/` | yes | |
| GET/PATCH | `accounts/owner/` | yes | GET auto-provisions a missing profile instead of 500ing |
| POST | `accounts/owner/create/` | yes | upsert - 201 on create, 200 on update |

### Hotels

The hotels app is mounted at `api/hotels/`, so the resource paths carry a
second segment: `api/hotels/hotels/`, `api/hotels/bookings/`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `hotels/hotels/` | no | `?mine=true` for owners |
| POST | `hotels/hotels/` | owner | |
| GET/PATCH/DELETE | `hotels/hotels/{id}/` | owner for writes | `is_verified` is read-only |
| GET/POST | `hotels/room-types/` | no / owner | `?hotel=<id>` |
| GET/POST | `hotels/room-units/` | no / owner | `?room_type=<id>` |
| GET/POST | `hotels/rate-plans/` | no / owner | `?room_type=<id>` |
| GET | `hotels/availability/` | no | `?room_type=&date__gte=&date__lte=` |
| POST | `hotels/hotels/{id}/generate_availability/` | owner | |
| GET/POST | `hotels/bookings/` | yes | POST creates a **hold** and returns `hold_token` |
| POST | `hotels/bookings/{id}/confirm/` | yes | body `{ "hold_token": "..." }` |
| POST | `hotels/bookings/{id}/cancel/` | yes | releases inventory |

Cross-hotel relations are rejected, and a child object cannot be reassigned to
another owner's hotel.

### Food / attractions / rentals / transport

These apps are mounted directly under `api/`, so the resource path *is* the
route - there is no `/api/` + resource name doubling.

| Method | Path |
|---|---|
| GET | `food/`, `food/nearby/?lat=&lon=`, `food/categories/`, `food/cuisines/`, `food/random/` |
| GET/POST | `food/{id}/menu-items/` |
| DELETE | `food/{id}/menu-items/{item_id}/` |
| POST | `food/import-area/`, `food/import-city/` |
| GET | `attractions/`, `attractions/nearby/?lat=&lon=`, `attractions/categories/`, `attractions/random/` |
| GET | `rentals/`, `rentals/nearby/?lat=&lon=`, `rentals/my_rentals/` |
| GET/POST | `rentals/images/`, `rentals/amenities/` |
| GET | `transport/`, `transport/nearby/?lat=&lon=` |
| GET | `transport/route/?start_lat=&start_lon=&end_lat=&end_lon=` |
| POST | `transport/load_area/` |
| GET | `transport/load_area_status/?job_id=` |

> Only the **hotels** app is nested (`api/hotels/hotels/`). The others are
> single-segment. Getting this wrong returns `404`, or a confusing
> `Field 'id' expected a number but got 'attractions'` because the router read
> your path segment as a primary key.

`transport/route/` returns a real OSRM route with a GeoJSON `LineString`:

```json
{
  "start": [12.9716, 77.5946],
  "end": [13.0827, 77.7299],
  "distance_km": 25.92,
  "duration_min": 25.3,
  "geometry": { "type": "LineString", "coordinates": [[...]] },
  "source": "OSRM"
}
```

It answers `503` with `"code": "routing_unavailable"` when OSRM is down, and
`400` for non-numeric, missing or out-of-range coordinates.

`transport/load_area/` starts a background OSM import for a bounding box and
returns immediately; poll `transport/load_area_status/?job_id=` for the outcome.

### Chatbot

| Method | Path | Notes |
|---|---|---|
| POST | `chatbot/chat/` | `multipart/form-data`: `message`, optional `session_id`, `access_key`, `image` |
| GET | `chatbot/history/` | `?session_id=&access_key=` |
| POST | `chatbot/clear/` | `{ "session_id": ..., "access_key": ... }` |
| GET | `chatbot/sessions/` | |

---

## Data ingestion & RAG

Attractions, food and transport come from OpenStreetMap:

```bash
python manage.py fetch_attractions --city Bengaluru --radius 10000
python manage.py fetch_food --city Bengaluru --radius 5000
python manage.py fetch_transport --city Bengaluru --radius 30
```

`fetch_transport` reads bus stands, auto stands, metro, railway and airport hubs.
Besides `--city`, it accepts `--lat`/`--lon`, `--state`, and `--all-cities N` to
walk the settlement index. `--reclassify` re-runs operator/name classification
over stored rows and exits without fetching.

The `--all-cities` mode needs the settlement index:

```bash
python manage.py build_settlements          # all of India
python manage.py build_settlements --limit 200 --fresh --delay 1.2
```

There are roughly 650k villages in India, so the default is deliberately slow
with a per-cell delay. `--limit` caps the number of grid cells (`0` = the whole
country) and `--fresh` deletes existing settlements first.

Push catalogue data into Pinecone:

```bash
python manage.py sync_rag --status                # index state
python manage.py sync_rag --model hotel
python manage.py sync_rag --model all --recreate  # drop and rebuild
```

`sync_rag` is the canonical entry point. `ingest_data` is an alias, and
`scripts/auto_rag_sync.py` just delegates to it. The index is 3072-dimensional -
if you change `PINECONE_EMBEDDING_DIMENSION` you must `--recreate`, otherwise
the upserts will fail on a dimension mismatch.

**Set `OSM_USER_AGENT` to something identifying.** The public Nominatim and
Overpass endpoints block generic user agents and will return 403/504.

---

## Booking concurrency model

Availability rows are `(room_type, date, room_unit)`. Overbooking is prevented
with row locks, not application-level checks:

- creating a hold takes `SELECT ... FOR UPDATE` on every availability row in
  the range inside a single transaction, and decrements `available_rooms`;
- if any row has nothing left, the whole transaction rolls back;
- the response carries a `hold_token`; `confirm` redeems it;
- cancel and expiry both release the same rows and are idempotent.

Verified: 8 concurrent requests for the last remaining room yield exactly 1
success and 7 `409`s. The `(room_type, date)` unique constraint is conditional
on `room_unit IS NULL`, which lets a room type hold a pooled inventory row
while individual units keep their own rows.

---

## Chat session security

Sessions have a UUID primary key, which is not a secret. Anonymous access is
therefore gated on a separate 43-character `access_key`:

- a logged-in owner can read their own sessions;
- an anonymous caller must present the matching `access_key` via query string
  or body;
- guessing a session UUID returns `403`, not another user's transcript;
- internal exception text is never returned to the client.

The frontend keeps both `session_id` and `access_key` in `localStorage`
(`yatrip_chat_session`, `yatrip_chat_access_key`). Clearing the chat clears
both.

---

## Housekeeping task

Holds left unconfirmed block inventory forever, so they need expiring:

```bash
python manage.py shell -c "from hotels.tasks import expire_pending_bookings; print(expire_pending_bookings())"
```

The task is `hotels.expire_stale_holds` (Celery `shared_task`). It handles both
`HELD` and legacy `PENDING` bookings. **There is no Celery beat schedule
configured**, so run it from cron/Celery beat in your deployment - see
[Known gaps](#known-gaps).

---

## Testing & verification

```bash
cd yatrip
python manage.py check
python -m pip check
```

The end-to-end API regression script (58 checks covering hotel ownership,
booking concurrency, account registration, owner profiles and chat session
authorization) is **not committed** - it is a scratch script, not part of the
repository. Re-create it if you need it.

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Current state: `manage.py check` clean, `pip check` clean, 15 MCP tools live,
API regression 58/58, `npm run build` passing.

`npm run lint` is **not** clean - it reports unused-import and `no-unused-vars`
errors across several pages. These are warnings-level and do not block
`npm run build`, but they are pre-existing and unresolved.

---

## Troubleshooting

**`Invalid HTTP_HOST header: 'testserver'`** - correct behaviour, not a bug.
Override in tests:

```python
from django.test import override_settings
with override_settings(ALLOWED_HOSTS=["testserver"]):
    ...
```

**`ModuleNotFoundError: No module named 'yatrip.chatbot'`** - apps are
top-level. Import `chatbot.rag`, not `yatrip.chatbot.rag`.

**`DisallowedHost` / missing CORS headers** - add your frontend origin to
`CORS_ALLOWED_ORIGINS` and the host to `ALLOWED_HOSTS`.

**Chatbot says the providers are exhausted** - expected once Gemini's daily
quota is gone. Check the `LLM_PROVIDER_CHAIN`, then add the missing key.

**Overpass `504 Gateway Timeout`** - the public endpoint is rate limited and
often overloaded. Lower `OVERPASS_TIMEOUT` and retry, or point at a mirror.

**Pinecone dimension mismatch on ingest** - the index was built at a different
dimensionality. Re-run with `--recreate`.

**Frontend requests 404 on a catalogue call** - path shape. Only the hotels
app is nested, so it is `api/hotels/hotels/`, but food, attractions, rentals
and transport are single-segment (`api/food/`, `api/attractions/`). All paths
are centralised in `frontend/src/services/api.js`; use it rather than
hard-coding URLs.

---

## Known gaps

- **Stale-hold expiry is not scheduled.** The task exists but Celery beat is
  not configured, so holds only expire when something runs it manually.
- **The `reviews` app has no `urls.py`** and is not wired into the root URLconf.
  Its models exist; there is no HTTP surface yet.
- **`reviews`, `food` and `attractions` menu entries** link to pages that exist
  but are not part of the owner dashboard flow.
- **Production server config is not included.** `runserver` is for development
  only; use gunicorn/uvicorn with a real static file setup.
- **No automated test suite is committed.** Verification is manual via the
  regression script.
- **Open data coverage is OSM-only**, so it reflects what is mapped, not what
  exists. For production listing data you would want a commercial provider.
- **Vision input is Gemini-only.** The default Groq fallback model is
  text-only, so image uploads will not fall back.

---

## License

Unlicensed / private. All rights reserved.
