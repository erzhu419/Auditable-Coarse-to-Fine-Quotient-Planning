from copy import deepcopy
from fractions import Fraction as F
import gzip
from itertools import product
import json
from types import SimpleNamespace

import pytest

from acfqp.science import evidence_weighted_prefix_v279 as v279


v278 = v279.v278
SUBSETS = v279.CANDIDATE_SUBSETS


def uniform_weights():
    return {op: dict.fromkeys(SUBSETS, F(1, 4)) for op in v278.OPERATORS}


def synthetic_source():
    contexts = v278._contexts(v278.SOURCE_PAIRS, "source")
    pattern = {
        "SHORT_PASS": ["DELIVERY", "LOST"] * 32,
        "DETOUR_PASS": (["DELIVERY", "LOST", "RECOVERY"] * 22)[:64],
        "RECOVERY_RETRY": ["DELIVERY", "LOST"] * 32,
    }
    return contexts, {c.context_id: deepcopy(pattern) for c in contexts}


def synthetic_record(contexts, streams):
    initial = v278.select_factor_subsets(contexts, streams)
    learner = v278.OnlineLearner("CONTINUAL_FACTOR_ONLINE",
        dict(initial["selected_fields"]), contexts, streams)
    target = v278.TARGETS[0]
    rows, selections = [], []
    # These are synthetic retained observations, never sampled outcomes.
    schedule = [
        ("A", 1, 0, "goal", [{"operator": "SHORT_PASS", "outcome": "DELIVERY", "visit": 0}]),
        ("A", 1, 1, "risk", [
            {"operator": "DETOUR_PASS", "outcome": "RECOVERY", "visit": 0},
            {"operator": "RECOVERY_RETRY", "outcome": "LOST", "visit": 1}]),
        ("B", 1, 0, "goal", [
            {"operator": "DETOUR_PASS", "outcome": "RECOVERY", "visit": 0},
            {"operator": "RECOVERY_RETRY", "outcome": "DELAYED", "visit": 1}]),
    ]
    active = None
    for phase, episode, trial, query, events in schedule:
        if active != (phase, episode):
            selection = v278.select_online_fields(contexts, streams, learner.history)
            learner.selected = selection["selected_fields"]
            selections.append({"phase": phase, "episode": episode, **selection})
            active = phase, episode
        prediction = v278._consequence_vector_dynamic(v278.CASE, learner.model(target))
        policy = v278._choose_policy(prediction, v278.QUERIES[query])
        row = {"phase": phase, "episode": episode, "trial": trial,
            "context": target.as_dict(), "query": query,
            "recommended_policy": policy, "recommendation_regret": str(v278.regret(
                v278._exact_vectors(target, phase), query, policy)),
            "history_before": len(learner.history), "events": deepcopy(events)}
        for event in events:
            learner.observe(target, phase, episode, trial, event["operator"], event["outcome"])
        row["history_after"] = len(learner.history)
        rows.append(row)
    return {"source_seed": 275401, "seed": 275401, "initial_selection": initial,
            "arms": {arm: deepcopy(rows) for arm in v279.HISTORY_ARMS},
            "selections": {arm: deepcopy(selections) for arm in v279.HISTORY_ARMS}}


def test_evidence_weights_normalize_and_ignore_common_score_offset():
    scores = {op: [{"fields": fields, "score": index - 3.0}
                  for index, fields in enumerate(SUBSETS)] for op in v278.OPERATORS}
    selection = {"scores": scores}
    shifted = deepcopy(selection)
    for rows in shifted["scores"].values():
        for row in rows:
            row["score"] += 1000
    weights = v279.evidence_weights(selection)
    assert weights == v279.evidence_weights(shifted)
    for row in weights.values():
        assert sum(row.values(), F(0)) == 1
        assert all(value > 0 for value in row.values())
        assert row[SUBSETS[0]] < row[SUBSETS[-1]]
    uniform = {"scores": {op: [{"fields": fields, "score": -999.0}
        for fields in SUBSETS] for op in v278.OPERATORS}}
    assert v279.evidence_weights(uniform) == uniform_weights()


