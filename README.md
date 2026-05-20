# 🏥 MediLink — o platformă medicală digitală

> Lucrare de licență · Facultatea de Informatică · 2026

MediLink este o platformă medicală completă care conectează pacienți, doctori și asistenți medicali într-un sistem unificat, securizat și conform cu GDPR.

---

## Stack tehnologic

| Layer | Tehnologie |
|---|---|
| **Backend** | FastAPI (Python 3.11), SQLAlchemy, PostgreSQL, Redis |
| **Frontend** | Angular 19, Angular Material (M3), Tailwind CSS |
| **AI** | Groq API (Llama 3.3 70B) — chat medical & predicție risc |
| **Real-time** | WebSockets (notificări, mesaje, video) |
| **Video** | WebRTC (teleconsultații peer-to-peer) |
| **Infra** | Docker Compose, Nginx (reverse proxy + rate limiting) |

---

## Funcționalități principale

### 👤 Pacient
- Dashboard cu statistici personale și programări viitoare
- Fișă medicală electronică (consultații, analize, tratamente, rețete, investigații)
- Semne vitale cu grafice de evoluție și alerte automate
- Chat medical AI (Groq / Llama 3.3)
- Programări online cu confirmare
- Mesagerie în timp real cu doctori, asistenți și alți pacienți
- Export GDPR complet (HTML + JSON)
- Teleconsultații video (WebRTC)

### 🩺 Doctor
- Dashboard cu pacienții atribuiți și programările zilei
- Fișe medicale complete pentru fiecare pacient (cu paginare)
- Predicție risc AI per pacient (scor 1–10 cu recomandări)
- Raport medical AI generat automat (PDF)
- Statistici și semne vitale pentru toți pacienții
- Recenzii pacienți cu analiză sentiment AI

### 🗂️ Asistent medical
- Gestionare programări și atribuire pacienți la doctori
- Adăugare semne vitale pentru pacienți
- Acces la statistici și vitale pacienți

### 🔧 Admin
- Dashboard cu statistici platformă și grafice
- Gestionare utilizatori (activare/dezactivare, roluri)
- Vizualizare toate programările

---

## Pornire rapidă (Docker)

### Cerințe
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalat și pornit
- [Git](https://git-scm.com/)

### Pași

```bash
# 1. Clonează repo-ul
git clone https://github.com/vladr2/MediLink.git
cd MediLink

# 2. Configurează variabilele de mediu
cp .env.example .env
# Editează .env și completează GROQ_API_KEY (obții gratuit la console.groq.com)

# 3. Pornește întreaga aplicație
docker compose up --build

# 4. Aplică migrațiile bazei de date (prima rulare)
docker compose exec backend alembic upgrade head

# 5. (Opțional) Populează cu date demo realiste
docker compose exec backend python seed_data.py
```

Aplicația va fi disponibilă la:
- **Frontend:** http://localhost (via Nginx) sau http://localhost:4200 (direct)
- **API Docs (Swagger):** http://localhost:8000/api/docs
- **API Docs (via Nginx):** http://localhost/api/docs
- **Backend direct:** http://localhost:8000/api

---

## Conturi demo

> Toate conturile demo folosesc parola: **`Parola123!`**

| Rol | Email | Nume |
|---|---|---|
| 🔧 Admin | `admin@medilink.com` | Alexia Radoi |
| 🩺 Doctor | `doctor@medilink.com` | Mihai Constantin |
| 🩺 Doctor | `alexandru.ionescu@gmail.com` | Alexandru Ionescu |
| 🩺 Doctor | `maria.popescu@gmail.com` | Maria Popescu |
| 🗂️ Asistent | `asistent@medilink.com` | Daniela Vlad |
| 🗂️ Asistent | `asistent2@medilink.com` | Ana Florescu |
| 👤 Pacient | `pacient@medilink.com` | Alin Mincu |
| 👤 Pacient | `luminita.niculescu@yahoo.ro` | Luminița Niculescu |
| 👤 Pacient | `andrei.marinescu@gmail.com` | Andrei Marinescu |

---

## Structura proiectului

```
MediLink/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── api/routes/       # Endpoint-uri REST + WebSocket
│   │   ├── models/           # Modele SQLAlchemy
│   │   ├── schemas/          # Scheme Pydantic
│   │   ├── services/         # Logică business (AI, email, etc.)
│   │   └── middleware/       # Auth JWT, RBAC
│   ├── alembic/              # Migrații DB
│   └── tests/                # Teste pytest
├── frontend/                 # Angular 19
│   └── src/app/
│       ├── pages/            # Pagini (dashboard, fișe, vitale, etc.)
│       ├── services/         # API service, Auth service
│       └── layouts/          # Sidebar, Header
├── nginx/
│   └── nginx.conf            # Reverse proxy + rate limiting
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Securitate

- **Autentificare:** JWT cu refresh tokens (15 min / 7 zile)
- **2FA:** TOTP (Google Authenticator) opțional
- **Date sensibile:** criptate cu Fernet (AES-128-CBC)
- **Rate limiting:** Nginx — 5 req/min login, 60 req/min API
- **RBAC:** middleware per rol (patient / doctor / assistant / admin)
- **GDPR:** export complet date utilizator la cerere

---

## Dezvoltare locală (fără Docker)

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

## Variabile de mediu

Vezi [`.env.example`](.env.example) pentru lista completă și instrucțiuni de generare.

| Variabilă | Descriere | Obligatorie |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL | ✅ |
| `SECRET_KEY` | Secret JWT (min 32 chars random) | ✅ |
| `ENCRYPTION_KEY` | Cheie Fernet pentru date sensibile | ✅ |
| `GROQ_API_KEY` | API key Groq (chat AI + risc) | ✅ |
| `REDIS_URL` | URL Redis | ✅ |
| `SMTP_*` | Config email notificări | ❌ opțional |
