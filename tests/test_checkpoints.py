from src.models.review_state import ReviewState
from src.services.checkpoints import (
    chunk_word_ids,
    current_checkpoint_index,
    passed_checkpoint_indices,
)


def _sizes(n):
    return [len(c) for c in chunk_word_ids(list(range(n)))]


def test_chunk_word_ids_balances_words_across_checkpoints():
    assert _sizes(18) == [5, 5, 4, 4]
    assert _sizes(10) == [5, 5]
    assert _sizes(12) == [6, 6]


def test_chunk_word_ids_never_leaves_a_tiny_tail():
    # 21 used to end in a lone single word; now the extra is spread out.
    assert _sizes(21) == [6, 5, 5, 5]
    assert _sizes(7) == [7]
    assert _sizes(6) == [6]


def test_chunk_word_ids_keeps_order_and_covers_every_word():
    ids = list(range(100, 118))
    chunks = chunk_word_ids(ids)
    assert [w for c in chunks for w in c] == ids


def test_chunk_word_ids_handles_empty_and_single_word():
    assert chunk_word_ids([]) == []
    assert chunk_word_ids([1]) == [[1]]


def test_recorded_checkpoints_count_as_passed():
    chunks = [[1, 2], [3, 4]]
    assert passed_checkpoint_indices(chunks, {}, {0}) == {0}


def test_recorded_checkpoint_stays_passed_after_a_later_miss():
    chunks = [[1, 2]]
    state = {1: ReviewState(user_name="U", word_id=1, repetitions=0, fail_count=1)}
    assert passed_checkpoint_indices(chunks, state, {0}) == {0}


def test_fully_mastered_checkpoint_counts_as_passed_without_a_record():
    chunks = [[1, 2], [3, 4]]
    state = {
        1: ReviewState(user_name="U", word_id=1, repetitions=3),
        2: ReviewState(user_name="U", word_id=2, repetitions=4),
        3: ReviewState(user_name="U", word_id=3, repetitions=3),
    }
    assert passed_checkpoint_indices(chunks, state, set()) == {0}


def test_current_checkpoint_is_first_unpassed():
    assert current_checkpoint_index(4, {0, 2}) == 1
    assert current_checkpoint_index(4, set()) == 0


def test_current_checkpoint_parks_on_last_when_all_passed():
    assert current_checkpoint_index(3, {0, 1, 2}) == 2


def test_current_checkpoint_with_no_chunks_is_zero():
    assert current_checkpoint_index(0, set()) == 0
