from __future__ import annotations

from dataclasses import dataclass
import hashlib

import pytest

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as v57
from acfqp import construction_k7_domain_registry_extension_v58 as domains_v58
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_joint_successor_version_space_planner_v42 import (
    compile_joint_successor_version_space_model_v42,
)
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    run_relation_covering_learned_successor_acquisition_v41,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    GenericReusableVersionSpaceCertificatePlannerV43Error,
    run_matched_reusable_version_space_ablation_v43,
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.generic_role_free_relational_template_v33 import (
    compile_role_free_relational_template_library_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes


def _source_fixture():
    catalogue = (
        FlatRawActionV4(0, (1, 2)),
        FlatRawActionV4(1, (2, 3)),
    )
    rows = []
    for position, delta, key in (
        (0, 1, 0),
        (0, 2, 1),
        (1, 1, 0),
        (1, 2, 1),
        (2, 1, 0),
        (2, 2, 1),
        (3, 1, 0),
        (3, 2, 1),
    ):
        pre = (position, 4, 10 + position, 4)
        next_position = position + delta
        terminal = next_position >= 4
        legal_after = () if terminal else (0, 1)
        for residual in (pre[2], pre[2] + delta + 1):
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    pre,
                    (0, 1),
                    catalogue[key],
                    (next_position, 4, residual, 9 if terminal else 4),
                    legal_after,
                    True if terminal else None,
                )
            )
    candidate_rows = [*rows]
    candidate_rows.append(
        FlatRawTransitionV4(
            0,
            len(candidate_rows),
            (0, 4, 10, 4),
            (0, 1),
            catalogue[0],
            (1, 4, 109, 4),
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
        candidate_domain=(
            domains_v58.CONSTRUCTION_K7_UNIVERSAL_MIXTURE_ACQUISITION_V58_DOMAIN
        ),
        candidate_content_id=domains_v58.extension_content_id_v58,
        minimum_factor_assignment_count=2,
    )
    tree = {
        "kind": "RELATION",
        "opcode": "GE",
        "left_column": 3,
        "right_column": 2,
        "when_true": {
            "kind": "LEAF",
            "terminal_class": "ACCEPT",
            "status_token": 9,
        },
        "when_false": {
            "kind": "LEAF",
            "terminal_class": "ACTIVE",
            "status_token": 4,
        },
    }
    encoded = canonical_json_bytes(tree)
    source_program = {
        "schema": "acfqp.generic_relational_terminal_program.v28",
        "terminal_program_id": hashlib.sha256(encoded).hexdigest(),
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
    library = compile_role_free_relational_template_library_v33((source_program,))
    evidence = {
        "layout": candidate.public_document["layout"],
        "unknown_residual_target_columns": candidate.public_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": [row.to_document() for row in rows],
    }
    acquisition = run_relation_covering_learned_successor_acquisition_v41(
        evidence,
        role_free_template_library=library,
        successor_prior_library=None,
        required_terminal_classes=("ACCEPT", "ACTIVE"),
        confidence_denominator=2,
        successor_confidence_denominator=2,
    )
    model = compile_joint_successor_version_space_model_v42(
        candidate, evidence, acquisition
    )
    return candidate, tuple(candidate_rows), catalogue, model


@dataclass(frozen=True)
class _Outcome:
    next_state: tuple[int, ...]


class _Kernel:
    def step(self, state, action):
        delta = action.fields[0]
        next_position = state[0] + delta
        terminal = next_position >= state[1]
        return tuple(
            _Outcome(
                (
                    next_position,
                    state[1],
                    residual,
                    9 if terminal else 4,
                )
            )
            for residual in (state[2], state[2] + delta + 1)
        )


class _Adapter:
    family = "ANONYMOUS_TWO_SUPPORT_PROGRESS"
    seed = 430_001

    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.kernel = _Kernel()

    def initial(self):
        return (0, 4, 10, 4)

    def encode(self, state):
        return state

    def action(self, key):
        return next(row for row in self.catalogue if row.key == key)

    def action_key(self, action):
        return action.key

    def actions(self, state):
        return self.catalogue if self.active(state) else ()

    def active(self, state):
        return state[3] == 4

    def success(self, state):
        return state[3] == 9

    def select_outcome(self, state, key, episode_index, decision):
        outcomes = self.kernel.step(state, self.action(key))
        offset = (episode_index + decision) % len(outcomes)
        tape = hashlib.sha256(
            canonical_json_bytes(
                {
                    "state": list(state),
                    "key": key,
                    "episode_index": episode_index,
                    "decision": decision,
                    "offset": offset,
                }
            )
        ).hexdigest()
        return outcomes[offset], tape


def test_v43_rejects_same_source_and_target_episode_identity():
    candidate, rows, catalogue, model = _source_fixture()
    with pytest.raises(GenericReusableVersionSpaceCertificatePlannerV43Error):
        run_reusable_version_space_certificate_episode_v43(
            _Adapter(catalogue),
            candidate,
            rows,
            reusable_model=model,
            model_source_episode_index=0,
            episode_index=0,
            maximum_abstract_depth=2,
            maximum_execution_steps=8,
        )


def test_v43_reusable_model_reduces_actual_certificate_local_queries():
    candidate, rows, catalogue, model = _source_fixture()
    result = run_matched_reusable_version_space_ablation_v43(
        _Adapter(catalogue),
        candidate,
        rows,
        model,
        model_source_episode_index=0,
        episode_index=1,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    derived = result["arms"]["REUSABLE_JOINT_VERSION_SPACE_MODEL"]
    strict = result["arms"]["STRICT_NO_REUSABLE_MODEL"]
    assert derived["success"] is strict["success"] is True
    assert derived["abstract_plan_success_count"] > 0
    assert strict["abstract_plan_attempt_count"] == 0
    assert result["actual_target_sample_reduction_observed"] is True
    assert result["derived_target_certificate_local_ground_support_labels"] < result[
        "strict_target_certificate_local_ground_support_labels"
    ]
    for arm in (derived, strict):
        assert arm["all_ground_queries_followed_failed_certificates"] is True
        assert arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        assert arm["reusable_abstract_model_used_as_safety_authority"] is False
        assert len(arm["failed_certificates"]) == len(arm["local_distinctions"])
    assert result["only_reusable_model_availability_differs_between_arms"] is True
    assert result["offline_source_labels_and_target_labels_separate"] is True
    assert result["official_execution_allowed"] is False
    assert result["official_scalar_cost"] is None
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