def test_mixed_rows_equal_independent_structure_average_of_policy_vectors():
    models = {}
    for index, fields in enumerate(SUBSETS):
        short, recovery, retry = F(index + 1, 5), F(index + 1, 10), F(index + 2, 7)
        models[fields] = {
            "SHORT_PASS": {"DELIVERY": short, "LOST": 1 - short},
            "DETOUR_PASS": {"DELIVERY": F(1, 3), "LOST": F(2, 3) - recovery,
                            "RECOVERY": recovery},
            "RECOVERY_RETRY": {"DELIVERY": retry, "LOST": 1 - retry},
        }
    models[SUBSETS[-1]]["RECOVERY_RETRY"] = {
        "DELIVERY": F(1, 2), "LOST": F(1, 4), "DELAYED": F(1, 4)}
    candidates = {fields: SimpleNamespace(model=lambda _target, m=model: m)
                  for fields, model in models.items()}
    weights = {op: {fields: F(1 + (index + shift) % 4, 10)
        for index, fields in enumerate(SUBSETS)} for shift, op in enumerate(v278.OPERATORS)}
    mixture = v279.weighted_model(candidates, v278.TARGETS[0], weights)
    actual = v278._consequence_vector_dynamic(v278.CASE, mixture)
    expected = {policy: [F(0), F(0), F(0)] for policy in actual}
    for combination in product(SUBSETS, repeat=len(v278.OPERATORS)):
        probability = F(1)
        rows = {}
        for operator, fields in zip(v278.OPERATORS, combination):
            probability *= weights[operator][fields]
            rows[operator] = models[fields][operator]
        vectors = v278._consequence_vector_dynamic(v278.CASE, rows)
        for policy, vector in vectors.items():
            for index, value in enumerate(vector):
                expected[policy][index] += probability * value
    assert actual == {policy: tuple(values) for policy, values in expected.items()}
    assert all(sum(row.values(), F(0)) == 1 for row in mixture.values())


def test_delayed_admission_is_projection_local_and_uses_committed_prefix():
    contexts, streams = synthetic_source()
    candidates = v279.candidate_learners(contexts, streams)
    observed, target = v278.TARGETS[0], v278.TARGETS[-1]
    before = v279.weighted_model(candidates, target, uniform_weights())
    assert "DELAYED" not in before["RECOVERY_RETRY"]
    for learner in candidates.values():
        learner.observe(observed, "B", 1, 0, "RECOVERY_RETRY", "DELAYED")
    predictions = {fields: learner.model(target) for fields, learner in candidates.items()}
    assert predictions[()]["RECOVERY_RETRY"]["DELAYED"] > 0
    for fields in SUBSETS[1:]:
        assert "DELAYED" not in predictions[fields]["RECOVERY_RETRY"]
        assert "DELAYED" in candidates[fields].known_support["RECOVERY_RETRY"]
    after = v279.weighted_model(candidates, target, uniform_weights())
    assert after["RECOVERY_RETRY"]["DELAYED"] == predictions[()]["RECOVERY_RETRY"]["DELAYED"] / 4
    assert "DELAYED" not in before["RECOVERY_RETRY"]


def test_source_audit_suffix_cannot_change_weights_or_predictions():
    contexts, streams = synthetic_source()
    altered = deepcopy(streams)
    for rows in altered.values():
        for operator in v278.OPERATORS:
            rows[operator][48:] = ["DELAYED" if operator == "RECOVERY_RETRY" else "LOST"] * 16
    original_selection = v278.select_online_fields(contexts, streams, [])
    assert original_selection == v278.select_online_fields(contexts, altered, [])
    weights = v279.evidence_weights(original_selection)
    original = v279.weighted_model(v279.candidate_learners(contexts, streams), v278.TARGETS[0], weights)
    changed = v279.weighted_model(v279.candidate_learners(contexts, altered), v278.TARGETS[0], weights)
    assert changed == original
    assert "DELAYED" not in changed["RECOVERY_RETRY"]


