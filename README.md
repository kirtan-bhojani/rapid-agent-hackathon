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

GEMINI_API_KEY=YOUR_API_KEY

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

GET /

GET /ask?q=your_query

GET /time

GET /add?a=5&b=7

GET /agent?q=your_query
