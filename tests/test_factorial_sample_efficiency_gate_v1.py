from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

from acfqp.factorial_sample_efficiency_gate_v1 import (
    DIRECT_FIXED,
    DIRECT_SEQUENTIAL,
    META_PRIOR_FIXED,
    META_PRIOR_SEQUENTIAL,
    NO_PRIOR_FIXED,
    NO_PRIOR_SEQUENTIAL,
    REGISTERED_ARMS,
    REGISTERED_FAMILY_TAIL_UPPER,
    REGISTERED_GRAPH_CONTEXTS,
    ConfidenceFamily,
    ConfidenceContractV1,
    EvidenceEventVectorV1,
    FactorialSampleEfficiencyInvariantViolation,
    FactorialSampleEfficiencyPreregistrationV1,
    GraphOccurrenceArmResultV1,
    OccurrenceSampleWorkV1,
    PlannerKind,
    ProposalMode,
    SourcePriorGateEvidenceV1,
    TargetSequentialOperatorInstantiationV1,
    TerminalClass,
    adapt_direct_sequential_result_v1,
    build_registered_graph_occurrences_v1,
    evaluate_factorial_sample_efficiency_gate_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _source_prior(offline_draws: int = 100_000_000) -> SourcePriorGateEvidenceV1:
    return SourcePriorGateEvidenceV1(
        _id("source-prior"),
        tuple(sorted((_id("source-a"), _id("source-b")))),
        tuple(sorted(item.context_id for item in REGISTERED_GRAPH_CONTEXTS)),
        EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            offline_draws,
            0,
            12,
            0,
        ),
        EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            offline_draws,
            0,
            12,
            0,
        ),
        EvidenceEventVectorV1.zero("OFFLINE_SOURCE"),
        (_id("prior-verification"),),
    )


def _operator_instantiation(
    occurrence: object,
    proposal_id: str,
) -> TargetSequentialOperatorInstantiationV1:
    from acfqp.anytime_variable_graph_runner_v1 import (
        CHECKPOINTS,
        AnytimeVariableGraphTerminal,
        anytime_variable_graph_profile_v1,
    )
    from acfqp.v0066_graph_acquisition_metaprior_v1 import (
        GraphAcquisitionOperatorKind,
        _operator_candidates,
    )

    role_schema_id = _id("synthetic-role-schema")
    semantics, candidate = next(
        (semantics, candidate)
        for semantics, candidate in _operator_candidates(role_schema_id)
        if semantics.operator_kind
        is GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER
    )
    profile = anytime_variable_graph_profile_v1()
    return TargetSequentialOperatorInstantiationV1(
        target_proposal_id=proposal_id,
        target_context_id=occurrence.context_id,
        target_query_id=occurrence.query_id,
        source_role_schema_id=role_schema_id,
        source_candidate_id=candidate.candidate_id,
        source_operator_semantics_id=semantics.semantics_id,
        target_profile_id=profile.profile_id,
        target_checkpoints=CHECKPOINTS,
        source_maximum_draws_per_row=semantics.maximum_draws_per_row,
        target_maximum_draws_per_row=profile.max_draws,
        row_schedule=semantics.row_schedule,
        stopping_rule=semantics.stopping_rule,
        confidence_method_id=semantics.confidence_method_id,
        confidence_alpha=profile.confidence_alpha,
        target_half_width=profile.target_half_width,
        cap_failure_terminal=(
            AnytimeVariableGraphTerminal
            .FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP.value
        ),
    )


