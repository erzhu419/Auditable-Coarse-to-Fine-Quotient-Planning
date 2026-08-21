"""Producer-free verification of the frozen V91r2 source-Gate result."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    freeze_role_free_relational_template_library_v70,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_occurrence_balanced_compiler_ready_acquisition_v66 import (
    run_occurrence_balanced_compiler_ready_acquisition_v66,
)
from acfqp.generic_occurrence_balanced_model_compiler_v66 import (
    compile_occurrence_balanced_model_v66,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_reference_aligned_source_pool_v65 import (
    _actions,
    _layout,
    _rows,
    pool_reference_aligned_source_evidence_v65,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "3a3d634361c16438ce9fe74f961a0c57f31f8476e8118869531fe849f68b42a6"
CAMPAIGN_BYTE_COUNT = 473_436
CAMPAIGN_SHA256 = "c85f2c701bd7de569a0539194e8b36f728dae54a9af5949178b2f107b991e85f"
PREREGISTRATION_ID = "57ed9c74fb7944ffa6f21dc4450cb45d5299e81424b8229ac8055282b161e7b9"
FAILED_V91R1_ID = "6c076b761b7b2b9e68a0ac49a7f7b8ae1accb43e2b140486b1c268eb23b179c6"
LAYOUT_DOMAIN = "acfqp:construction-k7-joint-factor-residual-layout:v54"
VERIFICATION_ID = (
    "1cc119b9d67a29ea439970208bdd41780038a3c4f8eba02f0a650f30fbcd7895"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_554
EXPECTED_CANONICAL_SHA256 = (
    "e59a3cad57c3fcb2616e95e393aa20f54f7e2ad55848ac3ec328a611ceded064"
)


class ConstructionK7PriorOnlyOccurrenceSourceIndependentVerifierV91R2Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PriorOnlyOccurrenceSourceIndependentVerifierV91R2Error(
        message
    )


def _candidate(member: dict[str, Any]) -> PartialFactorCandidateV15:
    acquisition = member.get("common_partial_acquisition")
    document = acquisition.get("candidate") if type(acquisition) is dict else None
    if type(document) is not dict:
        _fail("V91r2 retained partial candidate changed")
    layout = _layout(document.get("layout"))
    actions = _actions(member.get("action_catalogue"))
    evidence = member.get("source_evidence")
    if type(evidence) is not dict:
        _fail("V91r2 retained source evidence changed")
    rows = _rows(evidence.get("common_partial_raw_transition_rows"), actions)
    count = document.get("raw_transition_count_at_issuance")
    assignments = document.get("compiled_factor_assignments")
    if (
        type(count) is not int
        or not 0 < count <= len(rows)
        or type(assignments) is not list
    ):
        _fail("V91r2 retained partial issuance changed")
    aligned, _catalogue = align_generic_occurrence_v5(
        rows[:count], actions, layout, canonical_occurrence=0
    )
    return PartialFactorCandidateV15(
        document, layout, tuple(assignments), aligned
    )


def verify_prior_only_occurrence_source_campaign_bytes_v91r2(raw: bytes) -> bytes:
    if (
        type(raw) is not bytes
        or len(raw) != CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != CAMPAIGN_SHA256
    ):
        _fail("V91r2 frozen campaign bytes changed")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V91r2 frozen campaign canonical bytes changed")
    payload = {
        key: value for key, value in document.items() if key != "campaign_id"
    }
    if (
        document.get("campaign_id") != CAMPAIGN_ID
        or domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_CAMPAIGN_V91R2_DOMAIN,
            payload,
        )
        != CAMPAIGN_ID
        or document.get("preregistration_id") != PREREGISTRATION_ID
        or document.get("failed_v91r1_id") != FAILED_V91R1_ID
    ):
        _fail("V91r2 frozen campaign identity join changed")
    members = document.get("source_members")
    if type(members) is not list or len(members) != 2:
        _fail("V91r2 source member inventory changed")
    for member in members:
        partial = member.get("common_partial_acquisition")
        if (
            type(partial) is not dict
            or partial.get("strict_no_prior_arm_executed") is not False
            or partial.get("matched_sample_tax_comparison_claimed") is not False
            or member.get("strict_no_prior_arm_executed_for_source_member")
            is not False
        ):
            _fail("V91r2 prior-only source boundary changed")
        partial_payload = {
            key: value
            for key, value in partial.items()
            if key != "acquisition_id"
        }
        if domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PARTIAL_ACQUISITION_V91R2_DOMAIN,
            partial_payload,
        ) != partial.get("acquisition_id"):
            _fail("V91r2 prior-only acquisition identity changed")
    replay_pool = pool_reference_aligned_source_evidence_v65(
        [
            {
                "member_id": row["member_id"],
                "common_partial_acquisition": row["common_partial_acquisition"],
                "source_evidence": row["source_evidence"],
                "action_catalogue": row["action_catalogue"],
            }
            for row in members
        ],
        layout_domain=LAYOUT_DOMAIN,
    )
    if replay_pool != document.get("reference_aligned_source_pool"):
        _fail("V91r2 reference-aligned source pool reconstruction diverged")
    template = freeze_role_free_relational_template_library_v70().to_document()[
        "compiled_template_library"
    ]
    replay_acquisition = run_occurrence_balanced_compiler_ready_acquisition_v66(
        replay_pool["canonical_source_pool"],
        role_free_template_library=template,
        maximum_exact_instantiations=8,
        confidence_denominator=4096,
    )
    if replay_acquisition != document.get(
        "occurrence_balanced_compiler_ready_acquisition"
    ):
        _fail("V91r2 occurrence-balanced acquisition reconstruction diverged")
    reference = next(
        row
        for row in members
        if row["member_id"] == replay_pool["reference_member_id"]
    )
    replay_model = compile_occurrence_balanced_model_v66(
        _candidate(reference),
        replay_pool["canonical_source_pool"],
        replay_acquisition,
    )
    if replay_model != document.get("reusable_joint_successor_version_space_model"):
        _fail("V91r2 joint successor model reconstruction diverged")
    clean = all(
        row["source_complete_episode"]["predecessor_v30_episode"]["success"]
        is True
        and row["source_complete_episode"]["predecessor_v30_episode"][
            "all_ground_queries_followed_failed_certificates"
        ]
        is True
        and row["source_complete_episode"]["predecessor_v30_episode"][
            "query_local_exact_overlay_exclusively_used_for_safety"
        ]
        is True
        for row in members
    )
    gate = document.get("registered_gate")
    if (
        clean is not True
        or type(gate) is not dict
        or gate.get("compiler_ready_heldout_validated") is not True
        or gate.get("joint_successor_model_compiled") is not True
        or gate.get("every_batch_exact_residual_expression_retained") is not True
        or gate.get("multiple_residual_proposals_jointly_compiled") is not False
        or gate.get("passed") is not False
        or replay_model.get("multiple_residual_proposals_jointly_compiled")
        is not False
        or document.get("status")
        != "PRIOR_ONLY_OCCURRENCE_MODEL_COMPILED_NO_TARGET_EXECUTION"
        or document.get("target_execution_performed") is not False
        or document.get("complete_world_model_synthesized") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("official_scalar_cost") is not None
        or document.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or document.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V91r2 Gate result or claim boundary changed")
    verification_payload = {
        "schema": "acfqp.prior_only_occurrence_source_independent_verification.v91r2",
        "campaign_id": CAMPAIGN_ID,
        "campaign_byte_count": CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": CAMPAIGN_SHA256,
        "preregistration_id": PREREGISTRATION_ID,
        "failed_v91r1_id": FAILED_V91R1_ID,
        "source_member_ids": [row["member_id"] for row in members],
        "reference_aligned_source_pool_id": replay_pool[
            "reference_aligned_source_pool_id"
        ],
        "occurrence_balanced_acquisition_id": replay_acquisition[
            "occurrence_balanced_compiler_ready_acquisition_id"
        ],
        "joint_successor_model_id": replay_model[
            "joint_successor_version_space_model_id"
        ],
        "producer_free_pool_reconstruction": True,
        "producer_free_acquisition_reconstruction": True,
        "producer_free_model_reconstruction": True,
        "source_certificate_discipline_verified": True,
        "irrelevant_strict_source_arm_absence_verified": True,
        "single_residual_proposal_gate_failure_verified": True,
        "typed_result": "SOURCE_MODEL_COMPILED_MULTIPLICITY_GATE_FAILURE_VERIFIED",
        "fresh_target_outcome_count": 0,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_VERIFICATION_V91R2_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r2 verification changed")
    return result


__all__ = (
    "VERIFICATION_ID",
    "verify_prior_only_occurrence_source_campaign_bytes_v91r2",
)
