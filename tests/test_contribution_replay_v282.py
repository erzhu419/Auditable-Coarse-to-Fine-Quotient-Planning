"""Semantic source, prefix, identity and actual-cost contribution checks."""
from copy import deepcopy
from fractions import Fraction as F

import pytest

from acfqp.science import contribution_replay_v282 as core


def source_fixture():
    contexts = core.route._contexts(((0, 0), (1, 0)), "source")
    target = core.route._contexts(((1, 1),), "target")[0]
    streams = {context.context_id: {op: ["DELIVERY"]*48 for op in core.route.OPERATORS}
               for context in contexts}
    initial = {"SHORT_PASS": ("road_profile",), "DETOUR_PASS": ("road_profile",),
               "RECOVERY_RETRY": ("retry_service",)}
    return contexts, target, streams, initial


def test_four_variants_distinguish_source_exclusion_frozen_counts_and_structure():
    contexts, target, streams, initial = source_fixture()
    current = {op: core.FEATURES for op in core.route.OPERATORS}
    history = [(target, "A", 1, 0, "SHORT_PASS", "LOST")]
    models = {variant: core.model_from_prefix(variant, target, initial, current,
                                             contexts, streams, history) for variant in core.VARIANTS}
    assert models["LOCAL_FULL"]["SHORT_PASS"]["DELIVERY"] == F(1, 4)
    assert models["SOURCE_FROZEN"]["SHORT_PASS"]["DELIVERY"] == F(97, 98)
    assert models["SOURCE_FIXED_UPDATE"]["SHORT_PASS"]["DELIVERY"] == F(97, 100)
    assert models["SOURCE_MAP_REVISED"]["SHORT_PASS"]["DELIVERY"] == F(1, 4)
    alternate = deepcopy(streams)
    for context in contexts:
        alternate[context.context_id]["SHORT_PASS"] = ["LOST"]*48
    assert core.model_from_prefix("LOCAL_FULL", target, initial, current, contexts, alternate, history) == models["LOCAL_FULL"]


def test_local_history_persists_across_phases_and_keeps_only_same_full_context():
    contexts, target, streams, initial = source_fixture()
    other = core.route._contexts(((1, 2),), "target")[0]
    history = [(target, "A", 1, 0, "SHORT_PASS", "DELIVERY"),
               (other, "B", 1, 1, "SHORT_PASS", "LOST"),
               (target, "B", 1, 2, "SHORT_PASS", "DELIVERY")]
    model = core.model_from_prefix("LOCAL_FULL", target, initial, initial, contexts, streams, history)
    assert model["SHORT_PASS"]["DELIVERY"] == F(5, 6)


def test_unknown_support_enters_only_allowed_committed_projection():
    contexts, target, streams, initial = source_fixture()
    history = [(target, "B", 1, 0, "RECOVERY_RETRY", "DELAYED")]
    frozen = core.model_from_prefix("SOURCE_FROZEN", target, initial, initial, contexts, streams, history)
    updated = core.model_from_prefix("SOURCE_FIXED_UPDATE", target, initial, initial, contexts, streams, history)
    assert "DELAYED" not in frozen["RECOVERY_RETRY"]
    assert updated["RECOVERY_RETRY"]["DELAYED"] == F(3, 5)


def retained_fixture():
    contexts, target, streams, fields = source_fixture()
    learner = core.route.OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(fields), contexts, streams)
    rows = []
    for trial, outcome in enumerate(("LOST", "DELIVERY")):
        vector = core.route._consequence_vector_dynamic(core.route.CASE, learner.model(target))
        recommendation = core.route._choose_policy(vector, core.route.QUERIES["goal"])
        exact = core.route._exact_vectors(target, "A")
        before = len(learner.history)
        event = dict(operator="SHORT_PASS", outcome=outcome, visit=0)
        learner.observe(target, "A", 1, trial, event["operator"], event["outcome"])
        rows.append(dict(phase="A", episode=1, trial=trial, query="goal", context=target.as_dict(),
            selected_fields=fields, recommended_policy=recommendation,
            recommendation_regret=str(core.route.regret(exact, "goal", recommendation)),
            history_before=before, history_after=len(learner.history), events=[event]))
    record = dict(source_seed=28040100, seed=28090100,
        initial_selection=dict(selected_fields=fields), arms={core.HISTORY_ARM: rows},
        selections={core.HISTORY_ARM: [dict(phase="A", episode=1, online_events_used=0, selected_fields=fields)]})
    return record, contexts, streams


