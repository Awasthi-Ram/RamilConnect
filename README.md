# RamilConnect 💖🤖

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

## 🏗️ Architecture

- **Backend:** Python 3.12+ / FastAPI (async)
- **Database:** PostgreSQL + pgvector (embeddings)
- **ORM:** SQLAlchemy 2.0 + Alembic (migrations)
- **AI:** Multi-provider (Google Gemini, OpenAI, Anthropic Claude)
- **Auth:** JWT (access + refresh tokens)
- **Admin:** FastAPI + Jinja2 + HTMX
- **Mobile:** Kivy/KivyMD (Android APK via Buildozer)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 15+ (with `pgvector` extension)
- At least one AI API key (Gemini, OpenAI, or Anthropic)

### Setup & Execution

```bash
# 1. Clone and enter the project
cd RamilConnect

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 4. Install dependencies
pip install -e ".[dev]"

# 5. Configure environment variables
copy .env.example .env
# Open .env and set your DATABASE_URL and API keys

# 6. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

*Note: In non-production mode, starting the server will automatically create your database tables and seed the initial admin account (`admin@ramilconnect.ai` / `admin123`).*

### Running Tests

We use `pytest` for integration testing. Because the application relies on `pgvector` for chat embeddings, a running PostgreSQL database is required for the full test suite.

```bash
# From the RamilConnect directory
pytest -v tests/
```

### API Documentation
Once running, visit: `http://localhost:8080/api/docs` (Swagger UI)

---

## 📂 Project Structure

```text
RamilConnect/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # Async SQLAlchemy engine
│   ├── models/                  # ORM models
│   ├── schemas/                 # Pydantic request/response
│   ├── routes/                  # API endpoints
│   ├── services/                # Business logic
│   │   ├── rac_engine.py        # 🧠 Retrieval-Augmented Context
│   │   ├── psychology_engine.py # 🔬 Deep psychology profiling
│   │   ├── user_summary_engine.py # 📝 Living profiles
│   │   ├── ai_provider.py       # Multi-provider AI
│   │   └── prompt_builder.py    # Companion persona prompts
│   ├── middleware/               # JWT auth
│   └── utils/                   # Security, embeddings
├── admin_dashboard/             # Admin web UI
├── mobile/                      # Android app (Kivy)
├── alembic/                     # DB migrations
├── tests/                       # Test suite
└── pyproject.toml               # Dependencies
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

*Made with ❤️ by RamilConnect — Meaningful AI-human connections.*
