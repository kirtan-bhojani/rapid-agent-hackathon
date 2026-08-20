# rapid-agent-hackathon
# Project Setup

## Clone Repository

git clone <repo-url>

cd rapid-agent-hackathon

---

# Frontend Setup

## Navigate to Frontend

cd frontend

## Install Dependencies

npm install

## Run Frontend

npm run dev

Frontend will run at:

http://localhost:5173

---

# Backend Setup

## Navigate to Backend

cd ../backend

## Create Virtual Environment

python -m venv venv

## Activate Environment

### Windows

venv\Scripts\activate

### Mac/Linux

source venv/bin/activate

## Install Dependencies

pip install -r requirements.txt

## Create .env

OPENAI_API_KEYS=your_openai_key
GROQ_API_KEYS=your_groq_key
MONGO_URI=mongodb+srv://...

## Run Backend

uvicorn main:app --reload

Backend will run at:

http://127.0.0.1:8000

---

# Current Architecture

Frontend (React + Vite)
↓
Backend (FastAPI)
↓
Gemini API
↓
Tools / Agents

---

# Current Working Endpoints

- `GET /` - Health check
- `POST /upload/` - Upload documents
- `POST /extract/` - Extract information from uploaded documents
- `GET /profile/` & `POST /profile/` - User profile management
- `POST /auth/register` & `POST /auth/login` - User authentication
- `GET /career-plan/` & `POST /career-plan/` - Career plan generation and retrieval
- `GET /opportunities/{user_id}` - Fetch opportunities for the user
- `POST /goal-analysis/` & `GET /goal-analysis/{user_id}` - Goal analysis
- `GET /dashboard/{user_id}` - Dashboard data
- `/application-prep/*` - Application preparation routes
- `/mcp-test/*` - MCP testing endpoints
