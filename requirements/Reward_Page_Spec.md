# 🎁 Reward Page — Requirements (v1)

This document specifies the Reward page behavior for the Spell app (frontend + backend expectations).

---

## 🧭 Page Goals
- Let users **redeem** points for custom items.
- Show the user's **redeem/earn history** in a paginated list.
- Respect authentication: **only logged-in users** can redeem or view history.

---

## 🔐 Authentication
- If the user is **not logged in**, the page displays:
  > **Please login first**
- All API calls on this page require a valid user context (e.g., JWT or current user name).
- If a request returns 401/403, show the same **Please login first** message and a **Login** button.

---

## 🧾 UI Layout

### 1) Redeem Section
- **Inputs**:
  - *Item name* (text, required)
  - *Points to redeem* (number, required, min=1)
- **Redeem button**:
  - On press, show a **confirmation dialog**:
    - Title: **Confirm Redeem**
    - Body: “Redeem **{points}** points for **{item}**?”
    - Actions: **Yes** / **Cancel**
  - On **Yes**:
    - Call backend to attempt the redemption.
    - If **insufficient points**, show toast/snackbar:
      - “Points are not sufficient.”
    - If **success**, show success message and refresh **Current Points** and **History**.

- **Current Points**:
  - Show current `total_points` at top of the section.
  - Refresh after each redemption.

### 2) Redeem History Section
- Title: **Redeem & Reward History**
- Table/list with columns:
  - **Timestamp**
  - **Action** (`earn` | `redeem`)
  - **Points** (positive for earn, negative for redeem)
  - **Reason/Item**
- **Pagination**:
  - 20 items per page (fixed).
  - Buttons/controls: **Previous** / **Next**.
  - Show current page indicator (e.g., “Page 2 of 5”).
- Empty state: “No history yet.”

---

## 🔌 Backend Contracts (Expected)

> Adjust paths to match your existing routes; these follow the current project conventions.

### Get Current Points
`GET /users/{name}/points/`
- **Response:**
```json
{
  "total_points": 120,
  "history_preview": [
    {"timestamp":"2025-08-16T10:10:00+08:00","action":"earn","points":1,"reason":"review"}
  ]
}
```

### Redeem Points
`POST /users/{name}/points/redeem`
- **Body:**
```json
{ "item": "Sticker Pack", "points": 30 }
```
- **Behavior:**
  - If user has **>= points**: deduct and append to `RewardHistory` as `{ action:"redeem", points: -30, reason: "Sticker Pack" }`.
  - Else: return 400 with `"detail":"insufficient_points"`.
- **Response (success):**
```json
{
  "ok": true,
  "total_points": 90
}
```

### Paged Reward History
`GET /users/{name}/points/history?page=1&size=20`
- **Defaults:** `page=1`, `size=20` (size fixed to 20 on server).
- **Response:**
```json
{
  "page": 1,
  "size": 20,
  "total": 86,
  "items": [
    {"timestamp":"2025-08-16T10:10:00+08:00","action":"earn","points":1,"reason":"review"},
    {"timestamp":"2025-08-15T22:11:00+08:00","action":"redeem","points":-30,"reason":"Sticker Pack"}
  ]
}
```

---

## 🧠 Validation Rules
- Item name: required, 2–64 characters.
- Points to redeem: integer, ≥ 1.
- On insufficient points, **do not** send partial success; return error and keep UI state.

---

## 🔄 UX Flows

**Redeem Flow:**
1. User enters item + points.
2. Click **Redeem** → Confirm dialog.
3. On **Yes**, call API.
4. If success: show toast “Redeemed {points} points for {item}”, update current points and refresh history (page 1).
5. If insufficient: show toast “Points are not sufficient.”

**History Pagination:**
- Click **Next** or **Previous** → fetch that page.
- Disable **Previous** on page 1; disable **Next** on the last page.

---

## 🧪 Testing
- Try redeem with sufficient points (deducts and appears in history).
- Try redeem with insufficient points (error shown, no deduction).
- Verify history lists newest first.
- Pagination works (exactly 20 per page).
- Unauthorized user sees **Please login first**.

---

## 🚀 Nice-to-haves (Future)
- Show **earn** summaries (e.g., daily/weekly totals).
- Add **filters**: action type, date range.
- Add **export** (CSV).
- Add **parent approval** mode (two-step confirm).
