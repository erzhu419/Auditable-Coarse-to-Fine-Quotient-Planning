from __future__ import annotations

import pytest

from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import v072_incremental_postbuild_bridge_v1 as bridge
from acfqp import (
    v072_incremental_postbuild_independent_verifier_v1 as verifier,
)


@pytest.fixture(scope="module")
def law_b_two_round_chain() -> tuple[object, ...]:
    first = materializer.run_development_incremental_materializer_control_v1(
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
    )
    first_result = bridge.run_incremental_postbuild_bridge_v1(
        handoff=first.handoff
    )
    preparation = bridge.prepare_actual_development_round_two_request_v1(
        first_handoff=first.handoff,
        failed_postbuild=first_result,
    )
    second_handoff = (
        materializer.materialize_authorized_incremental_round_v1(
            law_key=first.law_key,
            request=preparation.request,
        )
    )
    second_result = bridge.run_incremental_postbuild_bridge_v1(
        handoff=second_handoff,
        prior_handoff=first.handoff,
        prior_postbuild=first_result,
    )
    return first, first_result, second_handoff, second_result


def test_two_round_postbuild_chain_replays_independently(
    law_b_two_round_chain: tuple[object, ...],
) -> None:
    first, first_result, second_handoff, second_result = (
        law_b_two_round_chain
    )
    first_attestation = verifier.verify_incremental_postbuild_result_v1(
        handoff=first.handoff,
        claimed=first_result,
    )
    second_attestation = verifier.verify_incremental_postbuild_result_v1(
        handoff=second_handoff,
        claimed=second_result,
        prior_handoff=first.handoff,
        prior_postbuild=first_result,
    )
    assert first_attestation.audit_status == "FAILED_PROOF_FRONTIER"
    assert first_attestation.row_lineage_count == 6
    assert second_attestation.audit_status == "CERTIFIED"
    assert second_attestation.row_lineage_count == 8
    assert (
        second_attestation.prior_postbuild_result_id
        == first_result.result_id
    )


def test_independent_replay_does_not_call_production_bridge_or_raw_helpers(
    law_b_two_round_chain: tuple[object, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, first_result, second_handoff, second_result = (
        law_b_two_round_chain
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("production helper was called")

    for name in (
        "_content_id",
        "_build_standard_inputs",
        "_build_closure_and_projections",
        "_build_production_confidence",
        "run_incremental_postbuild_bridge_v1",
    ):
        monkeypatch.setattr(bridge, name, forbidden)
    for name in (
        "raw_word_u64_v1",
        "raw_commitment_id_v1",
        "upstream_raw_word_u64_v1",
        "upstream_raw_commitment_id_v1",
    ):
        monkeypatch.setattr(materializer, name, forbidden)

    first_attestation = verifier.verify_incremental_postbuild_result_v1(
        handoff=first.handoff,
        claimed=first_result,
    )
    second_attestation = verifier.verify_incremental_postbuild_result_v1(
        handoff=second_handoff,
        claimed=second_result,
        prior_handoff=first.handoff,
        prior_postbuild=first_result,
    )
    assert first_attestation.audit_status == "FAILED_PROOF_FRONTIER"
    assert second_attestation.audit_status == "CERTIFIED"
