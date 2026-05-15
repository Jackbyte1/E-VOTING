# Secure Student E-Voting System

Working full-stack prototype for a secure student e-voting workflow.

## Stack

- Backend: Python, Flask, REST APIs
- Frontend: HTML, CSS, Vanilla JavaScript
- Database: SQLite for local fallback, PostgreSQL for online deployment
- Security: bcrypt password hashing, OTP verification, Flask sessions, AES-GCM vote encryption, SHA-256 vote receipts, hash-chained audit logs
- V2 features: structured voting by position, live polling results, dashboard statistics, vote hash verification, student profiles
- UI upgrade: role-aware navigation, student dashboard, protected student/admin pages, responsive SaaS-style layout
- Research-design match: RSA-wrapped AES vote keys, Merkle root publication, DB-level vote immutability triggers, session timeout, voter/role management, CSV report export

## Project Structure

```text
project-root/
  backend/
    app.py
    config.py
    seed.py
    models/
    routes/
    services/
    utils/
  database/
    schema.sql
    schema_postgres.sql
    evoting.db
  frontend/
    css/
    html/
    js/
  requirements.txt
  README.md
```

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Optional: copy `.env.example` to `.env`.

For SQLite local testing, leave `DATABASE_URL` empty or remove it from `.env`.
For PostgreSQL local testing, create a database named `securevote` and set:

```text
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/securevote
```

4. Seed sample data.

```bash
python -m backend.seed
```

5. Start the Flask server.

```bash
python -m backend.app
```

6. Open the app.

```text
http://127.0.0.1:5000
```

## Demo Accounts

Admin:

```text
Email: jacksonndirangu25@gmail.com
Password: Kihikoko
```

Student:

```text
Email: student@school.edu
Password: StudentPass123
```

## OTP Flow

This prototype simulates email delivery. The OTP is printed in the Flask console. In local development only, set `EXPOSE_DEV_OTP=true` to also return `dev_otp` from `/login` for quick browser testing. Keep `EXPOSE_DEV_OTP=false` on Render.

## Required API Endpoints

Auth:

- `POST /register`
- `POST /login`
- `POST /verify-otp`

Voting:

- `GET /election`
- `POST /vote`
- `GET /results`
- `GET /stats`
- `GET /verify-vote?hash=...`
- `GET /profile`
- `GET /me`

Admin:

- `POST /admin/create-election`
- `POST /admin/add-candidate`
- `POST /admin/open-election`
- `POST /admin/close-election`
- `GET /admin/results`
- `GET /admin/stats`
- `GET /admin/audit-logs`
- `GET /admin/users`
- `POST /admin/update-user-role`
- `GET /admin/export-report`

Additional helper endpoints:

- `POST /logout`
- `GET /admin/elections`

## Security Notes

- Passwords are stored as bcrypt hashes.
- OTPs expire after 10 minutes by default.
- Votes are logically append-only. The application never updates or deletes vote rows.
- Duplicate voting is blocked per student, election, and position.
- Vote verification is restricted to authenticated students.
- Each vote is encrypted before storage with AES-GCM.
- Each vote uses a fresh AES-256 key wrapped with a local RSA-2048 public key for prototype key management.
- Each vote returns a SHA-256 verification hash to the student.
- SQLite and PostgreSQL triggers reject any `UPDATE` or `DELETE` against the `votes` table.
- Audit logs are hash chained using `previous_hash` and `current_hash`.
- Closing an election computes and stores a Merkle root over vote receipt hashes.
- Flask sessions are HTTP-only and SameSite Lax for the local prototype.

## Version 2 Notes

- Candidates are grouped by `position` in the voting UI.
- Students can cast one vote for each position in an active election.
- Student navigation shows Dashboard, Vote, Profile, Verify Vote, and Logout.
- Admin navigation shows Dashboard, Results, Audit Logs, and Logout. Admins cannot access student vote verification.
- Results include `total_votes` and `percentage` for each candidate within that position.
- Dashboard statistics show registered voters, votes cast, turnout, and candidate count.
- Existing SQLite databases are migrated automatically on startup to add `users.institution_id`, `users.reg_number`, `users.course`, `candidates.manifesto`, `votes.position`, vote key metadata, Merkle roots, and immutable vote triggers.
- PostgreSQL is selected automatically when `DATABASE_URL` is present.

## Render Deployment Notes

Create a Render PostgreSQL database, then create a Render Web Service from your GitHub repository.

Recommended Render settings:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn backend.app:app
```

Required environment variables:

```text
DATABASE_URL=<Render PostgreSQL internal database URL>
SECRET_KEY=<strong random secret>
FLASK_ENV=production
PYTHON_VERSION=3.11.11
VOTE_ENCRYPTION_KEY=<32+ character secret; first 32 bytes are used>
VOTE_RSA_PRIVATE_KEY=<one-line PEM generated by backend.utils.generate_render_secrets>
VOTE_RSA_PUBLIC_KEY=<one-line PEM generated by backend.utils.generate_render_secrets>
FRONTEND_ORIGIN=https://your-render-app.onrender.com
SESSION_COOKIE_SECURE=true
EXPOSE_DEV_OTP=false
AUTO_SEED_ON_STARTUP=false
SEED_ADMIN_EMAIL=jacksonndirangu25@gmail.com
SEED_ADMIN_PASSWORD=Kihikoko
```

Generate strong Render secrets locally with:

```bash
python -m backend.utils.generate_render_secrets
```

After the first deploy, run the seed command once from a Render shell/job or locally against the Render database if you want demo accounts:

```bash
python -m backend.seed
```

## Prototype Limits

The local prototype simulates production controls where a campus deployment would use managed services: local RSA keys are stored under `database/keys`, Render deployments should use `VOTE_RSA_PRIVATE_KEY` and `VOTE_RSA_PUBLIC_KEY`, OTP delivery is simulated, and HTTPS/backups are handled by the deployment environment.

For production, move `SECRET_KEY` and `VOTE_ENCRYPTION_KEY` into a managed secret store, enforce HTTPS, restrict CORS, add CSRF protection, harden admin provisioning, and use a stronger election-specific cryptographic protocol.
