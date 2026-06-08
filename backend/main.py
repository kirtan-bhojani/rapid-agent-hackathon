from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tools.time_tool import get_time
from tools.calculator_tool import add
from agent.agent import run_agent
from agent.orchestrator import handle_request
from tools.search_tool import (
    search_scholarships,
    search_universities,
    search_jobs,
    search_internships,
)
from routes.upload import router as upload_router  # ← NEW
from routes.extract import router as extract_router  # ← NEW
from routes.profile import router as profile_router  # ← NEW
from routes.auth import router as auth_router

from google import genai
from dotenv import load_dotenv

import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload_router)  # ← NEW  →  POST /upload/
app.include_router(extract_router)  # POST /extract/   ← NEW
app.include_router(profile_router)  # POST /profile/build   GET /profile/{user_id}   ← NEW
app.include_router(auth_router)

# ── Gemini client ─────────────────────────────────────────────────────────────
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# ── Existing routes ───────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.get("/ask")
def ask(q: str):
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=q,
    )
    return {"answer": response.text}


@app.get("/time")
def time():
    return {"time": get_time()}


@app.get("/add")
def add_numbers(a: int, b: int):
    return {"result": add(a, b)}


@app.get("/agent")
async def agent(q: str):
    return await handle_request(q)


@app.get("/scholarships")
def scholarships(q: str):
    return search_scholarships(q)