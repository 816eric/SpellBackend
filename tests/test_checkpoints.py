from src.models.review_state import ReviewState
from src.services.checkpoints import chunk_word_ids, current_checkpoint_index


def test_chunk_word_ids_splits_into_fixed_size_groups_with_remainder_last():
    assert chunk_word_ids(list(range(1, 19))) == [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
        [11, 12, 13, 14, 15],
        [16, 17, 18],
    ]


def test_chunk_word_ids_handles_empty_and_single_word():
    assert chunk_word_ids([]) == []
    assert chunk_word_ids([1]) == [[1]]


def test_chunk_word_ids_exact_multiple_of_chunk_size():
    assert chunk_word_ids([1, 2, 3, 4, 5, 6]) == [[1, 2, 3, 4, 5], [6]]


def test_current_checkpoint_index_stays_on_first_incomplete_chunk():
    chunks = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
    state_by_word = {
        1: ReviewState(user_name="U", word_id=1, repetitions=5),
        2: ReviewState(user_name="U", word_id=2, repetitions=5),
        3: ReviewState(user_name="U", word_id=3, repetitions=3),  # not mastered
    }
    assert current_checkpoint_index(chunks, state_by_word) == 0


def test_current_checkpoint_index_advances_once_first_chunk_fully_mastered():
    chunks = [[1, 2], [3, 4]]
    state_by_word = {
        1: ReviewState(user_name="U", word_id=1, repetitions=5),
        2: ReviewState(user_name="U", word_id=2, repetitions=5),
    }
    assert current_checkpoint_index(chunks, state_by_word) == 1


def test_current_checkpoint_index_stays_on_last_chunk_when_all_mastered():
    chunks = [[1, 2], [3, 4]]
    state_by_word = {
        1: ReviewState(user_name="U", word_id=1, repetitions=5),
        2: ReviewState(user_name="U", word_id=2, repetitions=5),
        3: ReviewState(user_name="U", word_id=3, repetitions=5),
        4: ReviewState(user_name="U", word_id=4, repetitions=5),
    }
    assert current_checkpoint_index(chunks, state_by_word) == 1


def test_current_checkpoint_index_with_no_chunks_is_zero():
    assert current_checkpoint_index([], {}) == 0


def test_current_checkpoint_index_treats_missing_state_as_zero_repetitions():
    chunks = [[1, 2]]
    assert current_checkpoint_index(chunks, {}) == 0