def test_MAP_reproduces_retained_recommendations_before_current_event_commit():
    record, contexts, streams = retained_fixture()
    replay = core.replay_history(record, contexts, streams)
    assert replay["committed_events"] == 2 and replay["opportunities"] == 2
    assert F(replay["regrets"]["SOURCE_MAP_REVISED"]) == sum(
        (F(row["recommendation_regret"]) for row in record["arms"][core.HISTORY_ARM]), F(0))
    corrupted = deepcopy(record)
    corrupted["arms"][core.HISTORY_ARM][1]["history_before"] = 0
    with pytest.raises(ValueError, match="committed prefix"):
        core.replay_history(corrupted, contexts, streams)


@pytest.mark.parametrize("field,value,message", (
    ("recommended_policy", "BAD", "MAP replay"),
    ("recommendation_regret", "123", "MAP replay"),
    ("history_after", 17, "committed event count"),
))
def test_prediction_and_event_corruption_is_detected(field, value, message):
    record, contexts, streams = retained_fixture()
    record["arms"][core.HISTORY_ARM][0][field] = value
    with pytest.raises(ValueError, match=message):
        core.replay_history(record, contexts, streams)


def test_structural_selection_matches_actual_episode_prefix():
    record, contexts, streams = retained_fixture()
    record["selections"][core.HISTORY_ARM][0]["online_events_used"] = 1
    with pytest.raises(ValueError, match="episode selection"):
        core.replay_history(record, contexts, streams)


def test_contribution_summary_retains_adverse_and_equal_source_deltas():
    record, contexts, streams = retained_fixture()
    first = core.replay_history(record, contexts, streams)
    second = deepcopy(first)
    second["regrets"]["SOURCE_MAP_REVISED"] = str(F(first["regrets"]["SOURCE_FIXED_UPDATE"])+1)
    second["contributions"]["structure_update"]["delta"] = "1"
    second["contributions"]["structure_update"].update(improved=0, equal=0, worse=2)
    summarized = core.summarize_replay([first, second])
    assert summarized["contributions"]["structure_update"]["per_source_delta"][1] == "1"
    assert summarized["contributions"]["structure_update"]["sources_improved_equal_worse"][2] >= 1
    assert summarized["mean_regret"]["SOURCE_MAP_REVISED"] == str(
        (F(first["regrets"]["SOURCE_MAP_REVISED"])+F(second["regrets"]["SOURCE_MAP_REVISED"]))/2)


def cost_fixture():
    records = []
    for seed in range(2):
        arms, totals = {}, {}
        for index, arm in enumerate(core.online.ARMS):
            local = arm == "FULL_CONTEXT_LOCAL"
            rows = [dict(events=[dict(operator="SHORT_PASS", outcome="DELIVERY")],
                         executed_regret=str(F(index, 10)), sampled_utility="1")]
            source_fit, reserved = (0, 0) if local else (720, 240)
            arms[arm] = rows
            totals[arm] = dict(start_opportunities=1, online_events=1,
                source_fit_cost=source_fit, source_reserved_cost=reserved,
                economic_source_observations=source_fit+reserved,
                total_economic_observations=source_fit+reserved+1,
                executed_regret=str(F(index, 10)), sampled_utility="1",
                cpu_seconds=dict.fromkeys(core.online.CPU_SCOPES, .1))
        records.append(dict(source_seed=seed, arms=arms, totals=totals))
    return dict(records=records, accounting=dict(physical_source_observations=1920,
        shared_source_cpu_seconds=dict(generation=.1, fit=.2)))