def _confidence(
    arm: object,
    context_key: str,
) -> ConfidenceContractV1:
    if arm == NO_PRIOR_FIXED or arm == META_PRIOR_FIXED:
        family = ConfidenceFamily.QUOTIENT_FIXED
        obligations = 287
        authority = "quotient-fixed-family"
    elif arm == NO_PRIOR_SEQUENTIAL or arm == META_PRIOR_SEQUENTIAL:
        family = ConfidenceFamily.QUOTIENT_SEQUENTIAL
        obligations = (
            47 if context_key == "variable_target_w5_v0" else 120
        )
        authority = f"quotient-sequential:{context_key}"
    elif arm == DIRECT_FIXED:
        family = ConfidenceFamily.DIRECT_FIXED
        obligations = (
            66 if context_key == "variable_target_w5_v0" else 132
        )
        authority = f"direct-fixed:{context_key}"
    elif arm == DIRECT_SEQUENTIAL:
        family = ConfidenceFamily.DIRECT_SEQUENTIAL
        obligations = (
            66 if context_key == "variable_target_w5_v0" else 132
        )
        authority = f"direct-sequential:{context_key}"
    else:
        raise AssertionError("unknown confidence arm")
    tail = Fraction(obligations, 250_000)
    return ConfidenceContractV1(
        _id("common-claim-scope"),
        _id("common-confidence-budget"),
        _id(f"certificate-profile:{authority}"),
        family,
        obligations,
        Fraction(1, 250_000),
        tail,
        1 - tail,
        "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_IID_SIMULATOR_ASSUMPTION",
    )


def _work(
    draws: int,
    acquired_rows: int,
    negative: bool,
) -> OccurrenceSampleWorkV1:
    return OccurrenceSampleWorkV1(
        EvidenceEventVectorV1(
            "ONLINE_TARGET",
            0,
            draws,
            acquired_rows,
            0,
            0,
        ),
        EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
        EvidenceEventVectorV1(
            "OPERATIONAL_QUERY",
            0,
            0,
            60 if negative else 0,
            0,
            0,
        ),
        EvidenceEventVectorV1(
            "STANDALONE_EVALUATION",
            0,
            0,
            1,
            0,
            0,
        ),
    )


def _rows_and_draws(
    context_key: str,
    arm: object,
    *,
    quotient_w5_per_row: int,
) -> tuple[int, int]:
    context = next(
        item
        for item in REGISTERED_GRAPH_CONTEXTS
        if item.context_key == context_key
    )
    if arm == NO_PRIOR_FIXED or arm == META_PRIOR_FIXED:
        rows = context.no_prior_fixed_acquisition_rows
        return rows, rows * 131_072
    if arm == DIRECT_FIXED:
        rows = context.direct_fixed_acquisition_rows
        return rows, rows * 131_072
    if arm == NO_PRIOR_SEQUENTIAL or arm == META_PRIOR_SEQUENTIAL:
        rows = context.no_prior_fixed_acquisition_rows
        per_row = (
            quotient_w5_per_row
            if context_key == "variable_target_w5_v0"
            else (
                4_096
                if context_key == "variable_target_k6_v0"
                else 16_384
            )
        )
        return rows, rows * per_row
    if arm == DIRECT_SEQUENTIAL:
        rows = context.direct_fixed_acquisition_rows
        return rows, rows * 8_192
    raise AssertionError("unknown arm")


