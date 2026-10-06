from fractions import Fraction as F
from types import SimpleNamespace

from acfqp.science import online_factor_confirmation_v277 as v277
from acfqp.science import online_factor_repair_v276 as v276
from acfqp.science import query_relevant_coverage_v278 as v278


SUPPORT = {
    "SHORT_PASS": {"DELIVERY", "LOST"},
    "DETOUR_PASS": {"DELIVERY", "LOST", "RECOVERY"},
    "RECOVERY_RETRY": {"DELIVERY", "LOST"},
}


def model(short=F(9, 10), delivery=F(1, 5), recovery=F(3, 5), retry=F(1, 2)):
    return {
        "SHORT_PASS": {"DELIVERY": short, "LOST": 1 - short},
        "DETOUR_PASS": {"DELIVERY": delivery, "LOST": 1 - delivery - recovery, "RECOVERY": recovery},
        "RECOVERY_RETRY": {"DELIVERY": retry, "LOST": 1 - retry},
    }


def empty_learner(operator, history=()):
    source = v278._contexts(((0, 0),), "source")
    fields = {op: () for op in v278.OPERATORS}
    fields[operator] = ("road_profile", "retry_service")
    streams = {source[0].context_id: {op: ["DELIVERY"] * 64 for op in v278.OPERATORS}}
    learner = SimpleNamespace(source_contexts=source, source_streams=streams,
        selected=dict(fields), history=list(history), known_support={op: set(row) for op, row in SUPPORT.items()})
    return learner, fields


def old_source_learner(seed):
    contexts = v278._contexts(v278.SOURCE_PAIRS, "source")
    streams = {c.context_id: v278._stream(c, seed + index) for index, c in enumerate(contexts)}
    fields = v278.select_factor_subsets(contexts, streams)["selected_fields"]
    return v278.OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(fields), contexts, streams), fields


def test_vertex_envelope_identifies_irrelevant_retry_and_reward():
    posterior = model()
    assert v278.relevance_envelopes(posterior, "RECOVERY_RETRY", SUPPORT["RECOVERY_RETRY"]) == {
        "reward": F(0), "risk": F(0), "goal": F(0)}
    # SHORT currently wins. A LOST vertex makes WAIT best for risk and the
    # detour best for goal; reward depends only on fixed route costs.
    assert v278.relevance_envelopes(posterior, "SHORT_PASS", SUPPORT["SHORT_PASS"]) == {
        "reward": F(0), "risk": F(41, 10), "goal": F(37, 25)}


def test_known_delayed_vertex_changes_envelope_only_after_admission():
    posterior = model(short=F(1, 10), delivery=F(4, 5), recovery=F(19, 100), retry=F(9, 10))
    old = v278.relevance_envelopes(posterior, "RECOVERY_RETRY", SUPPORT["RECOVERY_RETRY"])
    expanded = v278.relevance_envelopes(posterior, "RECOVERY_RETRY", SUPPORT["RECOVERY_RETRY"] | {"DELAYED"})
    assert old["goal"] == F(361, 2000)
    assert expanded["goal"] == F(1121, 2000)


def test_remaining_schedule_includes_current_exact_pair_and_full_lifecycle():
    target = v278.TARGETS[0]
    assert len(v278.SCHEDULE) == 288
    assert v278.remaining_query_counts(target, 0) == {"reward": 24, "risk": 24, "goal": 24}
    assert v278.remaining_query_counts(target, 1) == {"reward": 24, "risk": 24, "goal": 23}
    renamed = v278._contexts(((1, 1),), "another_id")[0]
    assert v278.remaining_query_counts(renamed, 1) == v278.remaining_query_counts(target, 1)
    assert v278.remaining_query_counts(v278.TARGETS[-1], 287) == {"reward": 1, "risk": 0, "goal": 0}
    assert sum(v278.remaining_query_counts(target, 287).values()) == 0
    assert sum(v278.remaining_query_counts(target, 288).values()) == 0


def test_current_source_coverage_stops_stale_initial_quota():
    learner, initial = empty_learner("SHORT_PASS")
    learner.selected["SHORT_PASS"] = ()
    assert v278.coverage_request(learner, initial, v278.TARGETS[0]) == "SHORT_PASS"
    requested, _, traces = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, model(), True)
    assert requested is None
    assert traces == [{"operator": "SHORT_PASS", "remaining_quota": 4, "reason": "CURRENT_SOURCE_COVERED"}]


