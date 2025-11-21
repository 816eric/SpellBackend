from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
from src.services.gemini_service import GeminiService

router = APIRouter(prefix="/ai", tags=["AI"])
gemini = GeminiService(model="gemini-2.0-flash-exp")

class WordsRequest(BaseModel):
    words: List[str]

@router.post("/extract-words", response_model=List[str])
def extract_words_from_image(file: UploadFile = File(...)):
    try:
        return gemini.extract_words_from_image(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-story")
def generate_story(req: WordsRequest):
    try:
        return {"story": gemini.generate_story(req.words)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-puzzle")
def create_puzzle(req: WordsRequest):
    try:
        return gemini.create_puzzle(req.words)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
