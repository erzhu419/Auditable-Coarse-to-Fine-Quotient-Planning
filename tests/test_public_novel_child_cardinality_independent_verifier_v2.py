from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import public_novel_child_cardinality_authority_v2 as authority
from acfqp import (
    public_novel_child_cardinality_independent_verifier_v2 as verifier,
)
from tests.test_public_novel_child_cardinality_authority_v2 import (
    _gain,
    _valid,
)


def _verify_fixture(*, include_novel_in_closure: bool = False):
    context, parent, closure, gain, claim = _valid(
        label=(
            "independent-present"
            if include_novel_in_closure
            else "independent"
        ),
        include_novel_in_closure=include_novel_in_closure,
    )
    return context, parent, closure, gain, claim


def test_independent_verifier_reconstructs_rows_counts_and_bounds() -> None:
    context, parent, closure, gain, claim = _verify_fixture()
    attestation = (
        verifier.verify_public_novel_child_cardinality_authority_v2(
            claimed=claim,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=gain,
        )
    )
    assert attestation.authority_id == claim.authority_id
    assert attestation.exact_new_child_row_count == len(
        claim.rows_to_acquire
    )
    assert attestation.exact_cumulative_child_row_count == len(
        claim.cumulative_rows
    )
    assert attestation.exact_round_draw_upper == (
        2_048 + 8_256 * len(claim.rows_to_acquire)
    )
    document = attestation.to_document()
    assert document["production_authorization_builder_called"] is False
    assert document["claimed_ids_or_counts_trusted"] is False
    assert document["environment_law_queries"] == 0
    assert document["new_draw_calls"] == 0


def test_independent_verifier_rejects_omitted_descriptor_induced_catalogue() -> None:
    context, parent, closure, gain, claim = _verify_fixture()
    omitted_catalogue = claim.induced_child_catalogues[0]
    catalogues = claim.induced_child_catalogues[1:]
    rows = tuple(
        row
        for row in claim.induced_rows
        if row.catalogue_id != omitted_catalogue.catalogue_id
    )
    forged_evidence = replace(
        claim.cardinality_evidence,
        induced_child_catalogues=catalogues,
        induced_rows=rows,
        already_present_rows=(),
        rows_to_acquire=rows,
        cumulative_rows=rows,
        new_child_row_count=len(rows),
        cumulative_child_row_count=len(rows),
        exact_round_draw_upper=2_048 + 8_256 * len(rows),
        cumulative_draw_upper=2_048 + 8_256 * len(rows),
        public_catalogue_queries=len(catalogues),
    )
    forged_gain = _gain(forged_evidence)
    forged = authority.PublicNovelChildCardinalityAuthorityV2(
        forged_evidence,
        forged_gain,
    )
    with pytest.raises(
        verifier.IndependentNovelChildCardinalityV2VerificationFailure,
    ):
        verifier.verify_public_novel_child_cardinality_authority_v2(
            claimed=forged,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=forged_gain,
        )


def test_independent_verifier_rejects_extra_public_catalogue_and_rows() -> None:
    context, parent, closure, gain, claim = _verify_fixture()
    extra_catalogue = closure.catalogues[0]
    extra_rows = tuple(
        row
        for row in closure.rows
        if row.catalogue_id == extra_catalogue.catalogue_id
    )
    induced_catalogues = tuple(
        sorted(
            (*claim.induced_child_catalogues, extra_catalogue),
            key=lambda item: item.catalogue_id,
        )
    )
    induced_rows = tuple(
        sorted(
            (*claim.induced_rows, *extra_rows),
            key=lambda item: item.physical_row_id,
        )
    )
    forged_evidence = replace(
        claim.cardinality_evidence,
        induced_child_catalogues=induced_catalogues,
        induced_rows=induced_rows,
        already_present_rows=extra_rows,
        public_catalogue_queries=len(induced_catalogues),
    )
    forged_gain = _gain(forged_evidence)
    forged = authority.PublicNovelChildCardinalityAuthorityV2(
        forged_evidence,
        forged_gain,
    )
    with pytest.raises(
        verifier.IndependentNovelChildCardinalityV2VerificationFailure,
        match="differs",
    ):
        verifier.verify_public_novel_child_cardinality_authority_v2(
            claimed=forged,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=forged_gain,
        )


def test_independent_verifier_rejects_charging_already_present_rows() -> None:
    context, parent, closure, gain, claim = _verify_fixture(
        include_novel_in_closure=True,
    )
    assert claim.rows_to_acquire == ()
    rows = claim.induced_rows
    forged_evidence = replace(
        claim.cardinality_evidence,
        already_present_rows=(),
        rows_to_acquire=rows,
        cumulative_rows=rows,
        new_child_row_count=len(rows),
        cumulative_child_row_count=len(rows),
        exact_round_draw_upper=2_048 + 8_256 * len(rows),
        cumulative_draw_upper=2_048 + 8_256 * len(rows),
    )
    forged_gain = _gain(forged_evidence)
    forged = authority.PublicNovelChildCardinalityAuthorityV2(
        forged_evidence,
        forged_gain,
    )
    with pytest.raises(
        verifier.IndependentNovelChildCardinalityV2VerificationFailure,
        match="differs",
    ):
        verifier.verify_public_novel_child_cardinality_authority_v2(
            claimed=forged,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=forged_gain,
        )


def test_independent_verifier_rejects_foreign_identity_even_if_self_valid() -> None:
    context, parent, closure, gain, claim = _verify_fixture()
    foreign_evidence = replace(
        claim.cardinality_evidence,
        model_id="0" * 64,
    )
    foreign_gain = _gain(foreign_evidence)
    foreign = authority.PublicNovelChildCardinalityAuthorityV2(
        foreign_evidence,
        foreign_gain,
    )
    with pytest.raises(
        verifier.IndependentNovelChildCardinalityV2VerificationFailure,
    ):
        verifier.verify_public_novel_child_cardinality_authority_v2(
            claimed=foreign,
            context=context,
            parent=parent,
            current_h1_closure=closure,
            selector_gain=foreign_gain,
        )


def test_round_formula_helper_rejects_duplicate_rows_and_round_reuse() -> None:
    _context_value, _parent_value, _closure, _gain_value, claim = (
        _verify_fixture()
    )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="sorted and distinct",
    ):
        authority.cumulative_round_draw_upper_v2(
            1,
            tuple(
                sorted(
                    (*claim.cumulative_rows, claim.cumulative_rows[0]),
                    key=lambda item: item.physical_row_id,
                )
            ),
        )
    with pytest.raises(
        authority.PublicNovelChildCardinalityV2InvariantViolation,
        match="round one or two",
    ):
        authority.cumulative_round_draw_upper_v2(
            3,
            claim.cumulative_rows,
        )
