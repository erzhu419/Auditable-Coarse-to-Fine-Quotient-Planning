from pathlib import Path

import pytest

from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134
from acfqp.packet_batching_transfer_campaign_core_v134 import (
    build_packet_batching_transfer_occurrence_v134,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


@pytest.fixture(scope="module")
def occurrence():
    return build_packet_batching_transfer_occurrence_v134(
        packet_batching_config_v134(),
        seed=1_034_101,
        episode_indices=(411, 412, 413),
        dictionary=loads_canonical_json(
            (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes()
        ),
        dictionary_verification=loads_canonical_json(
            (ROOT / "v132_opaque_source_archive_verification.json").read_bytes()
        ),
    )


def test_v134_source_unseen_domain_uses_same_compiled_planner(occurrence):
    assert occurrence["registered_gate"]["passed"] is True
    assert occurrence["registered_gate"]["source_unseen_domain_identity_present"] is True
    assert occurrence["registered_gate"][
        "planner_consumes_compiled_model_without_raw_rows"
    ] is True
    assert occurrence["registered_gate"][
        "certificate_failure_only_local_ground_distinctions"
    ] is True
    assert occurrence["accounting"][
        "acquisition_labels_avoided_by_opaque_archive_prior"
    ] > 0


def test_v134_keeps_claims_and_cost_axes_separate(occurrence):
    assert occurrence["v132_dictionary_predates_packet_batching_domain_implementation"] is True
    assert occurrence["arbitrary_unseen_domain_transfer_claimed"] is False
    assert occurrence["official_scalar_cost"] is None
    assert occurrence["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
