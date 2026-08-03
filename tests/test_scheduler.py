from src.models.review_state import ReviewState
from src.services.scheduler import Scheduler


def test_update_sm2_increments_fail_count_on_a_miss():
    state = ReviewState(user_name="U", word_id=1, repetitions=3, fail_count=0)
    Scheduler.update_sm2(state, quality=1)
    assert state.repetitions == 0
    assert state.fail_count == 1


def test_update_sm2_does_not_increment_fail_count_on_success():
    state = ReviewState(user_name="U", word_id=1, repetitions=0, fail_count=2)
    Scheduler.update_sm2(state, quality=5)
    assert state.fail_count == 2


def test_update_sm2_accumulates_fail_count_across_repeated_misses():
    state = ReviewState(user_name="U", word_id=1, fail_count=0)
    Scheduler.update_sm2(state, quality=0)
    Scheduler.update_sm2(state, quality=5)
    Scheduler.update_sm2(state, quality=1)
    assert state.fail_count == 2
