
import os
from typing import List
from pathlib import Path
from fastapi import UploadFile
import google.generativeai as genai

# Placeholder for Google Gemini API integration
# In production, use the official Google Gemini SDK or REST API


class GeminiService:
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash-exp"):
        # `Gemini_key` env var (e.g. a Fly secret) takes priority; the
        # literal below is only a last-resort fallback. It used to be
        # unconditionally overwritten right after this line, which meant
        # setting `Gemini_key` had no effect at all - fixed since that key
        # is now revoked (400 API_KEY_INVALID) and needs to be replaceable
        # without a code change.
        self.api_key = api_key or os.getenv("Gemini_key") or "AIzaSyAaXdGQdflEhPh1UcwxVGn1zc7woQtCn1Y"
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

    def explain_quiz_answer(
        self, word: str, question: str, options: List[str], correct_option: str
    ) -> str:
        """One short, kid-friendly sentence on why `correct_option` is right
        for this vocabulary quiz question - used by the Word Snake game's
        Knowledge Stone quiz to teach the reasoning, not just reveal the
        answer. Written in the same language as the question, since these
        quizzes are Chinese-language vocab questions as often as English."""
        prompt = (
            "You are a friendly elementary-school teacher. A student was asked "
            f"this vocabulary quiz question about the word '{word}':\n"
            f"Question: {question}\n"
            f"Options: {', '.join(options)}\n"
            f"Correct answer: {correct_option}\n\n"
            "In ONE short sentence (max 25 words), explain *why* this is the "
            "correct answer, in a way a child would understand. Respond in "
            "the same language as the question. Do not repeat the question "
            "or restate the options - just give the reason."
        )
        try:
            response = self.client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API error (quiz explanation): {e}")

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
