import math
from typing import List, Optional, Tuple, Dict
from datetime import date
from sqlmodel import select, Session
from src.models.word import SpellingWord
from src.models.link import WordTagLink
from src.services.word_manager import WordManager
from src.services.user_manager import UserManager
from src.models.review_state import ReviewState
from src.services.scheduler import Scheduler
from src.services.checkpoints import chunk_word_ids

class DeckBuilder:
    def __init__(self, session: Session):
        self.session = session



    @staticmethod
    def _card(w: SpellingWord, st: Optional[ReviewState], today, review: bool = False) -> Dict:
        if st is None:
            state = {
                "repetitions": 0,
                "interval_days": 0,
                "ease_factor": 2.5,
                "due_date": today.isoformat(),
                "status": "new",
            }
        else:
            state = {
                "repetitions": st.repetitions,
                "interval_days": st.interval_days,
                "ease_factor": st.ease_factor,
                "due_date": (st.due_date or today).isoformat(),
            }
        if review:
            # A word pulled in from outside the session's own words purely
            # as spaced review (see _due_review_words).
            state["review"] = True
        return {
            "word_id": w.id,
            "text": w.text,
            "language": w.language,
            "back_card": w.back_card,
            "quiz": w.quiz,
            "state": state,
        }

    def _due_review_words(self, user_name: str, candidates: List[SpellingWord], exclude_ids: set, today, n: int):
        """Up to `n` words from `candidates` that the user has studied and
        that are due for spaced review (missed-most first), skipping
        `exclude_ids`."""
        if n <= 0:
            return []
        by_id = {w.id: w for w in candidates if w.id not in exclude_ids}
        if not by_id:
            return []
        states = self.session.exec(
            select(ReviewState).where(
                (ReviewState.user_name == user_name) & (ReviewState.word_id.in_(list(by_id)))
            )
        ).all()
        due = [(by_id[st.word_id], st) for st in states if (st.due_date or today) <= today]
        due.sort(key=lambda item: (-item[1].fail_count, item[1].due_date or date.min, item[1].ease_factor, item[0].id))
        return due[:n]

    def _due_words_elsewhere(self, user_name: str, exclude_ids: set, today, n: int, language: Optional[str] = None):
        """Like _due_review_words, but over every word the user has studied
        (i.e. from earlier lessons), not a given candidate list. `language`
        limits it to words of that language, so an English word never turns
        up in a Chinese session or vice versa."""
        if n <= 0:
            return []
        states = self.session.exec(
            select(ReviewState).where(
                (ReviewState.user_name == user_name)
                & (ReviewState.due_date <= today)
            )
        ).all()
        states = [st for st in states if st.word_id not in exclude_ids]
        states.sort(key=lambda st: (-st.fail_count, st.due_date or date.min, st.ease_factor, st.word_id))
        out = []
        for st in states:
            if len(out) >= n:
                break
            w = self.session.get(SpellingWord, st.word_id)
            if w and (language is None or w.language == language):
                out.append((w, st))
        return out

    def build_daily_deck(self, user_name: str, limit: int = 10, tag: str = None, checkpoint: int = None, mode: str = None) -> Tuple[List[Dict], str]:
        """
        Returns (cards, empty_reason) where empty_reason in {'', 'no_tags', 'no_words'}

        `tag` may be a single tag or a comma-separated list of tags (used to
        scope a deck to a lesson that spans multiple tag variants, e.g. a
        Chinese lesson's ::read and ::write tags combined).

        `checkpoint` is a 0-based index that further scopes the tag's word
        pool to a single fixed-size chunk (see checkpoints.chunk_word_ids).
        It is a no-op if `tag` is None. An out-of-range value (negative or
        >= the number of chunks) clamps to the nearest valid chunk rather
        than raising or falling back to the entire unscoped pool.

        A checkpoint session is a mixed one: the checkpoint's own words plus
        a few spaced-review words that are due - mostly from the lesson's
        other checkpoints, one from earlier lessons - flagged
        `state.review = True`.

        `mode="review"` (with `tag`) builds a lesson review session: the
        whole lesson's words, weakest first (up to `limit`, less a few slots
        for due words from other lessons).
        """
        today = Scheduler.today_sg()

        user_manager = UserManager(self.session)
        user = user_manager.get_user(user_name)
        if not user:
            return ([], "no_tags")
        word_manager = WordManager(self.session)
        if tag is None:
            words = word_manager.get_all_words_for_user(user.id)
        else:
            tags = [t.strip() for t in tag.split(",") if t.strip()]
            words = word_manager.get_words_by_user_and_tags(user.id, tags)
        print(f"Found {len(words)} words for user {user_name} with tag: {tag}")
        if not words:
            return ([], "no_words")

        lesson_words = list(words)
        if mode == "review" and tag is not None:
            return (self._build_review_deck(user_name, lesson_words, limit, today), "")

        checkpoint_scoped = checkpoint is not None and tag is not None
        if checkpoint_scoped:
            sorted_ids = sorted(w.id for w in words)
            chunks = chunk_word_ids(sorted_ids)
            clamped = max(0, min(checkpoint, len(chunks) - 1))
            allowed_ids = set(chunks[clamped])
            words = [w for w in words if w.id in allowed_ids]

        pool_word_ids = [w.id for w in words]
        states = self.session.exec(
            select(ReviewState).where(
                (ReviewState.user_name == user_name) & (ReviewState.word_id.in_(pool_word_ids))
            )
        ).all()
        print(f"Found {len(states)} review states for user {user_name}")
        state_by_word = {s.word_id: s for s in states}

        overdue = []
        new_words = []
        not_due_yet = []
        for w in words:
            st = state_by_word.get(w.id)
            if st:
                due = st.due_date or today
                if due <= today:
                    overdue.append((w, st))
                elif tag is not None:
                    # A lesson-scoped request (the user explicitly picked
                    # this lesson) should still return its words even if
                    # SM-2 scheduled them for a later date - the generic,
                    # no-tag "daily deck" queue is the only place due-date
                    # gating should actually withhold words.
                    not_due_yet.append((w, st))
            else:
                new_words.append((w, None))

        overdue.sort(key=lambda item: (-item[1].fail_count, (item[1].due_date or today), item[1].ease_factor, item[0].id))
        not_due_yet.sort(key=lambda item: (-item[1].fail_count, (item[1].due_date or today), item[1].ease_factor, item[0].id))

        cards: List[Dict] = [self._card(w, st, today) for w, st in overdue[:limit]]

        if len(cards) < limit:
            cards.extend(
                self._card(w, None, today) for w, _ in new_words[: limit - len(cards)]
            )

        if len(cards) < limit:
            cards.extend(
                self._card(w, st, today) for w, st in not_due_yet[: limit - len(cards)]
            )

        if checkpoint_scoped:
            extra_cap = min(max(0, limit - len(cards)), math.ceil(len(words) / 2))
            in_lesson_ids = {w.id for w in lesson_words}
            own_ids = {w.id for w in words}
            # One slot goes to a due word from an earlier lesson; whatever
            # it can't fill (none due) falls back to this lesson's other
            # checkpoints, which take all the remaining slots.
            elsewhere = self._due_words_elsewhere(
                user_name, in_lesson_ids, today, min(1, extra_cap),
                language=words[0].language,
            )
            same_lesson = self._due_review_words(
                user_name, lesson_words, own_ids, today, extra_cap - len(elsewhere)
            )
            for w, st in same_lesson + elsewhere:
                cards.append(self._card(w, st, today, review=True))

        return (cards, "")

    def _build_review_deck(self, user_name: str, lesson_words: List[SpellingWord], limit: int, today) -> List[Dict]:
        elsewhere_cap = limit // 5
        own_cap = limit - elsewhere_cap
        states = self.session.exec(
            select(ReviewState).where(
                (ReviewState.user_name == user_name)
                & (ReviewState.word_id.in_([w.id for w in lesson_words]))
            )
        ).all()
        state_by_word = {st.word_id: st for st in states}
        # Weakest first: most misses, then fewest successful repetitions
        # (a word never studied counts as 0 and sorts with the weakest),
        # then the soonest due.
        ranked = sorted(
            lesson_words,
            key=lambda w: (
                -(state_by_word[w.id].fail_count if w.id in state_by_word else 0),
                state_by_word[w.id].repetitions if w.id in state_by_word else 0,
                (state_by_word[w.id].due_date or date.min) if w.id in state_by_word else date.min,
                w.id,
            ),
        )
        chosen = ranked[:own_cap]
        cards = [self._card(w, state_by_word.get(w.id), today) for w in chosen]
        elsewhere = self._due_words_elsewhere(
            user_name, {w.id for w in lesson_words}, today, elsewhere_cap,
            language=lesson_words[0].language if lesson_words else None,
        )
        cards.extend(self._card(w, st, today, review=True) for w, st in elsewhere)
        return cards
