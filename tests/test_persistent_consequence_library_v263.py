from fractions import Fraction as F

from acfqp.science.persistent_consequence_library_v263 import (
    BRIER_SPLIT_THRESHOLD,
    FIT_PER_OPERATOR,
    PHASES,
    SAMPLES_PER_OPERATOR,
    PersistentLibrary,
    _draw_rows,
    _empty_counts,
    _exact_vectors,
    _metrics,
    consequence_vector,
    posterior,
    run_development,
)
from acfqp.science.mechanism_switch_task_v205 import ALPHABETS, OPERATORS, WEATHER


def _rows(weather: str, seed: int):
    law = WEATHER[weather]
    return _draw_rows({
        "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
        "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
        "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
    }, seed)


def test_library_starts_empty_and_commits_validation_after_scoring():
    rows = _rows("normal", 263000)
    library = PersistentLibrary()
    result = library.ingest("opaque_0", rows)
    assert result["reason"] == "initial"
    assert result["fit_rows"] == FIT_PER_OPERATOR * len(OPERATORS)
    assert result["validation_rows"] == (SAMPLES_PER_OPERATOR - FIT_PER_OPERATOR) * len(OPERATORS)
    assert result["validation_brier"] >= 0
    assert library.assignments == {"opaque_0": 0}


def test_library_splits_changed_phase_and_reuses_return_phase():
    library = PersistentLibrary()
    first = library.ingest("opaque_0", _rows("normal", 263000))
    second = library.ingest("opaque_1", _rows("wet", 263001))
    third = library.ingest("opaque_2", _rows("normal", 263002))
    assert first["module_count_after"] == 1
    assert second["reason"] == "heldout_split_trigger"
    assert third["reason"] == "reuse"
    assert library.assignments["opaque_2"] == library.assignments["opaque_0"]


def test_query_weights_can_select_different_policies():
    vectors = _exact_vectors("normal")
    metrics = _metrics(vectors, vectors)
    assert metrics["risk"]["exact_policy"] != metrics["goal"]["exact_policy"]
    assert all(row["policy_correct"] for row in metrics.values())


def test_development_report_is_finite_and_preserves_query_changes():
    result = run_development()
    assert result["status"] == "DEVELOPMENT_COMPLETE"
    assert result["scientific_gate"] == "NOT_A_FORMAL_GATE"
    assert result["settings"]["brier_split_threshold"] == BRIER_SPLIT_THRESHOLD
    library_rows = result["arms"]["LIBRARY"]
    assert [row["phase"] for row in library_rows] == [phase for phase, _ in PHASES]
    assert library_rows[1]["assignment"]["reason"] == "heldout_split_trigger"
    assert library_rows[2]["assignment"]["reason"] == "reuse"
    assert all(isinstance(value, bool) for row in library_rows for value in (
        row["metrics"][query]["policy_correct"] for query in row["metrics"]))
