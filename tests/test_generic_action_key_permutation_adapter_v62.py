from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_coordinate_aligned_target_preregistration_v87r1 import (
    campaign_config_v87r1,
)
from acfqp.generic_action_key_permutation_adapter_v62 import (
    permute_adapter_action_keys_v62,
)


def test_v62_permutation_is_outcome_blind_bijective_and_ground_preserving():
    config = campaign_config_v87r1()
    original = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], 888_889, config
    )
    wrapped, document = permute_adapter_action_keys_v62(original)
    assert document["transition_outcomes_accessed_to_select_permutation"] is False
    assert document["semantic_action_names_accessed"] is False
    assert document["anonymous_descriptor_fields_preserved_exactly"] is True
    assert sorted(document["old_to_new"]) == list(range(len(original.catalogue)))
    assert document["old_to_new"] != list(range(len(original.catalogue)))
    for new, old in enumerate(document["new_to_old"]):
        assert wrapped.action(new) == original.action(old)
        assert wrapped.catalogue[new].fields == original.catalogue[old].fields
        assert wrapped.action_key(wrapped.action(new)) == new


def test_v62_permutation_is_seed_deterministic_and_seed_sensitive():
    config = campaign_config_v87r1()
    make = base.predecessor.predecessor.prior_ground._adapter  # noqa: SLF001
    first = permute_adapter_action_keys_v62(
        make(config["target_family"], 888_890, config)
    )[1]
    replay = permute_adapter_action_keys_v62(
        make(config["target_family"], 888_890, config)
    )[1]
    other = permute_adapter_action_keys_v62(
        make(config["target_family"], 888_891, config)
    )[1]
    assert first == replay
    assert first["permutation_id"] != other["permutation_id"]
