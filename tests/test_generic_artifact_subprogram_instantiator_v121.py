from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v121 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    exact_generic_artifact_factor_replay_v121,
    generic_artifact_factor_stop_update_v121,
    instantiate_normalized_subprograms_v121,
    synthesize_generic_artifact_factor_candidate_v121,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    build_dual_budget_adapter_v119,
    dual_budget_config_v119,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    V51_FACTOR_TEMPLATE_PROJECTION,
    synthesize_partial_factor_candidate_v15,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _sources():
    return {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }


def _development_rows():
    config = dual_budget_config_v119()
    adapter = build_dual_budget_adapter_v119(1_032_001, config)
    rows = []
    for label, batch in enumerate(
        v59.predecessor.predecessor.ground._witness_blind_depth_frontier(adapter), 1
    ):
        rows.extend(batch)
        if label == 40:
            break
    return config, adapter, tuple(rows)


def test_v121_generic_binder_reconstructs_same_exact_factor_assignments():
    config, adapter, rows = _development_rows()
    derived = derive_artifact_factor_projection_v120(_sources())[
        "v15_partial_synthesizer_projection"
    ]
    generic = synthesize_generic_artifact_factor_candidate_v121(
        rows,
        adapter.catalogue,
        derived,
        support_label_count=40,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN
        ),
        candidate_content_id=domains.extension_content_id_v121,
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    historical = synthesize_partial_factor_candidate_v15(
        rows,
        adapter.catalogue,
        V51_FACTOR_TEMPLATE_PROJECTION,
        support_label_count=40,
        layout_domain=config["generic_domains"]["layout"],
        candidate_domain=(
            domains.CONSTRUCTION_K7_GENERIC_ARTIFACT_SUBPROGRAM_ACQUISITION_V121_DOMAIN
        ),
        candidate_content_id=domains.extension_content_id_v121,
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
    )
    assert generic.public_document["compiled_factor_assignments"] == historical.public_document[
        "compiled_factor_assignments"
    ]
    assert exact_generic_artifact_factor_replay_v121(
        generic, rows, adapter.catalogue
    )["exact"] is True
    stop = generic_artifact_factor_stop_update_v121(
        generic,
        rows,
        adapter.catalogue,
        candidate_epoch=0,
        invalidated_candidate_count=0,
        post_issuance_exact_prediction_success_count=40,
        global_alpha_denominator=config["global_alpha_denominator"],
    )
    assert stop["generic_symbol_binding_and_opcode_interpretation_used"] is True
    assert stop["hand_written_normalized_expression_shape_cases"] == 0


def test_v121_binds_an_unseen_two_variable_expression_without_a_shape_case():
    library = {
        "schema": "acfqp.cross_schema_factor_template_projection.v15",
        "source_factor_library_id": "f" * 64,
        "cross_schema_subprograms": [
            {
                "signature_sha256": "e" * 64,
                "result_type": "INT",
                "normalized_expression": ["E05", ["A", 0], ["A", 1]],
                "source_schema_pairs": [[2, 2]],
            }
        ],
        "target_slot_inventory_supplied": False,
        "semantic_names_supplied": False,
    }
    rows = instantiate_normalized_subprograms_v121(0, 2, 3, library)
    assert len(rows) == 9
    assert {tuple(row["action_dependencies"]) for row in rows} == {
        (0,),
        (1,),
        (2,),
        (0, 1),
        (0, 2),
        (1, 2),
    }


def test_v121_source_has_no_normalized_expression_shape_dispatch():
    source = Path(__import__(
        "acfqp.generic_artifact_subprogram_instantiator_v121",
        fromlist=["x"],
    ).__file__).read_text()
    assert "elif normalized" not in source
    assert "normalized ==" not in source
