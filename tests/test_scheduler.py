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


def test_update_sm2_early_correct_answer_does_not_advance_spacing():
    """Repeating a word within the same session (after its first correct
    answer scheduled it for tomorrow) is practice, not a spaced recall."""
    state = ReviewState(user_name="U", word_id=1)
    Scheduler.update_sm2(state, quality=5)
    assert (state.repetitions, state.interval_days) == (1, 1)
    ease = state.ease_factor

    Scheduler.update_sm2(state, quality=5)
    Scheduler.update_sm2(state, quality=5)

    assert (state.repetitions, state.interval_days) == (1, 1)
    assert state.ease_factor == ease


def test_update_sm2_advances_once_the_word_is_due_again():
    state = ReviewState(user_name="U", word_id=1)
    Scheduler.update_sm2(state, quality=5)
    state.due_date = Scheduler.today_sg()  # a day later, it is due

    Scheduler.update_sm2(state, quality=5)

    assert (state.repetitions, state.interval_days) == (2, 6)


def test_update_sm2_early_miss_still_resets_the_word():
    state = ReviewState(user_name="U", word_id=1)
    Scheduler.update_sm2(state, quality=5)
    Scheduler.update_sm2(state, quality=1)
    assert state.repetitions == 0
    assert state.fail_count == 1
