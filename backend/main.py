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
from routes.mcp_test import router as mcp_test_router
from routes.career import router as career_router
from routes.opportunities import router as opportunities_router
from routes.application_prep import router as application_prep_router

from google import genai
from dotenv import load_dotenv

import os

load_dotenv()

from contextlib import asynccontextmanager
from services.mcp_service import MCPManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and start MCP Client
    print("Lifespan: Starting MCPManager...")
    mcp_manager = MCPManager()
    await mcp_manager.start()
    
    # Store in app state
    app.state.mcp_client = mcp_manager
    print("Lifespan: MCPManager started and injected into app.state.")
    
    yield # Serve traffic
    
    # Graceful Teardown
    print("Lifespan: Stopping MCPManager...")
    if hasattr(app.state, "mcp_client") and app.state.mcp_client:
        await app.state.mcp_client.stop()
    print("Lifespan: MCPManager stopped cleanly.")

app = FastAPI(lifespan=lifespan)

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
app.include_router(mcp_test_router)
app.include_router(career_router)
app.include_router(opportunities_router)
app.include_router(application_prep_router)

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