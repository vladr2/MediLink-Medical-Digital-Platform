# 🏥 MediLink — Digital Healthcare Platform

> Bachelor's Thesis · Faculty of Computer Science · 2026

MediLink is a comprehensive medical platform that connects patients, doctors, and medical assistants in a unified, secure, and GDPR-compliant system.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.11), SQLAlchemy, PostgreSQL, Redis |
| **Frontend** | Angular 19, Angular Material (M3), Tailwind CSS |
| **AI** | Groq API (Llama 3.3 70B) — medical chat & risk prediction |
| **Real-time** | WebSockets (notifications, messaging, video) |
| **Video** | WebRTC (peer-to-peer teleconsultations) |
| **Infra** | Docker Compose, Nginx (reverse proxy + rate limiting) |

---

## Core Features

### 👤 Patient
- Personal dashboard with statistics and upcoming appointments
- Electronic Health Records (EHR) covering consultations, lab results, treatments, and prescriptions
- Vitals tracking with evolution charts and automated alerts
- AI Medical Chat (Groq / Llama 3.3)
- Online appointment booking with confirmation
- Real-time messaging with doctors, assistants, and other patients
- Full GDPR user data export (HTML + JSON)
- Video teleconsultations (WebRTC)

### 🩺 Doctor
- Dashboard with assigned patients and daily schedule
- Comprehensive medical records for each patient (paginated)
- AI Risk Prediction per patient (1–10 score with recommendations)
- Auto-generated AI medical reports (PDF format)
- Global statistics and vital signs overview for all patients
- Patient reviews with AI sentiment analysis

### 🗂️ Medical Assistant
- Appointment management and patient-to-doctor assignment
- Vital signs data entry for patients
- Direct access to patient statistics and vitals

### 🔧 Admin
- Platform statistics dashboard and graphical charts
- User management (activate/deactivate accounts, role assignment)
- Global overview of all platform appointments

---

## Quickstart (Docker)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/)

### Steps

```bash
# 1. Clone the repository
git clone [https://github.com/vladr2/MediLink.git](https://github.com/vladr2/MediLink.git)
cd MediLink

# 2. Configure environment variables
cp .env.example .env
# Edit the .env file and add your GROQ_API_KEY (get it for free at console.groq.com)

# 3. Start the entire application stack
docker compose up --build

# 4. Apply database migrations (first run only)
docker compose exec backend alembic upgrade head

# 5. (Optional) Populate the database with realistic demo data
docker compose exec backend python seed_data.py
```

The application will be available at:
-Frontend: http://localhost (via Nginx) or http://localhost:4200 (direct)
-API Docs (Swagger): http://localhost:8000/api/docs
-API Docs (via Nginx): http://localhost/api/docs
-Backend direct: http://localhost:8000/api
---

## Demo Accounts

> All demo accounts use the password: **`Parola123!`**

| Rol | Email | Nume |
|---|---|---|
| 🔧 Admin | `admin@medilink.com` | Alexia Radoi |
| 🩺 Doctor | `doctor@medilink.com` | Mihai Constantin |
| 🩺 Doctor | `alexandru.ionescu@gmail.com` | Alexandru Ionescu |
| 🩺 Doctor | `maria.popescu@gmail.com` | Maria Popescu |
| 🗂️ Assistant | `asistent@medilink.com` | Daniela Vlad |
| 🗂️ Assistant | `asistent2@medilink.com` | Ana Florescu |
| 👤 Patient | `pacient@medilink.com` | Alin Mincu |
| 👤 Patient | `luminita.niculescu@yahoo.ro` | Luminița Niculescu |
| 👤 Patient | `andrei.marinescu@gmail.com` | Andrei Marinescu |

---

## Project Structure

```
MediLink/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── api/routes/       # REST & WebSocket Endpoints
│   │   ├── models/           # SQLAlchemy Models
│   │   ├── schemas/          # Pydantic Schemas
│   │   ├── services/         # Business Logic (AI, email, etc.)
│   │   └── middleware/       # JWT Auth, RBAC
│   ├── alembic/              # DB Migrations
│   └── tests/                # Pytest Suite
├── frontend/                 # Angular 19
│   └── src/app/
│       ├── pages/            # Views (dashboard, records, vitals, etc.)
│       ├── services/         # API & Auth Services
│       └── layouts/          # Sidebar, Header components
├── nginx/
│   └── nginx.conf            # Reverse proxy + rate limiting
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Security

- **Authentication:** JWT with refresh tokens (15 min / 7 days)
- **2FA:** Optional TOTP (Google Authenticator)
- **Sensitive Data:** Encrypted using Fernet (AES-128-CBC)
- **Rate Limiting:** Nginx — 5 req/min login, 60 req/min API
- **RBAC:** Role-based access control middleware (patient / doctor / assistant / admin)
- **GDPR:** Complete user data export available upon request
---

## Local Development (without Docker)
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (alt terminal)
cd frontend
npm install
ng serve --port 4200
```

---

## Environment Variables

See [`.env.example`](.env.example) for the complete list and generation instructions.

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection URL | ✅ |
| `SECRET_KEY` | JWT Secret (min 32 random chars) | ✅ |
| `ENCRYPTION_KEY` | Fernet key for sensitive data | ✅ |
| `GROQ_API_KEY` | Groq API key (AI chat + risk prediction) | ✅ |
| `REDIS_URL` | Redis connection URL | ✅ |
| `SMTP_*` | Email notification configurations | ❌ optional |
