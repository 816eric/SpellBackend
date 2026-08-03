from typing import Dict, List
from src.models.review_state import ReviewState

CHECKPOINT_SIZE = 5
MASTERY_REPS = 5


def chunk_word_ids(word_ids: List[int], chunk_size: int = CHECKPOINT_SIZE) -> List[List[int]]:
    """Splits word ids (already sorted by the caller, typically ascending by
    id) into fixed-size checkpoints, in order. The last chunk gets the
    remainder, so an 18-word lesson with chunk_size=5 becomes checkpoints of
    5, 5, 5, 3 words. Returns [] for an empty input."""
    return [word_ids[i:i + chunk_size] for i in range(0, len(word_ids), chunk_size)]


def current_checkpoint_index(
    chunks: List[List[int]],
    state_by_word: Dict[int, ReviewState],
    mastery_reps: int = MASTERY_REPS,
) -> int:
    """The user's current checkpoint = the first chunk containing any word
    below mastery_reps repetitions (a word with no ReviewState entry counts
    as 0 repetitions). If every chunk is fully mastered, or there are no
    chunks at all, returns the last valid index (0 when chunks is empty)."""
    for i, chunk in enumerate(chunks):
        if any(
            (state_by_word[wid].repetitions if wid in state_by_word else 0) < mastery_reps
            for wid in chunk
        ):
            return i
    return max(len(chunks) - 1, 0)
