# Financial Intelligence Processing System — Backend

FRC-side platform for receiving institution case submissions, managing FRC cases,
legal rules, reports, referrals, and audit logs.

**Tech stack:** FastAPI · MongoDB Atlas · Python 3.11  
**Deployment:** Render  
**API docs:** `/docs` (Swagger UI)

---

## Project Structure

```
app/
  core/         config, database, security, dependencies, exceptions
  models/       collection shape documentation
  schemas/      Pydantic request/response models
  routers/      FastAPI route handlers
  services/     Business logic (one file per module)
  utils/
  main.py       Entry point
scripts/
  seed.py       Seeds users, institution, API key, and 20 POCAMLA legal rules
tests/
requirements.txt
Procfile        Render start command
runtime.txt     python-3.11.0
.env.example    Environment variable template
```

---

## API Endpoints

| Module | Prefix | Key endpoints |
|---|---|---|
| Health | `/` | `GET /` · `GET /health` |
| Auth | `/api/v1/auth` | `POST /login` · `GET /me` · `POST /change-password` |
| Users | `/api/v1/users` | `GET/POST /` · `GET/PUT/DELETE /{id}` |
| Institutions | `/api/v1/institutions` | `GET/POST /` · `GET/PUT /{id}` · `PATCH /{id}/status` · `POST /{id}/api-key` |
| Intake | `/api/v1/intake` | `POST /cases` ← machine auth |
| Cases | `/api/v1/cases` | `GET/` · `GET/{id}` · `PATCH/{id}/status` · `PATCH/{id}` |
| Legal Rules | `/api/v1/legal` | `GET/POST /rules` · `GET/PUT /rules/{code}` |
| Reports | `/api/v1/reports` | `GET/POST /` · `GET/PATCH /{id}` · `PATCH /{id}/status` · `GET /case/{case_id}` |
| Referrals | `/api/v1/referrals` | `GET/POST /` · `GET/{id}` · `PATCH/{id}/status` · `GET /meta/destinations` |
| Audit Logs | `/api/v1/audit-logs` | `GET /` · `GET /{id}` |

---

## Local Development

### 1. Prerequisites

- Python 3.11
- MongoDB Atlas account (free tier is fine)

### 2. Clone and install

```bash
git clone https://github.com/jeremybrighton/Financial-Intelligence-Processing-System-Public.git
cd Financial-Intelligence-Processing-System-Public
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in MONGODB_URI and JWT_SECRET_KEY
```

### 4. Run the seed script

```bash
python scripts/seed.py
```

This creates:
- 4 demo users (admin, analyst, investigator, auditor)
- 1 demo institution with API key (printed once — save it)
- 20 structured POCAMLA / POTA legal rules

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the Swagger UI.

### 6. Test the health endpoint

```bash
curl http://localhost:8000/health
```

---

## MongoDB Atlas Setup

You do **not** need a local MongoDB. Use MongoDB Atlas free tier:

1. Go to [https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account → Create a free cluster (M0)
3. Create a database user with read/write permissions
4. Under **Network Access** → Add IP `0.0.0.0/0` (allow all — fine for dev)
5. Under **Connect** → **Connect your application** → Copy the connection string
6. Replace `<username>`, `<password>` in the string and set it as `MONGODB_URI`

The database `frc_db` and all collections are created automatically on first run.

---

## Render Deployment

> You will deploy this manually on Render. These are the settings to use.

### 1. Create a new Web Service on Render

- Connect your GitHub repo: `Financial-Intelligence-Processing-System-Public`
- **Environment:** Python
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Set Environment Variables in Render Dashboard

Go to your service → **Environment** → Add these:

| Variable | Value |
|---|---|
| `MONGODB_URI` | Your MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | `frc_db` |
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(64))"` |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `API_V1_PREFIX` | `/api/v1` |
| `ALLOWED_ORIGINS` | Your frontend URL (e.g. `https://your-frontend.vercel.app`) |

### 3. Run the seed after deployment

After the service is live, use the Render shell or run the seed locally against the production DB:

```bash
MONGODB_URI=<production_uri> JWT_SECRET_KEY=<any> python scripts/seed.py
```

### 4. Verify

Visit `https://your-render-url/health` — should return:
```json
{"status": "ok", "service": "FRC Backend", "database": "connected", ...}
```

---

## Authentication

### FRC users (JWT)

```bash
# Login
curl -X POST https://your-url/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@frc.go.ke", "password": "FRCAdmin2026!"}'

# Use the token
curl https://your-url/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Institution system (API key)

```bash
# Submit a case (machine-to-machine)
curl -X POST https://your-url/api/v1/intake/cases \
  -H "X-Institution-API-Key: frc_<your_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "suspicious_activity_report",
    "title": "SAR - Unusual Transfer",
    "transaction_summary": "Customer transferred KES 2M to unknown account with no business purpose",
    "triggering_rules": ["POCAMLA-S44-STR-GENERAL"],
    "risk_score": 0.87
  }'
```

---

## Roles

| Role | Access |
|---|---|
| `frc_admin` | Full access — manage users, institutions, cases, legal, reports, referrals, audit |
| `frc_analyst` | Create/manage cases, reports, referrals |
| `investigator` | View cases and reports; add investigation notes |
| `audit_viewer` | Read-only access to cases and audit logs |

---

## Referral Destination Bodies

| Code | Agency |
|---|---|
| `FRC` | Financial Reporting Centre |
| `DCI` | Directorate of Criminal Investigations |
| `KRA` | Kenya Revenue Authority |
| `CBK` | Central Bank of Kenya |
| `EACC` | Ethics and Anti-Corruption Commission |
| `NIS` | National Intelligence Service |
| `ARA` | Asset Recovery Agency |
| `ANTI_TERROR` | Anti-Terror Unit / National Counter Terrorism Centre |
| `EGMONT` | Egmont Group (international FIU channel) |
| `CUSTOMS` | KRA Customs |
| `COMMITTEE` | Counter Financing of Terrorism Inter-Ministerial Committee |
| `OTHER` | Other authority |

---

## Next Steps (after hosting)

- Frontend integration from `Suspicious-Alert-and-Report-Centre` repo
- Connect FraudGuard ML backend to `POST /api/v1/intake/cases` using institution API key
- Add `ALLOWED_ORIGINS` to include the Vercel frontend domain
