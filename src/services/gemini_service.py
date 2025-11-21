
import os
from typing import List
from pathlib import Path
from fastapi import UploadFile
import google.generativeai as genai

# Placeholder for Google Gemini API integration
# In production, use the official Google Gemini SDK or REST API


class GeminiService:
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("Gemini_key")
        self.api_key = "AIzaSyAaXdGQdflEhPh1UcwxVGn1zc7woQtCn1Y"
        if not self.api_key:
            raise ValueError("Google Gemini API key not set.")
        genai.configure(api_key=self.api_key)
        self.model = model
        self.client = genai.GenerativeModel(model)
        self.vision_client = genai.GenerativeModel(model)

    def extract_words_from_image(self, image_file: UploadFile) -> List[str]:
        # Read image bytes from UploadFile
        image_bytes = image_file.file.read()
        # Gemini Vision expects a list of dicts with 'mime_type' and 'data'
        image_data = [{
            "mime_type": image_file.content_type or "image/png",
            "data": image_bytes
        }]

        prompt = (
            "Extract all spelling words or sentences from this image. "
            "Return only the list of words or sentences, separated by commas. "
            "If the image contains a worksheet or spelling list, extract only the spelling words."
        )
        try:
            response = self.vision_client.generate_content([
                {"text": prompt},
                *image_data
            ])
            # The response text should be a comma-separated list
            text = response.text.strip()
            # Split by comma and clean up whitespace
            words = [w.strip() for w in text.split(",") if w.strip()]
            print(f"Extracted words: {words}")
            return words
        except Exception as e:
            raise RuntimeError(f"Gemini Vision API error: {e}")

    def generate_story(self, words: List[str]) -> str:
        prompt = (
            "Write a short, funny story for kids using all of these spelling words: "
            f"{', '.join(words)}. "
            "Make sure the story is creative, age-appropriate, and each word is used at least once."
        )
        try:
            response = self.client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error (story): {e}")

    def create_puzzle(self, words: List[str]) -> dict:
        prompt = (
            "Create a fun and age-appropriate word puzzle for kids using all of these spelling words: "
            f"{', '.join(words)}. "
            "Choose a suitable format (word search, crossword clues, or fill-in-the-blank sentences). "
            "Return the puzzle as structured text, including instructions and the puzzle content."
        )
        try:
            response = self.client.generate_content(prompt)
            # Return the puzzle as a dict for frontend rendering
            return {
                "puzzle": response.text.strip(),
                "words": words
            }
        except Exception as e:
            raise RuntimeError(f"Gemini API error (puzzle): {e}")
