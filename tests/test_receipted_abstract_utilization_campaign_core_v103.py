from pathlib import Path
from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_post_dependency_source_library_v97 import freeze_post_dependency_source_library_v97
from acfqp.construction_k7_residual_factor_library_v62 import freeze_residual_factor_library_v62, verify_residual_factor_library_v62
from acfqp.receipted_abstract_utilization_campaign_core_v103 import build_receipted_utilization_occurrence_v103


def test_v103_development_occurrence_derives_utilization_only_from_receipts():
    config = pre.campaign_config_v96(); source = freeze_post_dependency_source_library_v97(Path('.tmp/exact-freeze/v96_persistent_multi_residual_campaign.json').read_bytes(), Path('.tmp/exact-freeze/v96_persistent_multi_residual_verification.json').read_bytes()).to_document()['compiled_structure_library']; residual = verify_residual_factor_library_v62(freeze_residual_factor_library_v62()).to_document()['compiled_library']
    row = build_receipted_utilization_occurrence_v103(config, family='MAINTENANCE_CASCADE', seed=590_543, episode_indices=(0,1), factor_library=pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY, residual_library=residual, structural_prior_library=source)
    u = row['meta_prior_receipted_utilization']; assert u['every_execution_action_independently_receipted'] is True; assert u['receipt_replay_uses_no_producer_summary_count'] is True; assert row['complete_world_model_synthesized'] is False
