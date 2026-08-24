import ast
from pathlib import Path

from acfqp import construction_k7_open_world_campaign_v181r1 as campaign


def test_campaign_source_has_no_manifest_program_branch_or_named_family_switch() -> None:
    source = Path(campaign.__file__).read_text()
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "transition_programs" not in names
    assert "terminal_program" not in names
    assert "family_name" not in names


def test_campaign_constants_match_frozen_acquisition_and_resource_schedule() -> None:
    assert campaign.QUERY_BLOCK_SIZE == 16
    assert campaign.REPEAT_COUNT == 2
    assert campaign.MINIMUM_LABEL_COUNT == 32
    assert campaign.MAXIMUM_LABEL_COUNT == 512
    assert campaign.STABLE_CONFIRMATION_BLOCKS == 2
    assert campaign.MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION == 2_000_000
    assert campaign.MAXIMUM_TARGET_GROUND_LABELS == 32
    assert campaign.MAXIMUM_DECISIONS == 64