def _bundle(
    *,
    offline_draws: int = 100_000_000,
    quotient_w5_per_row: int = 8_192,
) -> tuple[
    FactorialSampleEfficiencyPreregistrationV1,
    SourcePriorGateEvidenceV1,
    tuple[GraphOccurrenceArmResultV1, ...],
]:
    source = _source_prior(offline_draws)
    query_ids = {
        item.context_key: _id(f"query:{item.context_key}")
        for item in REGISTERED_GRAPH_CONTEXTS
    }
    occurrences = build_registered_graph_occurrences_v1(query_ids, 1)
    preregistration = FactorialSampleEfficiencyPreregistrationV1(
        occurrences,
        REGISTERED_ARMS,
        source.gate_prior_id,
        _id("common-claim-scope"),
        _id("common-confidence-budget"),
    )
    results: list[GraphOccurrenceArmResultV1] = []
    for occurrence in occurrences:
        negative = (
            occurrence.context_key
            == "variable_negative_k6_minus_edge_v0"
        )
        arms = REGISTERED_ARMS[:4] if negative else REGISTERED_ARMS
        for arm in arms:
            rows, draws = _rows_and_draws(
                occurrence.context_key,
                arm,
                quotient_w5_per_row=quotient_w5_per_row,
            )
            is_meta = arm.proposal is ProposalMode.SOURCE_META_PRIOR
            proposal_id = (
                _id(f"source-proposal:{occurrence.occurrence_id}")
                if is_meta
                else None
            )
            failure = (
                Fraction(2277, 16000)
                if negative
                else Fraction(99, 5000)
            )
            results.append(
                GraphOccurrenceArmResultV1(
                    occurrence=occurrence,
                    arm=arm,
                    confidence=_confidence(arm, occurrence.context_key),
                    work=_work(draws, rows, negative),
                    acquired_ground_rows=rows,
                    terminal_class=TerminalClass.PLAN_CERTIFICATE,
                    certificate_id=_id(
                        f"certificate:{occurrence.occurrence_id}:{arm.arm_id}"
                    ),
                    evidence_verification_id=_id(
                        f"evidence-verification:{occurrence.occurrence_id}:"
                        f"{arm.arm_id}"
                    ),
                    exact_evaluation_id=_id(
                        f"exact-evaluation:{occurrence.occurrence_id}:"
                        f"{arm.arm_id}"
                    ),
                    access_verification_id=_id(
                        f"access-verification:{occurrence.occurrence_id}:"
                        f"{arm.arm_id}"
                    ),
                    paired_seed_stream_id=_id(
                        f"paired-seed:{occurrence.occurrence_id}"
                    ),
                    exact_failure_probability=failure,
                    exact_normalized_reward=Fraction(3, 64),
                    normalized_regret=Fraction(0),
                    audit_covers_exact_objective_constraint=True,
                    false_certificate_count=0,
                    source_prior_gate_id=(
                        source.gate_prior_id if is_meta else None
                    ),
                    source_proposal_id=(
                        proposal_id
                    ),
                    source_prior_selected_this_arm=(
                        arm == META_PRIOR_SEQUENTIAL
                    ),
                    cold_occurrence_local_model=(
                        arm.planner is PlannerKind.COLD_DIRECT_GROUND
                    ),
                    target_model_reused=False,
                    target_operator_instantiation=(
                        _operator_instantiation(
                            occurrence,
                            proposal_id,
                        )
                        if arm == META_PRIOR_SEQUENTIAL
                        else None
                    ),
                    pretrained_source_skeleton_used=(
                        arm.planner is PlannerKind.QUOTIENT_RAPM
                    ),
                )
            )
    return preregistration, source, tuple(results)


def test_target_operator_instantiation_rejects_cap_and_profile_attacks() -> None:
    _, _, rows = _bundle()
    meta = next(item for item in rows if item.arm == META_PRIOR_SEQUENTIAL)
    instantiation = meta.target_operator_instantiation
    assert type(instantiation) is TargetSequentialOperatorInstantiationV1
    assert instantiation.target_maximum_draws_per_row == 16_384
    assert instantiation.source_maximum_draws_per_row == 131_072
    assert not instantiation.exact_profile_transfer_claimed
    assert instantiation.operator_family_instantiation_only

    attacks = (
        {"target_maximum_draws_per_row": 262_144},
        {"confidence_method_id": "posthoc-method"},
        {"confidence_alpha": Fraction(1, 200_000)},
        {"target_half_width": Fraction(1, 100)},
        {"target_checkpoints": (2_048, 4_096, 8_192)},
        {"target_profile_id": _id("posthoc-profile")},
    )
    for attack in attacks:
        with pytest.raises(FactorialSampleEfficiencyInvariantViolation):
            replace(instantiation, **attack)


def test_target_operator_instantiation_presence_is_arm_typed() -> None:
    _, _, rows = _bundle()
    meta = next(item for item in rows if item.arm == META_PRIOR_SEQUENTIAL)
    fixed = next(item for item in rows if item.arm == META_PRIOR_FIXED)
    with pytest.raises(FactorialSampleEfficiencyInvariantViolation):
        replace(meta, target_operator_instantiation=None)
    with pytest.raises(FactorialSampleEfficiencyInvariantViolation):
        replace(
            fixed,
            target_operator_instantiation=meta.target_operator_instantiation,
        )


