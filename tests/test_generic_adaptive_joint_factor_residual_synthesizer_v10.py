from __future__ import annotations

import inspect

from acfqp import construction_k7_domain_registry_extension_v55 as domains_v55
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.generic_adaptive_joint_factor_residual_synthesizer_v10 import (
    adaptive_stop_update_v10,
    exact_candidate_replay_v10,
    synthesize_adaptive_joint_candidate_v10,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.joint_factor_residual_campaign_core_v54r1 import _interface, _observe
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
_LIBRARY = {
    "factor_library_id": "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162",
    "cross_schema_subprograms": [
        {
            "signature_sha256": signature,
            "source_schema_pairs": [[7, 5], [9, 6]],
        }
        for signature in (
            "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
        )
    ],
}
_GENERIC_DOMAINS = {
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
}


def _candidate():
    kernel, _ = generate_stochastic_balanced_batch_refinement(
        stage_count=6, unit_base=3, seed=558_101
    )
    catalogue, encode = _interface(558_101, kernel, _TOKENS)
    rows, labels, _ = _observe(0, kernel, catalogue, encode)
    candidate = synthesize_adaptive_joint_candidate_v10(
        rows,
        catalogue,
        _LIBRARY,
        support_label_count=labels,
        generic_domains=_GENERIC_DOMAINS,
        candidate_domain=(
            domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_CANDIDATE_V55_DOMAIN
        ),
        candidate_content_id=domains_v55.extension_content_id_v55,
        minimum_reusable_factor_count=3,
    )
    return candidate, rows, catalogue


def test_adaptive_candidate_has_no_scaffold_or_target_slot_input():
    parameters = inspect.signature(
        synthesize_adaptive_joint_candidate_v10
    ).parameters
    assert "scaffold_program" not in parameters
    assert "factor_slots" not in parameters
    assert "target_program" not in parameters
    candidate, rows, catalogue = _candidate()
    document = candidate.public_document
    assert document["factorable_reusable_count"] == 3
    assert document["factorable_novel_count"] == 1
    assert document["residual_schema_bound_count"] == 2
    assert document["shared_residual_scaffold_consumed"] is False
    assert document["predeclared_reusable_factor_slots_consumed"] is False
    assert exact_candidate_replay_v10(candidate, rows, catalogue)["exact"] is True


def test_only_factor_prior_initial_weight_changes_the_common_stopping_formula():
    candidate, _, _ = _candidate()
    common = {
        "confirmation_block_size": 4,
        "factor_prior_weight": 64,
        "exact_likelihood_block_weight": 64,
        "stopping_weight": 64,
        "minimum_reusable_factor_count": 3,
    }
    prior = adaptive_stop_update_v10(
        candidate,
        factor_prior_enabled=True,
        confirming_support_labels=0,
        **common,
    )
    no_prior = adaptive_stop_update_v10(
        candidate,
        factor_prior_enabled=False,
        confirming_support_labels=0,
        **common,
    )
    confirmed = adaptive_stop_update_v10(
        candidate,
        factor_prior_enabled=False,
        confirming_support_labels=4,
        **common,
    )
    assert prior["stopped"] is True
    assert no_prior["stopped"] is False
    assert confirmed["stopped"] is True
    assert prior["only_switched_variable"] == no_prior["only_switched_variable"]


def test_exact_replay_rejects_a_changed_successor_support():
    candidate, rows, catalogue = _candidate()
    first = rows[0]
    changed = FlatRawTransitionV4(
        first.occurrence,
        first.index,
        first.pre,
        first.legal_before,
        first.action,
        (first.post[0] + 101, *first.post[1:]),
        first.legal_after,
        first.terminal_acceptance_after,
        first.outcome_tape_sha256,
    )
    replay = exact_candidate_replay_v10(
        candidate, (changed, *rows[1:]), catalogue
    )
    assert replay["exact"] is False
    assert replay["support_mismatch_count"] >= 1