def test_cost_table_uses_full_arm_economics_once_and_actual_paired_regret():
    retained = cost_fixture()
    table = core.online_cost_table(retained)
    assert table["physical_source_observations"] == 1920
    assert table["arms"]["FULL_CONTEXT_LOCAL"]["mean_total_economic_observations"] == 1
    assert table["arms"]["RELEVANT_REVISED"]["mean_total_economic_observations"] == 961
    contrast = table["paired_actual_contrasts"]["RELEVANT_REVISED_minus_FULL_CONTEXT_LOCAL"]
    assert contrast["per_source_executed_regret_delta"] == ["2/5", "2/5"]
    assert contrast["per_source_economic_observation_delta"] == [960, 960]
    retained["records"][0]["totals"]["RELEVANT_REVISED"]["online_events"] = 2
    with pytest.raises(ValueError, match="actual cost ledger"):
        core.online_cost_table(retained)


def test_natural_contribution_preserves_same_leaf_pair_and_parent_scope():
    pair = dict(mean=1., ci95=[-1., 3.], lifecycle_deltas=[1.],
                parent_mean_deltas={"0": 1.}, interval_scope="conditional parent")
    document = dict(settings=dict(value_parameters="SAME_FROZEN_LEAF_ALL_ARMS"),
        source_provenance=dict(parents=[], inherited_dynamics_costs={}),
        parent_setup_costs={"0": dict(checkpoint_loads=1, cpu_seconds=.25)},
        resident_source_and_leaf_weight_bytes=128,
        wall_seconds=10., cpu_seconds=8., output_bytes=dict(records_jsonl_gz=4096),
        summary=dict(paired_contrasts={"FROZEN_H2-DIRECT": pair},
            arms={arm: dict(costs=dict(planning_counts={}, cpu_seconds=1.)) for arm in ("FROZEN_H2", "DIRECT")},
            accounting=dict(physical_warmup_transitions=10),
            by_lifecycle=[dict(lifecycle=0, parent=0, seed_base=12,
                warmup=dict(observations=300, physical_games=1, physical_costs=dict(cpu_seconds=2.),
                    planner_setup_counts={}, planner_setup_seconds=.05, frozen_statistics_observations=256,
                    memory_import_seconds=.1, memory_import_cpu_seconds=.08,
                    memory_import_counts={"FROZEN_H2": dict(observations_received=300)}),
                arms={arm: dict(total_utility=1., costs={}, planner_setup_counts=dict(cpp_compilations=int(arm=="FROZEN_H2")),
                                planner_setup_seconds=.2 if arm=="FROZEN_H2" else .02)
                      for arm in ("FROZEN_H2", "DIRECT")})]))
    result = core.natural_cost_contribution(document)
    assert result["paired"] == pair and result["by_lifecycle"][0]["parent"] == 0
    assert result["parent_setup_costs"] == document["parent_setup_costs"]
    assert result["recorded_run_wall_seconds"] == 10. and result["recorded_run_cpu_seconds"] == 8.
    assert result["output_bytes"]["records_jsonl_gz"] == 4096
    life = result["by_lifecycle"][0]
    assert life["shared_warmup"] == document["summary"]["by_lifecycle"][0]["warmup"]
    assert "shared_warmup" not in life["arms"]["DIRECT"]
    assert life["arms"]["FROZEN_H2"]["planner_setup_counts"] == dict(cpp_compilations=1)
    assert life["arms"]["DIRECT"]["planner_setup_seconds"] == .02
    document["settings"]["value_parameters"] = "DIFFERENT"
    with pytest.raises(ValueError, match="same frozen leaf"):
        core.natural_cost_contribution(document)