def test_positive_online_gate_passes_only_when_quotient_beats_real_direct() -> None:
    preregistration, source, results = _bundle()
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        results,
    )

    summaries = {item.arm.arm_key: item for item in result.summaries}
    assert (
        summaries[NO_PRIOR_FIXED.arm_key].acquisition_draws
        == 18_612_224
    )
    assert (
        summaries[NO_PRIOR_FIXED.arm_key].positive_certified_target_draws
        == 10_747_904
    )
    assert (
        summaries[NO_PRIOR_SEQUENTIAL.arm_key]
        .positive_certified_target_draws
        == 425_984
    )
    assert (
        summaries[DIRECT_FIXED.arm_key].positive_certified_target_draws
        == 11_796_480
    )
    assert (
        summaries[DIRECT_SEQUENTIAL.arm_key]
        .positive_certified_target_draws
        == 737_280
    )
    assert result.sequential_main_effect
    assert result.meta_selection_valid
    assert not result.meta_prior_main_effect
    assert not result.meta_prior_target_savings_claimed
    assert result.online_gate_passed
    assert result.registered_positive_target_generative_draw_efficiency
    assert result.historical_v0066_exact_fallback_detected
    assert result.offline_inclusive_break_even_occurrence is None
    assert result.offline_inclusive_status == "NOT_ESTABLISHED"
    assert not result.offline_inclusive_gate_passed
    assert not result.broad_generalization_claimed
    assert result.official_scalar_cost is None
    assert result.official_n_break_even is None


def test_source_prior_amortization_is_not_borrowed_from_sequential_effect() -> None:
    preregistration, source, results = _bundle(offline_draws=10_000)
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        results,
    )

    assert result.online_gate_passed
    assert result.offline_inclusive_break_even_occurrence is None
    assert not result.offline_inclusive_gate_passed
    assert result.offline_inclusive_status == "NOT_ESTABLISHED"
    assert not result.meta_prior_target_savings_claimed


def test_factorial_cells_are_not_summed_against_one_direct_arm() -> None:
    preregistration, source, results = _bundle()
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        results,
    )
    summaries = {item.arm.arm_key: item for item in result.summaries}

    assert (
        summaries[NO_PRIOR_SEQUENTIAL.arm_key]
        .positive_certified_target_draws
        == 425_984
    )
    assert (
        summaries[META_PRIOR_SEQUENTIAL.arm_key]
        .positive_certified_target_draws
        == 425_984
    )
    assert (
        summaries[DIRECT_SEQUENTIAL.arm_key]
        .positive_certified_target_draws
        == 737_280
    )
    assert 425_984 + 425_984 == 851_968
    assert result.combined_online_advantage
    assert result.online_gate_passed
    assert result.registered_positive_target_generative_draw_efficiency


def test_missing_negative_cell_cannot_be_removed_from_closure() -> None:
    preregistration, source, results = _bundle()
    truncated = results[:-1]
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="four quotient cells",
    ):
        evaluate_factorial_sample_efficiency_gate_v1(
            preregistration,
            source,
            truncated,
        )


def test_full_evidence_then_prefix_attack_is_rejected() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    target = next(
        index
        for index, item in enumerate(attacked)
        if item.arm == NO_PRIOR_SEQUENTIAL
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="certificate/evaluation obligations",
    ):
        attacked[target] = replace(
            attacked[target],
            operational_full_fixed_evidence_access_count=1,
        )


def test_paired_stream_substitution_blocks_gate() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    target = next(
        index
        for index, item in enumerate(attacked)
        if item.arm == META_PRIOR_SEQUENTIAL
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    attacked[target] = replace(
        attacked[target],
        paired_seed_stream_id=_id("different-seed-family"),
    )
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        attacked,
    )

    assert not result.prefix_only_access_verified
    assert not result.online_gate_passed


def test_positive_operational_fallback_access_is_rejected() -> None:
    preregistration, source, results = _bundle()
    target = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="positive sample endpoint",
    ):
        replace(
            target,
            work=replace(
                target.work,
                fallback=EvidenceEventVectorV1(
                    "OPERATIONAL_QUERY",
                    0,
                    0,
                    1,
                    0,
                    0,
                ),
            ),
        )


def test_direct_negative_arm_is_not_part_of_the_design() -> None:
    preregistration, source, results = _bundle()
    negative = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="obligations|negative control",
    ):
        replace(
            negative,
            arm=DIRECT_FIXED,
            source_prior_gate_id=None,
            source_proposal_id=None,
            source_prior_selected_this_arm=False,
            cold_occurrence_local_model=True,
        )


