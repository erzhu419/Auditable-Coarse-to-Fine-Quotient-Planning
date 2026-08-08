from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_lifecycle_output_leaf_join_v1 as join_v1
from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ANCHOR_ID = "4a4b0d1888f0ac18123e4163e1a26b0583a64946d2eb219e02d4b77dc0a3e327"


@pytest.fixture(scope="module")
def anchored_bundle():
    return dispatch_v1.freeze_h1_anchored_lifecycle_dispatch_bundle_v1(
        REPOSITORY_ROOT,
        expected_anchor_id=EXPECTED_ANCHOR_ID,
    )


@pytest.fixture(scope="module")
def leaf_join(anchored_bundle):
    return join_v1.build_h1_lifecycle_output_leaf_join_v1(anchored_bundle)


def _resign(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("h1_lifecycle_output_leaf_join_id", None)
    payload["h1_lifecycle_output_leaf_join_id"] = content_id(
        join_v1.OUTPUT_LEAF_JOIN_DOMAIN,
        payload,
    )
    return canonical_json_bytes(payload)


def test_exact_90_rows_16_presence_sets_and_readback_partition(leaf_join) -> None:
    document = leaf_join.to_document()
    roles = tuple(output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES)
    expected_sites = tuple(f"readback:output-role:{role}" for role in roles)

    assert document["context_count"] == 10
    assert document["terminal_leaf_count"] == 90
    assert document["role_presence_set_count"] == 16
    assert len(document["leaf_rows"]) == 90
    assert len({row["branch_key"] for row in document["leaf_rows"]}) == 90
    assert len({tuple(row["present_roles"]) for row in document["leaf_rows"]}) == 16
    assert [row["ordinal"] for row in document["lifecycle_output_role_readback_sites"]] == list(
        range(53, 61)
    )
    assert tuple(
        row["site_key"] for row in document["lifecycle_output_role_readback_sites"]
    ) == expected_sites

    for row in document["leaf_rows"]:
        assert tuple(role for role in roles if role in row["present_roles"]) == tuple(
            row["present_roles"]
        )
        assert tuple(role for role in roles if role not in row["present_roles"]) == tuple(
            row["absent_roles"]
        )
        selected = tuple(row["selected_readback_site_keys"])
        skipped = tuple(
            item["lifecycle_output_role_readback_site_key"]
            for item in row["skipped_readback_sites"]
        )
        assert selected == tuple(
            f"readback:output-role:{role}" for role in row["present_roles"]
        )
        assert skipped == tuple(
            f"readback:output-role:{role}" for role in row["absent_roles"]
        )
        assert set(selected).isdisjoint(skipped)
        assert set(selected) | set(skipped) == set(expected_sites)
        assert row["selected_readback_site_count"] + row[
            "skipped_readback_site_count"
        ] == 8
        assert all(
            item["kind"] == "SKIPPED_NOT_APPLICABLE"
            and item["reason"] == "ROLE_ABSENT_IN_REGISTERED_OUTPUT_LEAF"
            for item in row["skipped_readback_sites"]
        )


def test_critical_presence_and_finalization_leaves(leaf_join) -> None:
    rows = {row["branch_key"]: row for row in leaf_join.to_document()["leaf_rows"]}

    post_p0 = rows["EXACT_INFEASIBLE_P0_OUTPUT_COMMIT_FAILURE"]
    pre_p0 = rows["PROTOCOL_PRE_BUSINESS_P0_OUTPUT_COMMIT_FAILURE"]
    post_final = rows["EXACT_INFEASIBLE_P7_FINALIZED"]
    post_close = rows["EXACT_INFEASIBLE_P7_CLOSURE_FAILURE"]
    pre_final = rows["PROTOCOL_PRE_BUSINESS_P7_FINALIZED"]

    assert post_p0["present_roles"] == ["BUSINESS_RESULT"]
    assert pre_p0["present_roles"] == []
    assert post_final["present_roles"] == list(
        output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    )
    assert post_close["present_roles"] == post_final["present_roles"]
    assert pre_final["present_roles"] == list(output_v1.BROKER_OUTPUT_ROLE_ORDER)
    assert post_p0["ordinary_output_finalize_site_reached_by_leaf"] is False
    assert pre_p0["ordinary_output_finalize_site_reached_by_leaf"] is False
    assert post_final["ordinary_output_finalize_site_reached_by_leaf"] is True
    assert post_close["ordinary_output_finalize_site_reached_by_leaf"] is True
    assert all(row["output_owner_close_obligation_present"] for row in rows.values())
    assert post_final["effective_terminal_class"] == "INFEASIBILITY_CERTIFICATE"
    assert post_close["effective_terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"


def test_candidate_join_keeps_all_authority_and_gate_locks(leaf_join) -> None:
    document = leaf_join.to_document()
    assert document["registered_role_presence_readback_join_complete"] is True
    assert document["each_present_role_maps_to_one_readback_site"] is True
    assert document["each_absent_role_has_one_typed_skip"] is True
    assert document["output_terminal_context_join_complete"] is False
    assert document["production_output_leaf_authority_present"] is False
    assert document["production_output_commit_evidence_present"] is False
    assert document["production_output_readback_evidence_present"] is False
    assert document["conditional_absent_role_skip_dispatch_semantics_present"] is False
    assert document["production_lifecycle_source_authority_present"] is False
    assert document["production_live_hooks_complete"] is False
    assert document["current_access_atomic_bridge_present"] is False
    assert document["joint_output_read_fixed_point_present"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["workload_economics_gate_status"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["sample_efficiency_gate_status"] == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    assert all(
        row["production_output_leaf_authority_present"] is False
        and row["durable_role_commit_observed"] is False
        and row["native_readback_observed"] is False
        for row in document["leaf_rows"]
    )


def test_join_binds_every_available_anchored_and_output_identity(
    anchored_bundle, leaf_join
) -> None:
    document = leaf_join.to_document()
    program = anchored_bundle.program
    dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
    universe = (
        output_v1.registered_h1_production_output_serializer_universe_candidate_v1()
    )
    assert document["h1_lifecycle_local_main_anchor_id"] == program.anchor_id
    assert document["h1_caller_pinned_lifecycle_provenance_id"] == (
        program.provenance_id
    )
    assert document["lifecycle_program_snapshot_id"] == program.snapshot_id
    assert document["lifecycle_program_id"] == program.program_id
    assert document["lifecycle_branch_analysis_id"] == program.branch_analysis_id
    assert document["h1_anchored_lifecycle_program_id"] == (
        program.anchored_program_id
    )
    assert document["h1_anchored_lifecycle_handler_registry_id"] == (
        anchored_bundle.registry.registry_id
    )
    assert document["h1_production_lifecycle_source_manifest_id"] == (
        program.source_manifest_id
    )
    assert document["h1_execution_topology_profile_id"] == (
        program.execution_topology_profile_id
    )
    assert document["h1_production_output_branch_dag_id"] == dag.dag_id
    assert document["h1_production_output_serializer_universe_id"] == (
        universe.universe_id
    )


def test_canonical_replay_and_resigned_tamper_attacks(anchored_bundle, leaf_join) -> None:
    verified = join_v1.verify_h1_lifecycle_output_leaf_join_bytes_v1(
        leaf_join.canonical_bytes,
        bundle=anchored_bundle,
    )
    assert verified.join_id == leaf_join.join_id
    assert canonical_json_bytes(loads_canonical_json(leaf_join.canonical_bytes)) == (
        leaf_join.canonical_bytes
    )

    attacks = []
    deleted = leaf_join.to_document()
    del deleted["leaf_rows"][0]
    deleted["terminal_leaf_count"] = 89
    attacks.append(deleted)

    duplicate = leaf_join.to_document()
    duplicate["leaf_rows"][1] = copy.deepcopy(duplicate["leaf_rows"][0])
    attacks.append(duplicate)

    crossed_role = leaf_join.to_document()
    crossed_role["leaf_rows"][0]["selected_readback_site_keys"][0] = (
        "readback:output-role:OUTPUT_MANIFEST"
    )
    attacks.append(crossed_role)

    crossed_identity = leaf_join.to_document()
    crossed_identity["h1_production_output_serializer_universe_id"] = crossed_identity[
        "h1_production_output_branch_dag_id"
    ]
    attacks.append(crossed_identity)

    forged_authority = leaf_join.to_document()
    forged_authority["production_output_leaf_authority_present"] = True
    attacks.append(forged_authority)

    for attack in attacks:
        with pytest.raises(ValueError, match="independently derived"):
            join_v1.verify_h1_lifecycle_output_leaf_join_bytes_v1(
                _resign(attack),
                bundle=anchored_bundle,
            )

    with pytest.raises(ValueError, match="canonical JSON"):
        join_v1.verify_h1_lifecycle_output_leaf_join_bytes_v1(
            leaf_join.canonical_bytes + b"\n",
            bundle=anchored_bundle,
        )


def test_join_objects_are_not_caller_mintable(leaf_join) -> None:
    with pytest.raises(ValueError, match="verifier-issued"):
        join_v1.H1LifecycleOutputLeafJoinRowV1(object(), canonical_json_bytes({}))
    with pytest.raises(ValueError, match="verifier-issued"):
        join_v1.H1LifecycleOutputLeafJoinV1(
            object(),
            *([leaf_join.join_id] * 11),
            (),
        )
