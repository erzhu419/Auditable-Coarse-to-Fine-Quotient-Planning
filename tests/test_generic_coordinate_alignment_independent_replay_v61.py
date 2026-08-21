from acfqp import construction_k7_applicability_target_preregistration_v87 as prior
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.generic_coordinate_alignment_independent_replay_v61 import (
    rederive_coordinate_alignment_v61,
)
from acfqp.generic_coordinate_alignment_v60 import compile_coordinate_alignment_v60


def test_v61_independently_rederives_exact_v60_projection():
    config = prior.campaign_config_v87()
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], 888_882, config
    )
    factor_library = v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    model = load_projected_model_artifact_v86()[
        "projected_disagreement_successor_model"
    ]
    applicability = load_action_applicability_model_v87()[
        "action_applicability_program"
    ]
    produced = compile_coordinate_alignment_v60(
        model, applicability, partial["candidate"], partial["rows"], adapter.catalogue
    )
    replayed = rederive_coordinate_alignment_v61(
        model,
        applicability,
        partial["candidate"].public_document,
        [row.to_document() for row in partial["rows"]],
        [row.to_document() for row in adapter.catalogue],
    )
    assert replayed == produced
