from __future__ import annotations

import inspect

from acfqp import construction_k7_domain_registry_extension_v56 as domains
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    exact_candidate_replay_v11,
    mdl_confidence_stop_update_v11,
    synthesize_mdl_adaptive_joint_candidate_v11,
)
from acfqp.joint_factor_residual_campaign_core_v54r1 import _interface, _observe
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
)


_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
_LIBRARY = {
    "factor_library_id": (
        "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
    ),
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
        stage_count=6, unit_base=3, seed=568_101
    )
    catalogue, encode = _interface(568_101, kernel, _TOKENS)
    rows, labels, _ = _observe(0, kernel, catalogue, encode)
    candidate = synthesize_mdl_adaptive_joint_candidate_v11(
        rows,
        catalogue,
        _LIBRARY,
        support_label_count=labels,
        generic_domains=_GENERIC_DOMAINS,
        candidate_domain=domains.CONSTRUCTION_K7_MDL_ADAPTIVE_CANDIDATE_V56_DOMAIN,
        candidate_content_id=domains.extension_content_id_v56,
        minimum_reusable_factor_count=3,
    )
    return candidate, rows, catalogue


def test_v11_has_no_minimum_label_or_confirmation_block_input():
    synthesis_parameters = inspect.signature(
        synthesize_mdl_adaptive_joint_candidate_v11
    ).parameters
    stop_parameters = inspect.signature(mdl_confidence_stop_update_v11).parameters
    assert "minimum_candidate_labels" not in synthesis_parameters
    assert "minimum_candidate_labels" not in stop_parameters
    assert "confirmation_block_size" not in stop_parameters
    candidate, rows, catalogue = _candidate()
    assert candidate.public_document["minimum_label_floor_consumed"] is False
    assert candidate.public_document["confirmation_block_consumed"] is False
    assert exact_candidate_replay_v11(candidate, rows, catalogue)["exact"] is True


def test_v11_same_integer_mdl_formula_switches_only_factor_code_credit():
    candidate, rows, catalogue = _candidate()
    common = {
        "invalidated_candidate_count": 0,
        "candidate_program_disagreement_count": 0,
        "factor_signature_credit_units": 16,
        "confidence_reserve_units": 48,
        "invalidated_candidate_penalty_units": 16,
        "minimum_reusable_factor_count": 3,
    }
    prior = mdl_confidence_stop_update_v11(
        candidate,
        rows,
        catalogue,
        factor_prior_enabled=True,
        **common,
    )
    no_prior = mdl_confidence_stop_update_v11(
        candidate,
        rows,
        catalogue,
        factor_prior_enabled=False,
        **common,
    )
    assert prior["registered_factor_code_credit_units"] == 48
    assert no_prior["registered_factor_code_credit_units"] == 0
    assert prior["confidence_margin_units"] == (
        no_prior["confidence_margin_units"] + 48
    )
    assert prior["same_integer_mdl_formula_in_both_arms"] is True
    assert prior["only_switched_variable"] == (
        "REGISTERED_FACTOR_CODE_CREDIT_UNITS"
    )
    assert prior["statistical_confidence_interval_claimed"] is False