def test_hard_replay_matches_retained_recommendations_without_sampling(monkeypatch):
    contexts, streams = synthetic_source()
    record = synthetic_record(contexts, streams)
    immutable = deepcopy(record)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("retained-prefix replay must not execute or draw outcomes")

    monkeypatch.setattr(v278, "execute_policy", forbidden)
    monkeypatch.setattr(v278, "_stream", forbidden)
    observed = []
    original_observe = v278.OnlineLearner.observe

    def capture(learner, *event):
        observed.append(event)
        return original_observe(learner, *event)

    monkeypatch.setattr(v278.OnlineLearner, "observe", capture)
    arm = v279.HISTORY_ARMS[0]
    result = v279.replay_arm(record, arm, contexts, streams)
    assert record == immutable
    assert result["opportunities"] == 3
    assert F(result["map_regret"]) == sum((F(row["recommendation_regret"])
        for row in record["arms"][arm]), F(0))
    assert sum(result["improved_equal_worse"]) == 3
    expected = [(row["context"]["road_profile"], row["context"]["retry_service"],
        row["phase"], row["episode"], row["trial"], event["operator"], event["outcome"])
        for row in record["arms"][arm] for event in row["events"] for _ in range(5)]
    actual = [(context.road_profile, context.retry_service, *event) for context, *event in observed]
    assert actual == expected


def test_replay_rejects_changed_decision_or_prefix_ledger():
    contexts, streams = synthetic_source()
    original = synthetic_record(contexts, streams)
    arm = v279.HISTORY_ARMS[0]
    for location, field, value, message in (
        ("row", "history_before", 1, "decision does not match committed prefix"),
        ("row", "history_after", 2, "committed event count"),
        ("selection", "online_events_used", 1, "episode selection"),
        ("row", "recommended_policy", "UNRECORDED_POLICY", "hard-MAP replay"),
    ):
        record = deepcopy(original)
        item = record["arms"][arm][0] if location == "row" else record["selections"][arm][0]
        item[field] = value
        with pytest.raises(ValueError, match=message):
            v279.replay_arm(record, arm, contexts, streams)


def test_summary_retains_positive_and_negative_source_differences():
    records = []
    for index, delta in enumerate((-2, 0, 3)):
        decisions = [1, 2, 0] if delta < 0 else [0, 2, 1] if delta > 0 else [0, 3, 0]
        item = {"map_regret": "10", "weighted_regret": str(10 + delta), "delta": str(delta),
                "changed": int(delta != 0), "opportunities": 3, "improved_equal_worse": decisions}
        records.append({"source_seed": 275401 + index, "seed": 275401 + index,
                        "arms": {arm: deepcopy(item) for arm in v279.HISTORY_ARMS}})
    summary = v279.summarize(records)
    for arm in v279.HISTORY_ARMS:
        assert summary[arm]["per_source_delta"] == ["-2", "0", "3"]
        assert summary[arm]["sources_improved_equal_worse"] == [1, 1, 1]
        assert summary[arm]["decisions_improved_equal_worse"] == [1, 7, 1]
        assert summary[arm]["mean_delta"] == "1/3"
        assert summary[arm]["changed"] == 2
        assert summary[arm]["opportunities"] == 9


def test_diagnostic_keeps_every_retained_source_and_accounts_for_no_new_data(tmp_path, monkeypatch):
    contexts, streams = synthetic_source()
    first = synthetic_record(contexts, streams)
    second = deepcopy(first)
    second.update(source_seed=275402, seed=275402)
    input_path = tmp_path / "retained.json.gz"
    with gzip.open(input_path, "wt", encoding="utf-8") as handle:
        json.dump({"records": [first, second]}, handle)
    reconstructions = []

    def reconstruct(context, seed):
        reconstructions.append((context.context_id, seed))
        return deepcopy(streams[context.context_id])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("diagnostic must not execute a target policy")

    monkeypatch.setattr(v278, "_stream", reconstruct)
    monkeypatch.setattr(v278, "execute_policy", forbidden)
    result = v279.run_diagnostic(input_path)
    assert [(r["source_seed"], r["seed"]) for r in result["records"]] == [(275401, 275401), (275402, 275402)]
    assert reconstructions == [(c.context_id, seed + index)
        for seed in (275401, 275402) for index, c in enumerate(contexts)]
    assert result["accounting"] == {"new_source_observations": 0,
                                   "new_target_observations": 0, "replayed_decisions": 12}
    assert result["scientific_gate"] == "NOT_A_FORMAL_GATE"
    assert all(result["summary"][arm]["opportunities"] == 6 for arm in v279.HISTORY_ARMS)
