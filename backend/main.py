from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import traceback
from fastapi.middleware.cors import CORSMiddleware

from routes.upload import router as upload_router
from routes.extract import router as extract_router
from routes.profile import router as profile_router
from routes.auth import router as auth_router
from routes.mcp_test import router as mcp_test_router
from routes.career import router as career_router
from routes.opportunities import router as opportunities_router
from routes.application_prep import router as application_prep_router
from routes.goal_analysis import router as goal_analysis_router
from routes.dashboard import router as dashboard_router

from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

from contextlib import asynccontextmanager
from services.mcp_service import MCPManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan: Starting MCPManager...")
    mcp_manager = MCPManager()
    await mcp_manager.start()
    app.state.mcp_client = mcp_manager
    print("Lifespan: MCPManager started and injected into app.state.")
    yield
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

logger = logging.getLogger("api")
logger.setLevel(logging.ERROR)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload_router)          # POST /upload/
app.include_router(extract_router)         # POST /extract/
app.include_router(profile_router)         # GET/POST /profile/
app.include_router(auth_router)            # POST /auth/register, /auth/login
app.include_router(mcp_test_router)
app.include_router(career_router)          # POST/GET /career-plan/
app.include_router(opportunities_router)   # GET /opportunities/{user_id}
app.include_router(application_prep_router)
app.include_router(goal_analysis_router)   # POST /goal-analysis/, GET /goal-analysis/{user_id}
app.include_router(dashboard_router)       # GET /dashboard/{user_id}

# ── Gemini client ─────────────────────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "RAPID Backend is running", "version": "2.0"}
