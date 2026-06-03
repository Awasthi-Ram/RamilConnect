# 💖 RamilConnect

**Your AI Soulmate Companion** — An AI-powered dating companion app that learns your personality through conversation, builds a deep psychological profile, and suggests compatible matches.

> **Domains:** [ramilconnect.ai](https://ramilconnect.ai) (App) | [ramilconnectadmin.ai](https://ramilconnectadmin.ai) (Admin)

---

## 🌟 What Makes RamilConnect Special

### 🧠 RAC Engine (Retrieval-Augmented Context)
Context is **never lost**. Unlike typical chatbots that only see the last 20 messages, RamilConnect uses a 4-layer context system:

| Layer | Source | Purpose |
|-------|--------|---------|
| **User Summary** | Living profile document | Who is this person? Always injected. |
| **Session Memory** | Last 15 messages | Immediate conversation flow |
| **Semantic Retrieval** | pgvector similarity search | Recall relevant past topics from ANY point in history |
| **Psychology Snapshot** | Personality profile + mood | Current emotional state & traits |

### 🔬 Deep Psychology Engine
Hybrid rule-based + AI personality profiling with Bayesian weighted merge:
- **Big Five** (OCEAN) personality traits
- **Attachment styles** (secure, anxious, avoidant, disorganized)
- **Love languages**, communication style, conflict response
- **Emotional regulation** and stress response patterns

### 📝 Living User Summaries
Auto-generated natural-language profiles capturing key facts, emotional patterns, important dates, relationship dynamics, and life goals.

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                    RamilConnect                          │
│                                                         │
│  ┌──────────────┐    HTTP/SSE     ┌──────────────────┐  │
│  │  📱 Mobile    │◄──────────────►│  🖥️  FastAPI      │  │
│  │  Kivy/KivyMD │                │  Backend Server   │  │
│  └──────────────┘                └────────┬──────────┘  │
│                                           │              │
│                              ┌────────────┼────────────┐│
│                              │            │            ││
│                              ▼            ▼            ▼│
│                        ┌──────────┐ ┌──────────┐ ┌─────┤│
│                        │🗄️ Postgres│ │ 🔴 Redis │ │ 🤖  ││
│                        │+ pgvector│ │  Cache   │ │ AI  ││
│                        └──────────┘ └──────────┘ │Provs││
│                                                  └─────┤│
│                                                        ││
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | FastAPI (Python 3.12+) | Async REST API + SSE streaming |
| **Database** | PostgreSQL + pgvector | Data storage + vector embeddings |
| **Cache** | Redis 7 | Session caching & rate limiting |
| **ORM** | SQLAlchemy 2.0 + Alembic | Async DB access + migrations |
| **AI Providers** | Gemini, OpenAI, Claude | Multi-provider AI with fallback |
| **Auth** | JWT (access + refresh) | Stateless authentication |
| **Admin Panel** | Jinja2 + HTMX | Server-rendered admin dashboard |
| **Mobile App** | Kivy + KivyMD | Cross-platform mobile UI |
| **APK Builder** | Buildozer | Compiles Python → Android APK |
| **Containerization** | Docker + Docker Compose | One-command deployment |
| **CI/CD** | GitHub Actions | Lint → Test → Build → Publish |

---

## 🔄 Chat Data Flow

This is what happens when a user sends a message:

```
📱 User sends message
        │
        ▼
┌─────────────────┐
│ POST /companion/ │
│     message      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Save user msg   │────►│  PostgreSQL DB    │
│ to database     │     └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ RAC Engine:     │────►│ pgvector search  │
│ Find relevant   │◄────│ (similarity)     │
│ past context    │     └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prompt Builder: │
│ personality +   │
│ context +       │
│ user summary +  │
│ message         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ AI Provider     │────►│ Gemini / OpenAI  │
│ (streaming)     │◄────│ / Claude         │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ SSE stream back │──────► 📱 Real-time
│ to mobile app   │         token display
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save AI response│
│ + update psych  │
│ profile         │
└─────────────────┘
```

---

## 📂 Project Structure

```text
RamilConnect/
├── app/                             # 🖥️ Backend Application
│   ├── main.py                      # FastAPI entry point + app factory
│   ├── config.py                    # Settings (pydantic-settings from .env)
│   ├── database.py                  # Async SQLAlchemy engine + sessions
│   ├── models/                      # ORM Models
│   │   ├── user.py                  #   User account + profile
│   │   ├── companion.py             #   AI companion config + messages
│   │   ├── personality.py           #   Big Five, attachment, love languages
│   │   ├── match.py                 #   Compatibility matching
│   │   ├── chat_embedding.py        #   pgvector embeddings for RAC
│   │   └── user_summary.py          #   Living profile documents
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── routes/                      # API Endpoints
│   │   ├── auth.py                  #   Register, login, token refresh
│   │   ├── companion.py             #   Chat (SSE), history, mood, stats
│   │   ├── user.py                  #   Profile, onboarding, personality
│   │   ├── admin.py                 #   Admin API (users, config, stats)
│   │   ├── admin_dashboard.py       #   HTML admin panel at /admin
│   │   └── health.py                #   Health check at /api/health
│   ├── services/                    # Business Logic
│   │   ├── ai_provider.py           #   🤖 Multi-provider AI abstraction
│   │   ├── prompt_builder.py        #   📝 Companion persona prompt builder
│   │   ├── psychology_engine.py     #   🔬 Deep personality profiling
│   │   ├── rac_engine.py            #   🧠 Retrieval-Augmented Context
│   │   └── user_summary_engine.py   #   📋 Auto user summary generation
│   ├── middleware/                   # JWT authentication middleware
│   └── utils/                       # Security helpers, embeddings
├── mobile/                          # 📱 Android Mobile App
│   ├── main.py                      # Kivy app entry point
│   ├── api.py                       # HTTP client for backend API
│   ├── kv_ui.py                     # UI layout (Login, Register, Chat, Profile)
│   ├── buildozer.spec               # Android APK build configuration
│   └── requirements.txt             # Mobile-specific dependencies
├── admin_dashboard/                 # 🎛️ Admin Web UI
│   └── templates/                   # Jinja2 HTML templates
├── alembic/                         # 🗄️ Database migrations
├── tests/                           # 🧪 Test Suite
│   ├── conftest.py                  # Test fixtures
│   ├── test_health.py               # Health endpoint tests
│   └── test_auth.py                 # Authentication tests
├── .github/workflows/               # ⚙️ CI/CD Pipelines
│   ├── ci.yml                       # Lint → Test → Build
│   └── cd.yml                       # Publish to GHCR + Releases
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Full stack: App + DB + Redis
├── pyproject.toml                   # Dependencies & tool config
└── .env.example                     # Environment variable template
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Awasthi-Ram/RamilConnect.git
cd RamilConnect

# 2. Configure environment
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY (or OPENAI_API_KEY)

# 3. Start everything
docker compose up -d

# 4. Verify
curl http://localhost:8080/api/health
# → {"status":"healthy"}
```

**Services started:**

| Service | URL | Description |
|---------|-----|-------------|
| **API Server** | http://localhost:8080 | FastAPI backend |
| **API Docs** | http://localhost:8080/api/docs | Swagger UI |
| **Admin Panel** | http://localhost:8080/admin | Admin dashboard |
| **PostgreSQL** | localhost:5432 | Database |
| **Redis** | localhost:6379 | Cache |

**Default admin login:** `admin@ramilconnect.ai` / `change-this-password`

### Option 2: Manual Setup

```bash
# 1. Enter project
cd RamilConnect

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env → set DATABASE_URL and API keys

# 5. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

> **Note:** In non-production mode, starting the server automatically creates database tables and seeds the admin account.

---

## 📱 Running the Mobile App

### On Desktop (for testing)

```bash
cd mobile
pip install kivy kivymd requests
python main.py
```

This opens a desktop window with the mobile UI. Make sure the backend is running first.

### Building the Android APK

```bash
# Install buildozer
pip install buildozer

# Install system dependencies (Ubuntu/Debian)
sudo apt install -y python3-pip build-essential git \
    openjdk-17-jdk autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev

# Build the APK (first build takes ~20-30 minutes)
cd mobile
buildozer android debug
```

The APK will be generated at: `mobile/bin/ramilconnect-1.0.0-*-debug.apk`

> ⚠️ **Important:** Before building the APK, update `mobile/api.py` to point to your server's IP address instead of `localhost`.

---

## 🧪 Running Tests

```bash
pytest -v tests/
```

Requires a running PostgreSQL database with pgvector extension.

---

## ⚙️ CI/CD Pipeline

The project uses GitHub Actions for automated CI/CD:

```
Push / PR to main
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  🔍 Lint     │────►│  🧪 Test     │────►│  🐳 Build    │
│  ruff check  │     │  pytest +    │     │  Docker img  │
│  ruff format │     │  Postgres +  │     │              │
│              │     │  Redis       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘

Push to main (CD)
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  📦 Publish  │────►│  🚀 Release  │
│  → GHCR      │     │  (on v* tag) │
└──────────────┘     └──────────────┘
```

---

## 🔑 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | ❌ | Register new user |
| POST | `/api/auth/login` | ❌ | Login |
| POST | `/api/auth/refresh` | ❌ | Refresh token |
| GET | `/api/user/profile` | ✅ | Get profile |
| PUT | `/api/user/profile` | ✅ | Update profile |
| POST | `/api/user/onboarding` | ✅ | Complete onboarding |
| GET | `/api/user/personality` | ✅ | Get personality |
| POST | `/api/companion/message` | ✅ | Chat (SSE stream) |
| GET | `/api/companion/history` | ✅ | Chat history |
| PUT | `/api/companion/persona` | ✅ | Switch persona |
| GET | `/api/companion/mood` | ✅ | Mood analysis |
| GET | `/api/companion/stats` | ✅ | Chat stats |
| GET | `/api/admin/stats` | 🔒 | Dashboard stats |
| GET | `/api/admin/users` | 🔒 | List users |
| GET | `/api/admin/config` | 🔒 | Get config |

---

## 📄 License

Made with ❤️ by RamilConnect — Meaningful AI-human connections.
