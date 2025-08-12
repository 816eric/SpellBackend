# 🏆 Leaderboard — Requirements (v2)

This document defines the Leaderboard feature for the Spell app.

---

## 🎯 Objectives
- Show the **top 20 users** ranked by **highest total points**.
- Highest scores appear **at the top**.
- Support filters by **school** and/or **grade**.
- If a user is **logged in** and their profile contains **school** or **grade**, auto-apply those filters by default (user can clear them).

---

## 📊 Ranking Rules

1. **Primary sort**: `total_points` (descending).
2. **Tie-breakers** (in order):
   - `last_point_earned_at` (most recent activity ranks higher).
   - `name` (ascending, case-insensitive).
3. **Limit**: return **max 20** records.
4. **Visibility**:
   - Default scope is **global** (no filters).
   - When filters are applied, rank within the **subset**.

---

## 🔐 Privacy & Safety
- Display only: **name**, **total_points**, and optional **school/grade** if user consents.
- Do **not** show email/phone.
- (Optional) Allow users to opt-out or show **alias** instead of real name.

---

## 🗃️ Data Model

### `User` (existing)
- `name: str` (PK)
- `total_points: int`
- `school?: str`  ← used for filtering
- `grade?: str`   ← used for filtering
- `last_point_earned_at?: datetime` (recommended; update whenever points change)

No new tables required for v2.

---

## 🔌 API Endpoints

### `GET /leaderboard/top`
**Query params**
- `limit` (default: 20, max: 50)
- `school` (optional; exact match, case-insensitive)
- `grade` (optional; exact match, case-insensitive)

**Auto-apply filter (server-side helpful default):**
- If the **caller is authenticated** and:
  - `school` not provided → use caller’s `school` if not empty
  - `grade` not provided → use caller’s `grade` if not empty
- Client can override by sending `school=` or `grade=` as **empty** to force global.

**Response**
```json
{
  "scope": {
    "school": "ABC Primary",
    "grade": "P3"
  },
  "count": 20,
  "items": [
    {
      "rank": 1,
      "name": "Alice",
      "total_points": 245,
      "school": "ABC Primary",
      "grade": "P3"
    }
  ]
}
```

### `GET /leaderboard/me` (optional)
Returns the current user’s **rank snapshot** within the **same filter context**.
- Accepts the same `school`/`grade` query params and **applies auto-defaults** as above.

---

## ⚙️ Backend Logic

- Base query:
  ```sql
  SELECT name, total_points, school, grade, last_point_earned_at
  FROM user
  WHERE (:school IS NULL OR LOWER(school) = LOWER(:school))
    AND (:grade  IS NULL OR LOWER(grade)  = LOWER(:grade))
  ORDER BY total_points DESC, last_point_earned_at DESC, name COLLATE NOCASE ASC
  LIMIT :limit;
  ```
- **Auto-defaults**:
  - If request has an authenticated user and the query param is missing/empty, read from their profile and fill it in server-side.
- **Caching** (optional):
  - Cache key should include: `limit|school|grade`.
  - TTL: 60s; invalidate on reward point updates if needed.

---

## 🖥️ Flutter UI

- **Filter controls**:
  - Two dropdowns or text fields at top: **School**, **Grade**.
  - On page load:
    - If user is logged in and has school/grade in profile, **pre-fill** and auto-query.
    - Allow clearing one/both filters to view global.
  - Refresh button / pull-to-refresh.
- **List**:
  - Up to 20 rows with: rank, name, points, optional school/grade.
  - Medal icons for top 3: 🥇🥈🥉
  - Highlight current user if present in the list.
- **State**:
  - Show active filter chips (e.g., `School: ABC Primary`, `Grade: P3`) with clear (✕).
  - Empty state if no users match.
- **Accessibility**:
  - Large tap targets, proper contrast, and semantics.

---

## 🧪 Testing

- Seed users with assorted schools/grades.
- Verify:
  - Sorting and tie-breakers.
  - Auto-fill behavior for logged-in user profile.
  - Clearing filters → global leaderboard.
  - Case-insensitive matches for filters.
  - Limit truncation at 20.

---

## 📝 Acceptance Criteria

- Endpoint returns top **≤20** users ordered by `total_points` with tie-breakers.
- Filters by `school`/`grade` work (case-insensitive).
- If the user is logged in and has school/grade, the API **auto-applies** them when not provided.
- Flutter UI pre-fills filters from profile, allows clearing, and shows correct results.
- No private data (email/phone) is exposed.
