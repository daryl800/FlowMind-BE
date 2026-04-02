from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from app.bazi.schemas import BaziRequest
from app.bazi.report import generate_full_report
from typing import Literal

app = FastAPI(title="FlowMind BE")

LLMType = Literal["openai", "qianwen", "hunyuan"]
LangType = Literal["cn", "en"]

# --- CORS (dev-safe) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/bazi")
def generate_bazi(req: BaziRequest):
    try:
        # 1️⃣ Parse datetime
        if req.time:
            dt = datetime.strptime(
                f"{req.date} {req.time}",
                "%Y-%m-%d %H:%M"
            )
        else:
            dt = datetime.strptime(req.date, "%Y-%m-%d")

        # 2️⃣ Generate full report (BaZi + LLM)
        report = generate_full_report(
            dt,
            gender=req.gender,
            location=req.location,
            year=req.year,
            lang=req.lang,
            llm=req.llm,
            personality_profile=req.personality_profile
        )

        # 3️⃣ Attach language flag (optional use downstream)
        report["_meta"] = {
            "lang": req.lang
        }

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
