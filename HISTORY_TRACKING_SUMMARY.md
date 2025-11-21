# History Tracking Feature Summary

## Overview
Implemented comprehensive study and quiz history tracking system to enable AI analysis and reporting of user learning patterns.

## Backend Implementation

### Database Models (SpellBackend/src/models/history.py)

#### StudySessionHistory
Tracks each study action with:
- `id`: Primary key
- `user_name`: Foreign key to user
- `word`: The word studied
- `difficulty`: Quality rating (0=Again, 1=Hard, 3=Good, 5=Easy)
- `studied_at`: Timestamp (auto-generated)

#### QuizSessionHistory
Tracks each quiz answer with:
- `id`: Primary key
- `user_name`: Foreign key to user
- `word`: The word quizzed
- `is_correct`: Boolean (True/False)
- `completed_at`: Timestamp (auto-generated)

### REST Endpoints (SpellBackend/src/routes/history.py)

#### POST /history/study-session
**Purpose**: Save a batch of study records when session completes or user changes tabs

**Request Body**:
```json
{
  "user_name": "string",
  "records": [
    {"word": "string", "difficulty": 0|1|3|5},
    ...
  ]
}
```

**Response**:
```json
{
  "success": true,
  "count": 2,
  "message": "Study session saved"
}
```

#### POST /history/quiz-session
**Purpose**: Save a batch of quiz records when quiz completes

**Request Body**:
```json
{
  "user_name": "string",
  "records": [
    {"word": "string", "is_correct": true|false},
    ...
  ]
}
```

**Response**:
```json
{
  "success": true,
  "count": 4,
  "accuracy": 75.0,
  "message": "Quiz session saved"
}
```

#### GET /history/study/{user_name}
**Purpose**: Retrieve study history for a user

**Query Parameters**:
- `limit` (optional, default 100): Maximum records to return

**Response**: Array of study records with timestamps

#### GET /history/quiz/{user_name}
**Purpose**: Retrieve quiz history for a user

**Query Parameters**:
- `limit` (optional, default 100): Maximum records to return

**Response**: Array of quiz records with timestamps

### Route Registration (SpellBackend/main.py)
Added history router to main application:
```python
from src.routes import history
app.include_router(history.router)
```

## Frontend Implementation

### API Service Methods (FlutterSpell/lib/services/spell_api_service.dart)

```dart
// Save study session (batch of records)
static Future<Map<String, dynamic>> saveStudySession(
  String userName, 
  List<Map<String, dynamic>> records
)

// Save quiz session (batch of records)
static Future<Map<String, dynamic>> saveQuizSession(
  String userName, 
  List<Map<String, dynamic>> records
)

// Get study history
static Future<List<dynamic>> getStudyHistory(
  String userName, 
  {int limit = 100}
)

// Get quiz history
static Future<List<dynamic>> getQuizHistory(
  String userName, 
  {int limit = 100}
)
```

### Study Page Tracking (FlutterSpell/lib/screens/study_page.dart)

**Implementation**:
1. Added `List<Map<String, dynamic>> _studyRecords = []` to track current session
2. On each `_rate(quality)` call:
   - Records: `{word: "...", difficulty: 0|1|3|5}`
3. Saves batch on:
   - Session completion (all cards done)
   - Tab change (didChangeDependencies detects user switch)
4. Clears records after successful save

**User Flow**:
1. User rates word → Record added to list
2. User completes all words OR switches tabs → Batch saved to backend
3. Records cleared, ready for next session

### Quiz Page Tracking (FlutterSpell/lib/screens/quiz_page.dart)

**Implementation**:
1. Added `List<Map<String, dynamic>> _quizRecords = []` to track current session
2. On each `_submitAnswer()` call:
   - Records: `{word: "...", is_correct: true|false}`
3. Saves batch on:
   - Quiz completion (`_showFinalScore()`)
4. Clears records after successful save

**User Flow**:
1. User answers question → Record added to list
2. User completes quiz → Batch saved to backend
3. Final score shown
4. Records cleared, ready for next quiz

## Data Flow

### Study Session
```
User rates word (0/1/3/5)
    ↓
Add to _studyRecords[]
    ↓
User completes deck OR changes tab
    ↓
POST /history/study-session with all records
    ↓
Backend inserts batch into studysessionhistory table
    ↓
Frontend clears _studyRecords[]
```

### Quiz Session
```
User submits answer (correct/incorrect)
    ↓
Add to _quizRecords[]
    ↓
User completes all questions
    ↓
POST /history/quiz-session with all records
    ↓
Backend inserts batch into quizsessionhistory table
    ↓
Backend returns accuracy statistics
    ↓
Frontend shows final score dialog
    ↓
Frontend clears _quizRecords[]
```

## Benefits

1. **AI Analysis Ready**: Structured data enables AI to:
   - Identify difficult words for each user
   - Track learning progress over time
   - Generate personalized recommendations
   - Analyze quiz performance patterns

2. **Batch Operations**: Efficient database writes
   - One API call per session instead of per word
   - Reduced network overhead
   - Better performance

3. **Complete Tracking**: Captures all user interactions
   - Study difficulty ratings (spaced repetition feedback)
   - Quiz correctness (knowledge assessment)
   - Timestamps for temporal analysis
   - Username for personalized insights

4. **Privacy Conscious**: Only saves on explicit actions
   - Study: Session completion or tab change
   - Quiz: Quiz completion
   - No background tracking

## Testing

Backend server confirms tables created:
- `studysessionhistory` ✓
- `quizsessionhistory` ✓

Endpoints registered and server starts successfully:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

## Future Enhancements

1. **Analytics Dashboard**:
   - View study patterns by word/date
   - Quiz accuracy trends
   - Difficulty distribution charts

2. **AI Insights**:
   - "You struggle with words containing 'ie'"
   - "Your accuracy improves in morning sessions"
   - "Focus on these 5 words for best progress"

3. **Export Features**:
   - CSV download of history
   - PDF progress reports
   - Share stats with teachers

## Implementation Date
November 21, 2025

## Files Modified
- SpellBackend/src/models/history.py
- SpellBackend/src/routes/history.py (new)
- SpellBackend/main.py
- FlutterSpell/lib/services/spell_api_service.dart
- FlutterSpell/lib/screens/study_page.dart
- FlutterSpell/lib/screens/quiz_page.dart
