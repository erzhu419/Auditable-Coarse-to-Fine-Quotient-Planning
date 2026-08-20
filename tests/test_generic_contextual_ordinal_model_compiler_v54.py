from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_contextual_ordinal_model_compiler_v54 import (
    GenericContextualOrdinalModelCompilerV54Error,
    compile_contextual_ordinal_model_v54,
    verify_contextual_ordinal_model_v54,
)
from acfqp.generic_contextual_ordinal_residual_v54 import version_space_v54
from acfqp.generic_contextual_ordinal_planner_v54 import (
    plan_contextual_ordinal_model_v54,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.phase3e_ids import canonical_json_bytes


_ACQ_DOMAIN = b"acfqp:generic-contextual-ordinal-frontier-acquisition:v54\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-contextual-ordinal-frontier-acquisition:v54\x00"


def _fixture():
    catalogue = (
        FlatRawActionV4(0, (17, 1)),
        FlatRawActionV4(1, (43, 1)),
    )
    rows = []
    for index, (stage, key) in enumerate(
        ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1))
    ):
        delta = key + 1
        successor = stage + delta
        terminal = successor >= 4
        rows.append(
            FlatRawTransitionV4(
                0,
                index,
                (stage, 4, 9, 4),
                (0, 1),
                catalogue[key],
                (successor, 4, 9, 8 if terminal else 4),
                () if terminal else (0, 1),
                True if terminal else None,
            )
        )
    candidate_rows = list(rows)
    candidate_rows.append(
        FlatRawTransitionV4(
            0,
            len(candidate_rows),
            (0, 4, 9, 4),
            (0, 1),
            catalogue[0],
            (99, 4, 9, 4),
            (0, 1),
            None,
        )
    )
    config = v57.campaign_config_v57()
    candidate = synthesize_partial_factor_candidate_v15(
        tuple(candidate_rows),
        catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=8,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN,
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=2,
    )
    layout = candidate.public_document["layout"]
    state_order = layout["state_canonical_to_raw"]
    raw_to_canonical = {raw: canonical for canonical, raw in enumerate(state_order)}
    stage_target = raw_to_canonical[0]
    goal_target = raw_to_canonical[1]
    status_target = raw_to_canonical[3]
    public_rows = []
    for row in rows:
        document = row.to_document()
        document["contextual_source_member_index"] = 0
        public_rows.append(document)
    evidence = {
        "layout": layout,
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": public_rows,
        "contextual_action_field_supports": [
            {
                "context_index": 0,
                "source_member_id": "c" * 64,
                "canonical_action_count": 2,
                "canonical_action_sha256": hashlib.sha256(
                    canonical_json_bytes(
                        [
                            {"action_key": action.key, "canonical_fields": [action.fields[index] for index in layout["action_canonical_to_raw"]]}
                            for action in catalogue
                        ]
                    )
                ).hexdigest(),
                "action_field_supports": [
                    sorted(
                        {
                            action.fields[raw]
                            for action in catalogue
                        }
                    )
                    for raw in layout["action_canonical_to_raw"]
                ],
            }
        ],
        "contextual_action_supports_derived_from_catalogue_only": True,
        "unacquired_successor_or_terminal_used_for_action_supports": False,
        "contextual_action_support_projection_id": "d" * 64,
    }
    tree = {
        "kind": "RELATION",
        "opcode": "GE",
        "left_column": stage_target,
        "right_column": goal_target,
        "when_true": {"kind": "LEAF", "terminal_class": "ACCEPT", "status_token": 8},
        "when_false": {"kind": "LEAF", "terminal_class": "ACTIVE", "status_token": 4},
    }
    encoded = canonical_json_bytes(tree)
    program_payload = {
        "schema": "acfqp.generic_relational_terminal_program.v28",
        "status_target_column": status_target,
        "decision_tree_candidate_frontier": [
            {
                "candidate_index": 0,
                "decision_tree_node_count": 3,
                "decision_tree_byte_count": len(encoded),
                "decision_tree_sha256": hashlib.sha256(encoded).hexdigest(),
                "decision_tree": tree,
            }
        ],
        "empirical_program_only": True,
        "future_unseen_terminal_authority_present": False,
    }
    program = {
        **program_payload,
        "terminal_program_id": hashlib.sha256(
            b"test-terminal\x00" + canonical_json_bytes(program_payload)
        ).hexdigest(),
    }
    schedule = schedule_relation_covering_queries_v39(evidence)
    groups = []
    grouped = {}
    for row in schedule["scheduled_raw_transition_rows"]:
        identity = (tuple(row["pre_vector"]), row["selected_action"]["action_key"])
        if identity not in grouped:
            grouped[identity] = []
            groups.append(grouped[identity])
        grouped[identity].append(row)
    stop = len(groups) - 2
    frontier, _ = version_space_v54(evidence, groups[:stop], stage_target)
    spaces = [
        {
            "target_column": stage_target,
            "batch_exact_candidate_count": len(frontier),
            "batch_exact_candidate_frontier": frontier,
        }
    ]
    acquisition_payload = {
        "schema": "acfqp.generic_contextual_ordinal_frontier_acquisition.v54",
        "status": "PROPOSAL_ISSUED_HELDOUT_VALIDATED",
        "heldout_exact_prediction": True,
        "heldout_rows_accessed_before_stop": False,
        "every_retained_terminal_frontier_candidate_prequentially_checked": True,
        "every_retained_residual_frontier_candidate_prequentially_checked": True,
        "every_retained_terminal_frontier_candidate_heldout_checked": True,
        "every_retained_residual_frontier_candidate_heldout_checked": True,
        "proposal_only_not_safety_authority": True,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": program,
        "selected_terminal_program_id": program["terminal_program_id"],
        "selected_residual_version_spaces": spaces,
    }
    acquisition = {
        **acquisition_payload,
        "contextual_ordinal_frontier_acquisition_id": hashlib.sha256(
            _ACQ_DOMAIN + canonical_json_bytes(acquisition_payload)
        ).hexdigest(),
    }
    bundle_payload = {
        "schema": "acfqp.relation_covering_contextual_ordinal_frontier_acquisition.v54",
        "query_schedule": schedule,
        "contextual_ordinal_frontier_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "contextual_ordinal_frontier_acquisition_id": acquisition[
            "contextual_ordinal_frontier_acquisition_id"
        ],
    }
    bundle = {
        **bundle_payload,
        "relation_covering_contextual_ordinal_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(bundle_payload)
        ).hexdigest(),
    }
    return candidate, catalogue, evidence, bundle