def test_quota_stays_on_initial_projection_after_factor_revision():
    learner, initial = empty_learner("SHORT_PASS")
    initial["SHORT_PASS"] = ("retry_service",)
    learner.selected["SHORT_PASS"] = ("road_profile",)
    other = v278.TARGETS[2]
    learner.history = [(other, "A", 1, index, "SHORT_PASS", "DELIVERY") for index in range(3)]
    requested, _, traces = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, model(), False)
    assert requested == "SHORT_PASS"
    assert traces[0]["remaining_quota"] == 1
    learner.history.append((other, "A", 1, 3, "SHORT_PASS", "DELIVERY"))
    assert v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, model(), False)[0] is None


def test_retry_cost_counts_failed_reach_attempts_but_natural_execution_remains():
    learner, initial = empty_learner("RECOVERY_RETRY")
    posterior = model(short=F(1, 100), delivery=F(4, 5), recovery=F(1, 100), retry=F(1, 100))
    requested, policy, traces = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, posterior, True)
    assert requested is None and policy == "DETOUR_RETURN"
    assert traces[0]["reason"] == "ATTEMPT_BUDGET"
    assert F(traces[0]["reach_probability"]) == F(1, 100)
    assert F(traces[0]["expected_attempts"]) == 400
    posterior["RECOVERY_RETRY"] = {"DELIVERY": F(9, 10), "LOST": F(1, 10)}
    requested, policy, traces = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, posterior, True)
    assert requested == "RECOVERY_RETRY" and policy == "DETOUR_RETRY"
    assert traces[0]["reason"] == "NATURAL"
    assert F(traces[0]["expected_attempts"]) == 400


def test_cost_filter_can_reject_an_affordable_but_unrecoverable_override():
    learner, initial = empty_learner("RECOVERY_RETRY")
    posterior = model(short=F(23, 25), delivery=F(4, 5), recovery=F(1, 5), retry=F(1, 100))
    relevant = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 192, posterior, False)
    cost = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 192, posterior, True)
    assert relevant[0] == "RECOVERY_RETRY"
    assert cost[0] is None and cost[1] == "SHORT"
    trace = cost[2][0]
    assert trace["reason"] == "COST_EXCEEDS_POTENTIAL"
    assert F(trace["expected_attempts"]) == 20 <= sum(trace["remaining_queries"].values())
    assert F(trace["expected_attempts"]) * F(trace["probe_loss"]) > F(trace["potential_gain"])


def test_detour_sampling_uses_better_route_without_unnecessary_retry():
    learner, initial = empty_learner("DETOUR_PASS")
    posterior = model(short=F(4, 5), delivery=F(1, 2), recovery=F(3, 10), retry=F(1, 100))
    requested, policy, _ = v278.relevant_request(learner, initial, v278.TARGETS[0], "goal", 0, posterior, False)
    assert requested == "DETOUR_PASS" and policy == "DETOUR_RETURN"


def test_old_short_blindspot_survives_cost_filter_without_target_sampling():
    learner, initial = old_source_learner(275402)
    assert initial["SHORT_PASS"] == ("road_profile", "retry_service")
    for ordinal, target in enumerate(v278.TARGETS):
        requested, policy, traces = v278.relevant_request(learner, initial, target, "goal", ordinal, learner.model(target), True)
        assert requested == "SHORT_PASS" and policy == "SHORT"
        assert traces[0]["reason"] == "ACCEPT"
        assert F(traces[0]["expected_attempts"]) * F(traces[0]["probe_loss"]) < F(traces[0]["potential_gain"])
    assert learner.history == []


def test_old_adverse_source_skips_wet_retry_and_keeps_natural_blocked_retry():
    learner, initial = old_source_learner(27741100)
    for ordinal, target in enumerate(v278.TARGETS):
        requested, policy, traces = v278.relevant_request(learner, initial, target, "goal", ordinal, learner.model(target), True)
        if target.road_profile == 1:
            assert requested is None and policy == "SHORT"
            assert traces[0]["reason"] == "IRRELEVANT"
        else:
            assert requested == "RECOVERY_RETRY" and policy == "DETOUR_RETRY"
            assert traces[0]["reason"] == "NATURAL"
    assert learner.history == []


