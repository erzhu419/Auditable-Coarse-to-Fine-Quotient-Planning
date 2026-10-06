"""Frozen-policy roster checks, with no environment or fitting execution."""

from copy import deepcopy

import pytest

from scripts import run_controlled_predictive_fixed_board_replication_v175 as runner
from test_consequence_partition_runner_v172 import make_root


def root(cohort="TRAIN", life=0, replica=0, slot=0, ordinal=0):
    result = make_root(life, replica, slot, cohort)
    result.update(cohort=cohort, ordinal=ordinal)
    return result


def choice(record, tree="DOWN", one="RIGHT"):
    return {
        "cohort": record["cohort"], "root_id": record["root_id"],
        "changed": tree != one,
        "decisions": {
            "TREE": {"canonical_action": tree},
            "ONE": {"canonical_action": one},
        },
    }


def frozen(records, same_ids=()):
    return {"choices": [choice(record, one="DOWN" if record["root_id"] in same_ids else "RIGHT")
                        for record in records]}


def test_protocol_adds_suffixes_without_new_sources_fits_or_promotion():
    settings = runner.settings()
    assert settings["new_source_games"] == 0
    assert settings["new_model_fits"] == 0
    assert settings["new_parameter_updates"] == 0
    assert settings["strategy_promotion"] is False
    assert settings["source_clusters_per_history"] == {"TRAIN": 12, "FRESH": 8}


def test_worst_case_roster_has_exact_fixed_budget_and_all_source_units():
    records = [root(cohort, life, replica, slot, replica * 8 + slot)
               for cohort, sources in (("TRAIN", 12), ("FRESH", 8))
               for life in range(4) for replica in range(sources) for slot in range(8)]
    assert len(records) == 640
    fixed = frozen(records)
    rosters = {phase: runner.branch_roster(records, fixed, phase)
               for phase in ("TRAIN_REPL", "FRESH_REPL")}
    assert len(rosters["TRAIN_REPL"]) == 384 * 16 * 2
    assert len(rosters["FRESH_REPL"]) == 256 * 16 * 2
    assert sum(map(len, rosters.values())) == 20_480
    assert sum(map(len, rosters.values())) * 8192 == 167_772_160
    assert len({row["branch_id"] for rows in rosters.values() for row in rows}) == 20_480
    for phase, sources in (("TRAIN_REPL", 12), ("FRESH_REPL", 8)):
        for life in range(4):
            assert len({row["source_id"] for row in rosters[phase] if row["life"] == life}) == sources


def test_skipping_zero_difference_keeps_the_ordinal_of_later_roots():
    records = [root("TRAIN", 2, 0, slot, slot) for slot in range(3)]
    fixed = frozen(records, same_ids=[records[1]["root_id"]])
    before = deepcopy((records, fixed))
    roster = runner.branch_roster(records, fixed, "TRAIN_REPL")
    assert len(roster) == 64
    assert records[1]["root_id"] not in {row["root_id"] for row in roster}
    for record in (records[0], records[2]):
        rows = [row for row in roster if row["root_id"] == record["root_id"]]
        assert {row["ordinal"] for row in rows} == {record["ordinal"]}
        for suffix in range(16):
            pair = [row for row in rows if row["suffix"] == suffix]
            seed = 17_500_000_000 + 10_000_000 + 2_000_000 + record["ordinal"] * 1000 + suffix
            assert {row["seed"] for row in pair} == {seed}
            assert len(pair) == 2
    assert (records, fixed) == before


def test_identical_actions_need_no_new_branches_and_keep_frozen_root_records():
    records = [root("TRAIN", life, replica, 0, replica)
               for life in range(4) for replica in range(12)]
    fixed = frozen(records, same_ids=[record["root_id"] for record in records])
    before = deepcopy(fixed)
    assert runner.branch_roster(records, fixed, "TRAIN_REPL") == []
    assert fixed == before
    # The full SOURCE denominator remains in the frozen data, despite zero sampling.
    for life in range(4):
        assert len({record["source_id"] for record in records if record["life"] == life}) == 12
    assert len(fixed["choices"]) == 48


def test_cohorts_use_disjoint_streams_and_transport_each_frozen_action():
    records = [root(cohort, 1, 0, 0, 7) for cohort in ("TRAIN", "FRESH")]
    fixed = {"choices": [choice(record, tree="RIGHT", one="DOWN") for record in records]}
    seeds = {}
    for phase, cohort, offset in (("TRAIN_REPL", "TRAIN", 10_000_000),
                                  ("FRESH_REPL", "FRESH", 20_000_000)):
        roster = runner.branch_roster(records, fixed, phase)
        assert len(roster) == 32
        assert {row["cohort"] for row in roster} == {cohort}
        assert {row["root_id"] for row in roster} == {f"{cohort}:1:0:0"}
        seeds[phase] = {row["seed"] for row in roster}
        for suffix in range(16):
            pair = [row for row in roster if row["suffix"] == suffix]
            assert {row["seed"] for row in pair} == {
                17_500_000_000 + offset + 1_000_000 + 7000 + suffix
            }
            assert [(row["canonical_action"], row["actual_action"]) for row in pair] == [
                ("RIGHT", "DOWN"), ("DOWN", "RIGHT")
            ]
            for row in pair:
                assert row["query"] == "risk1"
                assert row["source_id"] == f"{cohort}_SOURCE:1:0"
                assert row["branch_id"] == f'{phase}:{row["root_id"]}:{suffix}:{row["canonical_action"]}'
                assert "mode" not in row
    assert seeds["TRAIN_REPL"].isdisjoint(seeds["FRESH_REPL"])