def test_meta_tie_is_valid_selection_not_a_required_main_effect() -> None:
    preregistration, source, results = _bundle()
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        results,
    )
    no_prior = next(
        item
        for item in result.summaries
        if item.arm == NO_PRIOR_SEQUENTIAL
    )
    meta = next(
        item
        for item in result.summaries
        if item.arm == META_PRIOR_SEQUENTIAL
    )

    assert (
        no_prior.positive_certified_target_draws
        == meta.positive_certified_target_draws
    )
    assert result.meta_selection_valid
    assert not result.meta_prior_main_effect
    assert result.online_gate_passed


def test_negative_control_draws_are_reported_but_cannot_offset_endpoint() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    target = next(
        index
        for index, item in enumerate(attacked)
        if item.arm == META_PRIOR_SEQUENTIAL
        and item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    prior_positive = sum(
        item.work.certified_target_draws
        for item in attacked
        if item.arm == META_PRIOR_SEQUENTIAL
        and item.occurrence.context_key
        != "variable_negative_k6_minus_edge_v0"
    )
    attacked[target] = replace(
        attacked[target],
        work=_work(60 * 131_072, 60, True),
    )
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        attacked,
    )
    summary = next(
        item
        for item in result.summaries
        if item.arm == META_PRIOR_SEQUENTIAL
    )

    assert summary.positive_certified_target_draws == prior_positive
    assert summary.negative_control_certified_target_draws == 60 * 131_072
    # 60 support-descriptor queries plus the separately charged 60-row
    # exact fallback are both retained in the native work vector.
    assert summary.negative_control_exact_kernel_queries == 120
    assert attacked[target].work.fallback.exact_kernel_queries == 60
    assert result.online_gate_passed


def test_independent_generative_verification_suffix_is_charged() -> None:
    preregistration, source, results = _bundle()
    target = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    amended = replace(
        target,
        work=replace(
            target.work,
            independent_verification=EvidenceEventVectorV1(
                "STANDALONE_EVALUATION",
                0,
                17,
                1,
                0,
                0,
            ),
        ),
    )

    assert (
        amended.work.certified_target_draws
        == amended.work.operational_target_draws + 17
    )


def test_confidence_budget_substitution_invalidates_shared_authority() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    attacked[0] = replace(
        attacked[0],
        confidence=replace(
            attacked[0].confidence,
            confidence_budget_id=_id("different-confidence-budget"),
        ),
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="incompatible confidence contracts",
    ):
        evaluate_factorial_sample_efficiency_gate_v1(
            preregistration,
            source,
            attacked,
        )


def test_duplicate_confidence_authority_is_rejected() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    for index, item in enumerate(attacked):
        if item.arm == META_PRIOR_FIXED:
            attacked[index] = replace(
                item,
                confidence=replace(
                    item.confidence,
                    certificate_profile_id=_id(
                        "duplicate-meta-fixed-authority"
                    ),
                ),
            )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="duplicated, dropped",
    ):
        evaluate_factorial_sample_efficiency_gate_v1(
            preregistration,
            source,
            attacked,
        )


def test_dropped_confidence_authority_is_rejected() -> None:
    preregistration, source, results = _bundle()
    attacked = list(results)
    k6 = next(
        item
        for item in attacked
        if item.arm == NO_PRIOR_SEQUENTIAL
        and item.occurrence.context_key == "variable_target_k6_v0"
    )
    for index, item in enumerate(attacked):
        if (
            item.arm
            in (NO_PRIOR_SEQUENTIAL, META_PRIOR_SEQUENTIAL)
            and item.occurrence.context_key
            == "variable_negative_k6_minus_edge_v0"
        ):
            attacked[index] = replace(
                item,
                confidence=replace(
                    item.confidence,
                    certificate_profile_id=(
                        k6.confidence.certificate_profile_id
                    ),
                ),
            )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="duplicated, dropped",
    ):
        evaluate_factorial_sample_efficiency_gate_v1(
            preregistration,
            source,
            attacked,
        )


def test_negative_exact_fallback_authority_mismatch_is_rejected() -> None:
    _, _, results = _bundle()
    target = next(
        item
        for item in results
        if item.arm == NO_PRIOR_SEQUENTIAL
        and item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="60-row exact fallback",
    ):
        replace(
            target,
            work=replace(
                target.work,
                fallback=EvidenceEventVectorV1(
                    "OPERATIONAL_QUERY",
                    0,
                    0,
                    59,
                    0,
                    0,
                ),
            ),
        )


