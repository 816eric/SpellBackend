# 🧠 Spell Practice Backend Specification

## 🏗️ Tech Stack

- **Backend Framework**: FastAPI
- **Database**: SQLite (file-based)
- **Language**: Python 3.x
- **Design Style**: Object-Oriented Programming (OOP)
- **Frontend**: Flutter or FlutterFlow (using REST API)
- **API Style**: RESTful
- **Deployment**: Local PC or cloud server

---

## 🗂️ System Overview

This backend supports a spell learning app that:

- Works for multiple users (with name-based identification, no login)
- Stores both global (admin-uploaded) and personal spelling words
- Tracks study activity and history
- Provides a points-based reward system
- Uses tag-based filtering (compatible with Anki format)
- Supports multilingual content (e.g., Chinese, English)

---

## 🧩 Object-Oriented Components

| Class          | Responsibility                                        |
| -------------- | ----------------------------------------------------- |
| `UserManager`  | Handles user registration, profile, login, and reward |
| `WordManager`  | Handles CRUD for spelling words                       |
| `StudyTracker` | Tracks study activity and timestamps                  |
| `TagManager`   | Manages tags and tag assignment                       |
| `RewardSystem` | Calculates and logs points and redemptions            |

---

## 🗃️ Data Models


### 1. User

| Field         | Type    | Required | Description               |
| ------------- | ------- | -------- | ------------------------- |
| id            | int     | ✅        | Primary key, auto-increment|
| name          | string  | ✅        | Unique user identifier    |
| age           | integer | ❌        | User age                  |
| email         | string  | ❌        | Email address             |
| phone         | string  | ❌        | Contact number            |
| school        | string  | ❌        | School name               |
| grade         | string  | ❌        | Grade (e.g., "Primary 1") |
| total\_points | int     | ✅        | Total reward points       |

---


### 2. SpellingWord

| Field        | Type   | Required | Description                         |
| ------------ | ------ | -------- | ----------------------------------- |
| id           | int    | ✅        | Primary key                         |
| text         | string | ✅        | Word or sentence                    |
| language     | string | ❌        | "en", "zh", "other"                 |
| created\_by  | string | ❌        | "admin" or user name                |

---


### 3. Tag

| Field        | Type   | Required | Description                         |
| ------------ | ------ | -------- | ----------------------------------- |
| id           | int    | ✅        | Primary key                         |
| tag          | string | ✅        | Tag name (arbitrary, Anki-compatible)|
| created_by   | int or "admin" | ✅ | Owner (user id or "admin")          |
| description  | string | ❌        | Tag description                     |

Examples:
  - `school::ABCPrimary`
  - `grade::Primary1`
  - `term::Term2`

### 4. UserTagsLink

| Field    | Type | Required | Description                |
|----------|------|----------|----------------------------|
| id       | int  | ✅        | Primary key                |
| user_id  | int  | ✅        | Foreign key to User        |
| tag_id   | int  | ✅        | Foreign key to Tag         |

### 5. WordTagLink

| Field    | Type | Required | Description                |
|----------|------|----------|----------------------------|
| id       | int  | ✅        | Primary key                |
| word_id  | int  | ✅        | Foreign key to SpellingWord|
| tag_id   | int  | ✅        | Foreign key to Tag         |

---

### 4. StudyHistory

| Field             | Type     | Description                 |
| ----------------- | -------- | --------------------------- |
| user\_name        | string   | User who studied            |
| word\_id          | int      | Foreign key to SpellingWord |
| count             | int      | Times the word was studied  |
| last\_studied\_at | datetime | Latest timestamp            |
| history           | list     | Optional list of timestamps |

---

### 5. LoginHistory

| Field      | Type     | Description |
| ---------- | -------- | ----------- |
| user\_name | string   | User name   |
| timestamp  | datetime | Login time  |

---

### 6. RewardHistory

| Field      | Type     | Description                |
| ---------- | -------- | -------------------------- |
| user\_name | string   | Who earned/redeemed points |
| action     | enum     | "earn" or "redeem"         |
| points     | int      | Points involved            |
| reason     | string   | Description or tag         |
| timestamp  | datetime | When action occurred       |

---

## 🔌 API Endpoints (REST)

### 👤 User Endpoints

- `POST /users/` → Create user
- `GET /users/{name}` → Get profile
- `POST /users/{name}/login` → Log login
- `GET /users/{name}/points/` → View points + history
- `POST /users/{name}/points/redeem` → Redeem points

---

### 📚 Word Endpoints

- `POST /words/` → Admin creates a global word
- `POST /users/{name}/words/` → User creates personal word
- `GET /users/{name}/words/?tags=tag1,tag2` → Get words (merged global + personal) by tag

---

### 🧠 Study Endpoints

- `POST /users/{name}/study/` → Log study event (increments count, gives point)
- `GET /users/{name}/history/` → View per-word history

---

### 🏷️ Tag Endpoints

- `GET /tags/` → List predefined tag templates
- `GET /users/{name}/tags/` → User-specific tags

---


## 📋 Business Logic Summary

- Users are identified by **name** (plus auto-incremented id)
- No password or auth system required
- Words can be **admin or user-owned**, text only
- **Tags are managed via Tag, UserTagsLink, and WordTagLink tables**
- When adding a word:
  - Add to SpellingWord if not exist
  - Add tag to Tag if not exist
  - Add UserTagsLink if user does not have tag
  - Add WordTagLink if word-tag link does not exist
  - If word exists, still add tag, UserTagsLink, and WordTagLink if not exist
- When deleting a word (admin only):
  - Remove from SpellingWord and WordTagLink
  - If tag is no longer linked to any word, remove from Tag and UserTagsLink
- Tag assignment:
  - User can assign existing tags to self (creates UserTagsLink)
- Tag unassignment:
  - User can unassign tags (removes UserTagsLink)
- Tag deletion:
  - Only owner can delete
  - If other users still use tag, change owner to "admin"
  - If no other users, remove tag from Tag and WordTagLink
- Tag editing:
  - Only owner can edit tag info
- **Each study earns 1 point**
- **Points can be redeemed** and deducted
- All actions are logged for transparency
- Words are filtered via **tag system**

---

## 🔮 Future Enhancements (Optional)

- Add audio for spelling words
- Add TTS or translation service
- Add leaderboard or classroom-based comparison
- Add spaced repetition logic

---

## 🗂️ Project Folder Structure

```
spell_backend/
├── main.py                            # Entry point for FastAPI app
├── config/
│   └── settings.py                    # App-wide settings (e.g., DB path)
├── database/
│   ├── db.sqlite3                     # SQLite database file (runtime)
│   └── init_db.py                     # DB creation logic (if needed)
├── src/
│   ├── models/                        # Pydantic and SQLModel classes
│   │   ├── user.py
│   │   ├── word.py
│   │   ├── tag.py
│   │   ├── history.py
│   │   └── reward.py
│   ├── services/                      # Business logic (object-oriented)
│   │   ├── user_manager.py
│   │   ├── word_manager.py
│   │   ├── study_tracker.py
│   │   ├── tag_manager.py
│   │   └── reward_system.py
│   ├── routes/                        # API route definitions
│   │   ├── users.py
│   │   ├── words.py
│   │   ├── study.py
│   │   ├── rewards.py
│   │   └── tags.py
│   └── db_session.py                 # SQLModel session manager
├── requirements.txt                  # Dependency list
└── README.md                         # Project documentation
```

