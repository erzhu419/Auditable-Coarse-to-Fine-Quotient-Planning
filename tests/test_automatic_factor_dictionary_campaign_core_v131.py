from pathlib import Path

from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.automatic_minimal_factor_dictionary_v131 import (
    derive_automatic_minimal_factor_dictionary_v131,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY,
    modular_routing_config_v128,
)
from acfqp.automatic_factor_dictionary_campaign_core_v131 import (
    build_automatic_dictionary_factor_prior_occurrence_v131,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _source():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def test_v131_development_occurrence_runs_owned_sequence_with_normalized_prior():
    source = _source()
    source_library = derive_artifact_factor_projection_v120(source)
    dictionary = derive_automatic_minimal_factor_dictionary_v131(
        source_library, source
    )
    config = modular_routing_config_v128()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 320
    document = build_automatic_dictionary_factor_prior_occurrence_v131(
        config,
        family=FAMILY,
        seed=1_031_104,
        episode_indices=(338, 339, 340),
        artifact_factor_library=dictionary,
        source_campaign_bytes=source,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"][
        "acquisition_labels_avoided_by_normalized_factor_prior"
    ] > 0
    assert document["sample_tax_comparison"][
        "fixed_two_to_library_cardinality_prior_multiplier_present"
    ] is False
    assert all(
        episode["success"]
        for arm in (
            "normalized_factor_prior_owned_sequence",
            "strict_no_prior_owned_sequence",
        )
        for episode in document[arm]["episodes"]
    )
    assert document["official_scalar_cost"] is None
