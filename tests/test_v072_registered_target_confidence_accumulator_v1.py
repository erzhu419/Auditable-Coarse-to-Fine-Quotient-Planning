from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)
from acfqp import (
    v072_registered_target_confidence_independent_verifier_v1
    as independent,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_disjoint_pure_count_cores_reconcile_exact_support_and_other() -> None:
    support = tuple(sorted((_id("disjoint:a"), _id("disjoint:b"))))
    validation = tuple(
        support[0] if index % 4 < 2 else (
            support[1] if index % 4 == 2 else _id("disjoint:novel")
        )
        for index in range(2_048)
    )
    producer = accumulator.derive_registered_confidence_count_core_v1(
        purpose=(
            accumulator.RegisteredTargetAcquisitionPurposeV1.COLD_INITIAL
        ),
        support_descriptor_ids=support,
        validation_descriptor_ids=validation,
        checkpoint=2_048,
    )
    counts, intervals = (
        independent.replay_registered_confidence_count_intervals_core_v1(
            support_descriptor_ids=support,
            validation_descriptor_ids=validation,
            checkpoint=2_048,
        )
    )
    assert counts == (1_024, 512, 512)
    assert counts == tuple(item.success_count for item in producer.events)
    assert tuple((item[0], item[1]) for item in intervals) == tuple(
        (
            item.checkpoint.lower_probability,
            item.checkpoint.upper_probability,
        )
        for item in producer.events
    )
    assert sum(counts) == 2_048
    assert sum(item[0] for item in intervals) <= 1
    assert sum(item[1] for item in intervals) >= 1
    assert all(
        type(bound) is Fraction
        for lower, upper, _document in intervals
        for bound in (lower, upper)
    )
    assert producer._payload()["source_prior_used_in_confidence"] is False


def test_production_acquisition_api_owns_all_target_randomness() -> None:
    signature = inspect.signature(
        accumulator.acquire_registered_target_row_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "context",
        "catalogue",
        "action",
        "arm",
        "purpose",
        "checkpoint",
        "frontier",
        "parent",
    )
    forbidden = {
        "observations",
        "observation",
        "counts",
        "intervals",
        "law",
        "seed",
        "random_words",
        "source_prior",
    }
    assert forbidden.isdisjoint(signature.parameters)
    verify_signature = inspect.signature(
        independent.verify_registered_target_confidence_independently_v1
    )
    assert tuple(verify_signature.parameters) == (
        "authority_chain",
        "anchor",
        "acquisition",
        "parent_replay",
    )
    assert forbidden.isdisjoint(verify_signature.parameters)


@pytest.mark.parametrize("foreign_chain", (None, object(), "draft"))
def test_invalid_chain_fails_before_any_observer_access(
    monkeypatch: pytest.MonkeyPatch,
    foreign_chain: object,
) -> None:
    calls: list[str] = []

    def forbidden_open(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls.append("open")
        raise AssertionError("observer must remain unopened")

    monkeypatch.setattr(
        observer,
        "open_heldout_target_transition_stream_v2",
        forbidden_open,
    )
    with pytest.raises(
        accumulator.RegisteredTargetAcquisitionGateLockedV1
    ) as caught:
        accumulator.acquire_registered_target_row_v1(
            authority_chain=foreign_chain,  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            context=object(),  # type: ignore[arg-type]
            catalogue=object(),  # type: ignore[arg-type]
            action=(0, 1, 0),
            arm="NO_PRIOR",
            purpose=(
                accumulator
                .RegisteredTargetAcquisitionPurposeV1.COLD_INITIAL
            ),
            checkpoint=2_048,
        )
    assert calls == []
    assert caught.value.access_audit.target_access_started is False
    assert caught.value.access_audit.observer_draw_calls == 0


def test_independent_replay_rejects_foreign_input_with_zero_draws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden_open(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls.append("open")
        raise AssertionError("observer must remain unopened")

    monkeypatch.setattr(
        observer,
        "open_heldout_target_transition_stream_v2",
        forbidden_open,
    )
    with pytest.raises(
        independent.RegisteredTargetConfidenceIndependentReplayLockedV1
    ) as caught:
        independent.verify_registered_target_confidence_independently_v1(
            authority_chain=object(),  # type: ignore[arg-type]
            anchor=object(),  # type: ignore[arg-type]
            acquisition=object(),  # type: ignore[arg-type]
        )
    assert calls == []
    assert caught.value.access_audit == (
        independent.ZERO_REPLAY_TARGET_ACCESS_AUDIT
    )
    assert caught.value.access_audit.target_access_started is False


def test_frontier_cannot_be_authorized_by_arbitrary_content_ids() -> None:
    with pytest.raises(
        accumulator.V072RegisteredTargetConfidenceAccumulatorViolation
    ):
        accumulator.RegisteredAcquisitionSelectionAuthorityV1(
            object(),
            _id("chain"),
            _id("anchor"),
            _id("context"),
            "NO_PRIOR",
            1,
            None,
            _id("occurrence"),
            _id("failed-audit"),
            _id("model-pair"),
            _id("model-replay"),
            _id("candidate-inventory"),
            _id("proposal-order"),
            _id("selected-candidate"),
            (_id("acquisition"),),
            (_id("support-row"),),
            _id("support-row"),
            (),
            (_id("support-row"),),
            2_048,
            2_048,
            _id("causal"),
        )
    signature = inspect.signature(
        accumulator.freeze_registered_acquisition_frontier_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "selection_authority",
        "predecessor",
        "supporting_acquisitions",
    )
    assert "selected_row_binding_ids" not in signature.parameters
    assert "causal_evidence_id" not in signature.parameters
    assert (
        accumulator
        .REGISTERED_INCREMENTAL_FRONTIER_SELECTION_AUTHORITY_STATUS
        == "ENABLED_ONLY_BY_INDEPENDENT_FAILED_PROOF_SELECTOR_REPLAY"
    )


def test_confidence_authority_direct_construction_remains_impossible() -> None:
    assert projection.REGISTERED_TARGET_CONFIDENCE_AUTHORITY_ENABLED is True
    assert projection.REGISTERED_TARGET_PROJECTION_STATUS == (
        "ENABLED_ONLY_BY_EXACT_ANCHOR_AND_INDEPENDENT_TRANSCRIPT_REPLAY"
    )
    with pytest.raises(
        projection.V072ConfidenceRowProjectionInvariantViolation
    ):
        projection.RegisteredTargetConfidenceProjectionAuthorityV1(
            object(),
            _id("anchor"),
            _id("final"),
            object(),  # type: ignore[arg-type]
            (),
            _id("discovery"),
            _id("validation"),
            _id("prefix"),
            _id("verification"),
            2_048,
        )


def test_transcript_and_frontier_source_encode_linear_no_replacement_rules(
) -> None:
    source = inspect.getsource(accumulator)
    assert "for _ in range(purpose.discovery_draw_count)" in source
    assert "for _ in range(checkpoint)" in source
    assert "replacement_allowed" in source
    assert "early_stop_allowed" in source
    assert "source_prior_used_in_confidence" in source
    assert "set(predecessor.supporting_acquisition_ids)" in source
    assert "< set(supporting_ids)" in source
    assert "in frontier.supporting_row_binding_ids" in source
    assert "development_synthetic_transition" not in source
    assert "caller_law_or_seed_accepted" in source