def test_audit_suffix_cannot_change_source_fit_model_or_admit_support():
    learner, fields = old_source_learner(275402)
    changed = {name: {op: list(outcomes[:48]) + ["LOST"] * 16 for op, outcomes in rows.items()}
               for name, rows in learner.source_streams.items()}
    changed_fields = v278.select_factor_subsets(learner.source_contexts, changed)["selected_fields"]
    other = v278.OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(changed_fields), learner.source_contexts, changed)
    target = v278.TARGETS[0]
    assert fields == changed_fields
    assert learner.model(target) == other.model(target)
    assert "DELAYED" not in learner.known_support["RECOVERY_RETRY"]
    before = v278.relevant_request(learner, fields, target, "goal", 0, learner.model(target), True)
    assert before == v278.relevant_request(other, changed_fields, target, "goal", 0, other.model(target), True)
    learner.observe(target, "B", 1, 0, "RECOVERY_RETRY", "DELAYED")
    assert "DELAYED" in learner.known_support["RECOVERY_RETRY"]
    assert "DELAYED" in learner.model(target)["RECOVERY_RETRY"]
    assert "DELAYED" not in other.known_support["RECOVERY_RETRY"]


def test_passive_and_quota_match_v276_on_small_committed_lifecycle(monkeypatch):
    fields = {op: ("road_profile", "retry_service") for op in v278.OPERATORS}
    streams = {op: ["DELIVERY"] * 64 for op in v278.OPERATORS}
    def execute(_context, _phase, _seed, _episode, _trial, policy):
        if policy == "WAIT":
            return []
        if policy == "SHORT":
            return [{"operator": "SHORT_PASS", "outcome": "DELIVERY", "visit": 0}]
        events = [{"operator": "DETOUR_PASS", "outcome": "RECOVERY", "visit": 0}]
        if policy == "DETOUR_RETRY":
            events.append({"operator": "RECOVERY_RETRY", "outcome": "LOST", "visit": 1})
        return events
    for module in (v276, v278):
        monkeypatch.setattr(module, "PHASES", ("A",))
        monkeypatch.setattr(module, "EPISODES_PER_PHASE", 3)
        monkeypatch.setattr(module, "_stream", lambda *_: streams)
        monkeypatch.setattr(module, "select_factor_subsets", lambda *_: {"selected_fields": dict(fields)})
        monkeypatch.setattr(module, "select_online_fields", lambda *_: {"selected_fields": dict(fields)})
        monkeypatch.setattr(module, "execute_policy", execute)
        monkeypatch.setattr(module, "_exact_vectors", lambda *_: v278._consequence_vector_dynamic(v278.CASE, model()))
    monkeypatch.setattr(v278, "SCHEDULE", tuple((v278.TARGETS[t % 4], v278.QUERY_SCHEDULE[e % 3])
        for e in range(3) for t in range(8)))
    old, new = v276.run_lifecycle(-1, -1), v278.run_lifecycle(-1, -1)
    keys = ("phase", "episode", "trial", "query", "context", "recommended_policy", "executed_policy",
            "coverage_request", "selected_fields", "history_before", "history_after", "events",
            "executed_regret", "recommendation_regret")
    for old_arm, new_arm in (("PASSIVE_REVISED", "PASSIVE_REVISED"), ("COVERED_REVISED", "QUOTA_REVISED")):
        assert [{k: row[k] for k in keys} for row in old["arms"][old_arm]] == [
            {k: row[k] for k in keys} for row in new["arms"][new_arm]]
    assert new["arms"]["PASSIVE_REVISED"][-1]["executed_policy"] == "WAIT"
    assert new["arms"]["QUOTA_REVISED"][-1]["executed_policy"] == "DETOUR_RETRY"


def test_registered_sources_are_unfiltered_disjoint_and_bootstrap_keeps_adverse_lifecycles(monkeypatch):
    assert len(v278.SOURCE_SEEDS) == len(v278.SEEDS) == 64
    new_source_draws = {seed + offset for seed in v278.SOURCE_SEEDS for offset in range(5)}
    old_source_draws = {seed + offset for seed in (*v276.SOURCE_SEEDS, *v277.SOURCE_SEEDS) for offset in range(5)}
    assert len(new_source_draws) == 64 * 5
    assert new_source_draws.isdisjoint(old_source_draws)
    assert set(v278.SOURCE_SEEDS).isdisjoint(v278.SEEDS)
    monkeypatch.setattr(v278, "BOOTSTRAP_DRAWS", 100)
    contrast = v278.paired_contrast([F(-3), F(0), F(3)])
    assert contrast == v278.paired_contrast([F(-3), F(0), F(3)])
    assert contrast["mean_regret_delta"] == "0"
    assert contrast["improved_equal_worse"] == [1, 1, 1]
    assert contrast["per_seed_regret_delta"] == ["-3", "0", "3"]
    assert contrast["ci95"][0] < 0 < contrast["ci95"][1]