def reference_fixture():
    records = [root("TRAIN"), root("FRESH")]
    fixed = frozen(records)
    old = [
        {"root_id": records[1]["root_id"], "mode": "PART_UTILITY_UNPRUNED", "canonical_action": "DOWN"},
        {"root_id": records[1]["root_id"], "mode": "ONE_LATE", "canonical_action": "RIGHT"},
        # These other retained V174 methods are irrelevant to the fixed TREE policy.
        {"root_id": records[1]["root_id"], "mode": "PART_UTILITY_CONFIRMED", "canonical_action": "RIGHT"},
        {"root_id": records[1]["root_id"], "mode": "PART_SSE_UNPRUNED", "canonical_action": "RIGHT"},
    ]
    return fixed, old


def test_reference_matches_unpruned_tree_and_one_without_reading_train_teacher():
    fixed, old = reference_fixture()
    assert runner.reference_choices_match(fixed, old)
    assert all(row["root_id"].startswith("FRESH:") for row in old)


@pytest.mark.parametrize("failure", ["changed_tree", "missing_one"])
def test_reference_binding_rejects_a_different_or_missing_fresh_action(failure):
    fixed, old = reference_fixture()
    if failure == "changed_tree":
        old[0]["canonical_action"] = "RIGHT"
    else:
        old = [row for row in old if row["mode"] != "ONE_LATE"]
    assert not runner.reference_choices_match(fixed, old)


def test_compact_outcome_keeps_fixed_board_identity_without_replica_or_slot():
    record = root("TRAIN", life=1, replica=3, slot=5, ordinal=29)
    plan = runner.branch_roster([record], frozen([record]), "TRAIN_REPL")[0]
    assert "replica" not in plan
    assert "slot" not in plan
    components = [25.0, 0.0, 1.0]
    result = {
        "score": 51_200, "steps": 1000, "status": "WON",
        "components": components, "utility": 26.0,
    }
    module = {
        "mode": "FORCED_H2", "life": 1, "forced_decisions": 1, "h2_calls": 999,
    }
    row = {**deepcopy(plan), "root_board": record["canonical_board"],
           "result": result, "module": module}
    compact = runner.compact_outcome(row)
    for key, value in plan.items():
        assert compact[key] == value
    assert compact["cohort"] == "TRAIN"
    assert compact["source_id"] == record["source_id"]
    assert compact["ordinal"] == 29
    for key, value in result.items():
        assert compact[key] == value
    assert compact["components"] == [25.0, 0.0, 1.0]
    assert compact["module"] == module


def test_retained_branch_is_not_replayed_and_paid_work_is_counted_once(tmp_path, monkeypatch):
    from collections import Counter
    from types import SimpleNamespace

    record = root("TRAIN", life=1, replica=3, slot=5, ordinal=29)
    record["board"] = record["canonical_board"]
    plan = runner.branch_roster([record], frozen([record]), "TRAIN_REPL")[0]
    paid_policy = {"decisions": 4}
    paid_environment = {"sampled_transitions": 4}
    row = {
        **deepcopy(plan),
        "root_board": record["board"],
        "module": {"mode": "FORCED_H2", "life": 1, "forced_decisions": 1, "h2_calls": 3},
        "result": {
            "score": 2048, "steps": 4, "status": "LOST",
            "components": [1.0, 1.0, 0.0], "utility": 0.0,
            "environment_counts": paid_environment,
            "policy_counts": paid_policy,
            "policy_counts_by_query": {"risk1": paid_policy, "risk8": {}},
        },
    }
    bank = {query: SimpleNamespace(counts=Counter()) for query in ("risk1", "risk8")}
    teacher_helpers = runner.parent.prior.old.prior
    monkeypatch.setattr(teacher_helpers, "teachers", lambda source, folder: (bank, {}, {}, {}))

    def finish_teachers(teachers, parents, leaves, records):
        records.update({query: {"counts": dict(teacher.counts)} for query, teacher in teachers.items()})

    def no_new_branch(*args, **kwargs):
        pytest.fail("A paid retained branch must not be executed again")

    monkeypatch.setattr(teacher_helpers, "finish_teachers", finish_teachers)
    monkeypatch.setattr(runner.parent.prior.old, "run_forced_branch", no_new_branch)
    result = runner.physical_lifecycle(
        {"life": 1}, "TRAIN_REPL",
        {"roots": [record], "rosters": {"TRAIN_REPL": [plan]}, "retained_branches": [row]},
        tmp_path,
    )
    assert result["physical_branches"] == 1
    assert result["environment_counts"] == paid_environment
    assert result["policy_counts"] == paid_policy
    assert result["statuses"] == {"LOST": 1}
    assert result["teacher_bank"] == {"risk1": {"counts": paid_policy}, "risk8": {"counts": {}}}
    assert bank["risk1"].counts == Counter(paid_policy)
    assert not bank["risk8"].counts
