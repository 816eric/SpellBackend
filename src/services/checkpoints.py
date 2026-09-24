from typing import List, Set

# Checkpoints ("points" on the journey path) aim for this many words each.
CHECKPOINT_SIZE = 5

# A word counts as learned for mastery/stars once it has this many
# spaced-repetition successes (see Scheduler.update_sm2 - repetitions only
# advance on a due review, so this takes real days, not one sitting).
MASTERY_REPS = 3

# checkpoint_index stored in CheckpointProgress for a lesson's review node
# (the node after its last checkpoint), which isn't tied to any word chunk.
REVIEW_CHECKPOINT_INDEX = -1


def chunk_word_ids(word_ids: List[int], chunk_size: int = CHECKPOINT_SIZE) -> List[List[int]]:
    """Splits word ids (already sorted by the caller, typically ascending by
    id) into balanced checkpoints of about `chunk_size` words, in order.
    The count is the nearest whole number of chunk_size-sized groups (at
    least one), and words are spread evenly across them, so there is never a
    tiny tail: 18 words become 5, 5, 4, 4 (not 5, 5, 5, 3) and 21 become
    6, 5, 5, 5 (not a trailing single word). Returns [] for empty input."""
    total = len(word_ids)
    if total == 0:
        return []
    count = max(1, int(total / chunk_size + 0.5))
    base, extra = divmod(total, count)
    chunks: List[List[int]] = []
    start = 0
    for i in range(count):
        size = base + (1 if i < extra else 0)
        chunks.append(word_ids[start:start + size])
        start += size
    return chunks


def passed_checkpoint_indices(chunks: List[List[int]], recorded: Set[int]) -> Set[int]:
    """Indices of checkpoints the user has passed. A checkpoint is passed
    once a study session on it was completed (`recorded`, from
    CheckpointProgress) - it stays passed even if a later review misses a
    word.

    Deliberately does NOT also pass a checkpoint just because every word in
    it happens to already be mastered (e.g. via overlap with another
    lesson's words) - lessons in this app commonly reuse the same words, so
    that shortcut was silently marking checkpoints/reviews passed without
    the user ever doing a session for *that* lesson."""
    return {i for i in range(len(chunks)) if i in recorded}


def current_checkpoint_index(chunk_count: int, passed: Set[int]) -> int:
    """The user's current checkpoint = the first one not yet passed. If all
    are passed, or there are none, returns the last valid index (0 when
    there are no checkpoints)."""
    for i in range(chunk_count):
        if i not in passed:
            return i
    return max(chunk_count - 1, 0)