def test_v54_compiles_and_reconstructs_contextual_ordinal_model():
    candidate, catalogue, evidence, bundle = _fixture()
    model = compile_contextual_ordinal_model_v54(candidate, evidence, bundle)
    verified = verify_contextual_ordinal_model_v54(model)
    assert verified["contextual_ordinal_action_support_operator_present"] is True
    assert verified["every_batch_exact_residual_expression_retained"] is True
    assert verified["all_state_coordinates_represented"] is True
    assert verified["complete_world_model_claimed"] is False
    assert verified["abstract_plan_safety_authority_present"] is False
    plan = plan_contextual_ordinal_model_v54(
        model,
        candidate,
        catalogue,
        (0, 4, 9, 4),
        maximum_depth=4,
    )
    assert plan["initial_action_key"] in (0, 1)
    assert plan["contextual_target_action_supports_derived_without_ground_successors"] is True
    assert plan["all_residual_version_spaces_jointly_propagated"] is True
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["abstract_plan_used_as_safety_authority"] is False


def test_v54_model_rejects_claim_flip():
    candidate, _catalogue, evidence, bundle = _fixture()
    model = compile_contextual_ordinal_model_v54(candidate, evidence, bundle)
    model["complete_world_model_claimed"] = True
    with pytest.raises(GenericContextualOrdinalModelCompilerV54Error):
        verify_contextual_ordinal_model_v54(model)
