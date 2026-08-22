from pathlib import Path

from acfqp import construction_k7_robust_factor_dictionary_independent_verifier_v131r2 as base
from acfqp.anonymous_relational_template_instantiator_v147 import (
    instantiate_anonymous_relational_templates_v147,
)
from acfqp.generic_layout_factorized_world_model_v5 import discover_generic_layout_v5
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v147_rebinds_one_alpha_relation_template_on_every_source_occurrence():
    campaign = loads_canonical_json(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes()
    )
    bank = (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes()
    verification = (
        ROOT / "v146_anonymous_relational_factor_bank_verification.json"
    ).read_bytes()
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_024
    receipts = []
    for occurrence in campaign["target_occurrences"]:
        adapter = build_maintenance_cascade_adapter_v144(occurrence["seed"], config)
        labels = occurrence["strict_no_prior_acquisition"]["ground_support_labels"]
        stream = base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
        rows = tuple(row for _ in range(labels) for row in next(stream))
        layout = discover_generic_layout_v5(
            rows,
            adapter.catalogue,
            layout_domain=config["generic_domains"]["layout"],
        )
        receipt = instantiate_anonymous_relational_templates_v147(
            bank, verification, rows, adapter.catalogue, layout
        )
        assert receipt["exact_relational_instantiation_count"] >= 1
        assert receipt["binding_derived_from_raw_observations"] is True
        assert receipt["target_coordinate_roles_supplied_by_bank"] is False
        assert receipt["exact_rows_are_program_proposals_not_planning_authority"] is True
        receipts.append(receipt["instantiation_id"])
    assert len(set(receipts)) == 6


def test_v147_retains_claim_boundary():
    campaign = loads_canonical_json(
        (ROOT / "v145_certificate_local_recovery_union_campaign.json").read_bytes()
    )
    occurrence = campaign["target_occurrences"][0]
    config = maintenance_cascade_config_v144()
    adapter = build_maintenance_cascade_adapter_v144(occurrence["seed"], config)
    labels = occurrence["strict_no_prior_acquisition"]["ground_support_labels"]
    stream = base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    rows = tuple(row for _ in range(labels) for row in next(stream))
    layout = discover_generic_layout_v5(
        rows, adapter.catalogue, layout_domain=config["generic_domains"]["layout"]
    )
    receipt = instantiate_anonymous_relational_templates_v147(
        (ROOT / "v146_anonymous_relational_factor_bank.json").read_bytes(),
        (ROOT / "v146_anonymous_relational_factor_bank_verification.json").read_bytes(),
        rows,
        adapter.catalogue,
        layout,
    )
    assert receipt["new_target_outcomes_accessed"] is False
    assert receipt["complete_world_model_claimed"] is False
    assert receipt["official_scalar_cost"] is None
    assert receipt["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
