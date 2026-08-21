from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib

import pytest

from acfqp import construction_k7_retained_space_preregistration_v81 as pre
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70_pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_reference_aligned_source_pool_v65 import (
    GenericReferenceAlignedSourcePoolV65Error,
    pool_reference_aligned_source_evidence_v65,
)
from acfqp.phase3e_ids import canonical_json_bytes


FACTOR_LIBRARY = (
    v70_pre.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
)


def _coupled_member(seed):
    config = pre.campaign_config_v81()
    config["maximum_execution_steps"] = 5
    adapter = base.predecessor.predecessor.prior_ground._adapter(
        "COUPLED_EXCHANGE", seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, FACTOR_LIBRARY, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    candidate = partial["candidate"].public_document
    evidence_payload = {
        "schema": "acfqp.v65.construction_fixture_source_evidence",
        "layout": candidate["layout"],
        "unknown_residual_target_columns": candidate[
            "unknown_residual_target_columns"
        ],
        "common_partial_raw_transition_rows": [
            row.to_document() for row in partial["rows"]
        ],
        "query_local_raw_transition_rows": [],
        "raw_transition_rows": [row.to_document() for row in partial["rows"]],
    }
    evidence = {
        **evidence_payload,
        "source_evidence_id": hashlib.sha256(
            b"acfqp:v65:construction-fixture\x00"
            + canonical_json_bytes(evidence_payload)
        ).hexdigest(),
    }
    return {
        "member_id": hashlib.sha256(str(seed).encode()).hexdigest(),
        "common_partial_acquisition": partial["document"],
        "source_evidence": evidence,
        "action_catalogue": [row.to_document() for row in adapter.catalogue],
    }


@pytest.fixture(scope="module")
def coupled_members():
    with ProcessPoolExecutor(max_workers=2) as executor:
        return list(executor.map(_coupled_member, (888_881, 888_882)))


def test_v65_aligns_stochastic_partial_layouts_before_pooling(coupled_members):
    first, second = coupled_members
    assert (
        first["source_evidence"]["layout"]["schema_signature"]
        == second["source_evidence"]["layout"]["schema_signature"]
    )
    assert (
        first["source_evidence"]["layout"]["state_structural_colors"]
        != second["source_evidence"]["layout"]["state_structural_colors"]
    )
    result = pool_reference_aligned_source_evidence_v65(
        coupled_members, layout_domain=pre.campaign_config_v81()["generic_domains"]["layout"]
    )
    assert result["source_member_count"] == 2
    assert len(result["aligned_unknown_residual_target_columns"]) == 2
    assert len(
        {
            tuple(row["aligned_unknown_residual_target_columns"])
            for row in result["source_alignment_receipts"]
        }
    ) == 1
    assert result["canonical_source_pool"]["source_member_count"] == 2
    assert result["canonical_source_pool"]["pooled_raw_transition_row_count"] == 76
    assert result["full_finite_observation_structural_color_equality_required"] is False
    assert result["target_occurrence_or_target_outcome_input_present"] is False
    assert result["empirical_source_pool_promoted_to_safety_authority"] is False
    assert any(
        row["graph_edit_score"] > 0 for row in result["source_alignment_receipts"]
    )
    assert pool_reference_aligned_source_evidence_v65(
        list(reversed(copy.deepcopy(coupled_members))),
        layout_domain=pre.campaign_config_v81()["generic_domains"]["layout"],
    ) == result


def test_v65_rejects_layout_not_replayed_from_raw_observations(coupled_members):
    forged = copy.deepcopy(coupled_members)
    forged[1]["source_evidence"]["layout"]["schema_signature"] = "0" * 64
    with pytest.raises(GenericReferenceAlignedSourcePoolV65Error):
        pool_reference_aligned_source_evidence_v65(
            forged,
            layout_domain=pre.campaign_config_v81()["generic_domains"]["layout"],
        )
