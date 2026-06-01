from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tools.time_tool import get_time
from tools.calculator_tool import add

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

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

@app.get("/")
def home():
    return {"message": "Backend is running"}

@app.get("/ask")
def ask(q: str):

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=q
    )

    return {
        "answer": response.text
    }
@app.get("/time")
def time():

    return {
        "time": get_time()
    }
@app.get("/add")
def add_numbers(a: int, b: int):

    return {
        "result": add(a, b)
    }