# Spell Practice Backend

Run `main.py` with uvicorn to start the API.

## AI Features (Google Gemini)

### 1. Extract Spelling Words from a Picture
- Upload or provide a picture (worksheet, textbook page, handwritten note, etc).
- The system uses Google Gemini vision to:
  - Perform OCR to extract text from the image.
  - Identify and extract a list of spelling words from the recognized text.
- Returns the list of words to the user for review or further use.

### 2. Generate a Story from a List of Spelling Words
- User provides a list of spelling words.
- The system uses Google Gemini text generation to:
  - Compose a short, coherent story that meaningfully incorporates all the provided spelling words.
  - Ensure the story is age-appropriate and contextually relevant for spelling practice.
- Returns the generated story to the user.

### 3. Create a Puzzle from a List of Spelling Words
- User provides a list of spelling words.
- The system uses Google Gemini to:
  - Generate a word puzzle (e.g., word search, crossword clues, fill-in-the-blank sentences) using the provided words.
  - Ensure the puzzle is suitable for the user’s age group and spelling level.
- Returns the puzzle in a format that can be displayed or printed.

## fly.io deployment steps
1. install fly.io if needed: iwr https://fly.io/install.ps1 -useb | iex
2. flyctl auth signup   # or: fly auth login if haven't login
3. flyctl deploy --local-only #if docker is installed and running.
