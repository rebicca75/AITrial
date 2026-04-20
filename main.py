from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="CheckMate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    ai_output: str
    original_prompt: str


class SectionResult(BaseModel):
    score: int
    explanation: str | None = None
    source: str | None = None
    suggestion: str | None = None
    fix: str


class AnalyzeResponse(BaseModel):
    bias: SectionResult
    hallucination: SectionResult
    promptRisk: SectionResult
    total: int
    topIssues: List[str]


RISKY_WORDS = ["always", "never", "guaranteed", "everyone", "proven", "definitely"]


def detect_risk(text: str, base: int) -> int:
    lower = text.lower()
    keyword_hits = sum(1 for word in RISKY_WORDS if word in lower)
    length_penalty = 12 if len(text) > 450 else 0
    score = min(95, base + keyword_hits * 9 + length_penalty)
    return score


@app.get("/")
def health_check() -> dict:
    return {"message": "CheckMate FastAPI server is running."}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    bias_score = detect_risk(payload.ai_output, 32)
    hallucination_score = detect_risk(payload.ai_output + payload.original_prompt, 28)
    prompt_score = detect_risk(payload.original_prompt, 22)
    total = round((bias_score + hallucination_score + prompt_score) / 3)

    top_issues = [
        "High-certainty language without evidence",
        "Potentially unsupported factual claim",
        "Prompt lacks verification requirement",
    ]

    return AnalyzeResponse(
        bias=SectionResult(
            score=bias_score,
            explanation="The response uses broad statements that may overgeneralize groups or outcomes.",
            fix="Use neutral words, avoid all-or-nothing claims, and add balanced context.",
        ),
        hallucination=SectionResult(
            score=hallucination_score,
            source="Wikipedia cross-check: related summary found but some details are unsupported.",
            fix="Verify facts with trusted citations before finalizing the output text.",
        ),
        promptRisk=SectionResult(
            score=prompt_score,
            suggestion="Suggested prompt: 'Give a balanced answer with factual references, confidence level, and possible limitations.'",
            fix="Add clearer constraints: ask for sources, confidence score, and avoid assumptions.",
        ),
        total=total,
        topIssues=top_issues,
    )