def test_direct_model_reuse_attack_is_rejected() -> None:
    _, _, results = _bundle()
    target = next(item for item in results if item.arm == DIRECT_SEQUENTIAL)
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="not cold per occurrence",
    ):
        replace(target, target_model_reused=True)


def test_real_w5_direct_runner_has_typed_gate_adapter() -> None:
    import acfqp.variable_order_graph_rapm_v1 as graph
    from acfqp.variable_graph_direct_sequential_v1 import (
        run_direct_sequential_context_v1,
        verify_direct_sequential_result_v1,
    )

    preregistration, _, _ = _bundle()
    occurrence = next(
        item
        for item in preregistration.occurrences
        if item.context_key == "variable_target_w5_v0"
    )
    context = next(
        item
        for item in graph.registered_variable_order_contexts_v1()
        if item.context_id == occurrence.context_id
    )
    direct = run_direct_sequential_context_v1(context)
    verification = verify_direct_sequential_result_v1(direct)
    adapted = adapt_direct_sequential_result_v1(
        preregistration,
        occurrence,
        direct,
        verification,
    )

    assert adapted.arm == DIRECT_SEQUENTIAL
    assert adapted.acquired_ground_rows == 30
    assert adapted.work.acquisition_draws == 245_760
    assert adapted.work.target_acquisition.exact_kernel_queries == 30
    assert adapted.work.fallback.exact_kernel_queries == 0
    assert adapted.work.independent_verification.exact_kernel_queries > 0
    assert adapted.exact_failure_probability == Fraction(99, 5000)
    assert adapted.exact_normalized_reward == Fraction(3, 64)
    assert adapted.prefix_coupling_verified


def test_feasible_exact_risk_difference_is_not_mislabeled_noninferiority() -> None:
    preregistration, source, results = _bundle()
    changed = list(results)
    target = next(
        index
        for index, item in enumerate(changed)
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    changed[target] = replace(
        changed[target],
        exact_failure_probability=Fraction(1337, 67500),
    )
    result = evaluate_factorial_sample_efficiency_gate_v1(
        preregistration,
        source,
        changed,
    )

    assert result.exact_objective_constraint_preservation
    assert not result.exact_risk_equality_claimed
    assert result.online_gate_passed


def test_exact_constraint_or_objective_violation_is_rejected() -> None:
    _, _, results = _bundle()
    target = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="positive sample endpoint",
    ):
        replace(target, exact_failure_probability=Fraction(1, 20))
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="certificate/evaluation obligations",
    ):
        replace(target, exact_normalized_reward=Fraction(1, 32))


def test_registered_context_delta_and_terminal_class_are_bound() -> None:
    _, _, results = _bundle()
    positive = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    negative = next(
        item
        for item in results
        if item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )

    assert negative.exact_failure_probability == Fraction(2277, 16000)
    assert negative.exact_failure_probability < Fraction(1, 5)
    assert negative.terminal_class is TerminalClass.PLAN_CERTIFICATE
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="registered delta",
    ):
        replace(negative, exact_failure_probability=Fraction(1, 5))
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="registered delta",
    ):
        replace(
            negative,
            terminal_class=TerminalClass.INFEASIBILITY_CERTIFICATE,
        )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="positive sample endpoint",
    ):
        replace(
            positive,
            terminal_class=TerminalClass.INFEASIBILITY_CERTIFICATE,
        )


def test_missing_support_descriptor_charge_is_rejected() -> None:
    _, _, results = _bundle()
    target = next(
        item
        for item in results
        if item.arm == NO_PRIOR_SEQUENTIAL
        and item.occurrence.context_key == "variable_target_w5_v0"
    )
    with pytest.raises(
        FactorialSampleEfficiencyInvariantViolation,
        match="support-descriptor queries were omitted",
    ):
        replace(
            target,
            work=replace(
                target.work,
                target_acquisition=replace(
                    target.work.target_acquisition,
                    exact_kernel_queries=target.acquired_ground_rows - 1,
                ),
            ),
        )
