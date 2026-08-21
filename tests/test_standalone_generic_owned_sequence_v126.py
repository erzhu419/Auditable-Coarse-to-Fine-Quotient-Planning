from pathlib import Path
import ast

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96
from acfqp.construction_k7_standalone_generic_model_preregistration_v125 import campaign_config_v125
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_artifact_subprogram_acquisition_v121 import acquire_generic_artifact_subprogram_model_v121
from acfqp.generic_inventory_assembly_adapter_v118 import build_inventory_assembly_adapter_v118
from acfqp.standalone_generic_owned_sequence_v126 import run_standalone_generic_owned_sequence_v126


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    config = campaign_config_v125()
    adapter = build_inventory_assembly_adapter_v118(1_030_004, config)
    library = derive_artifact_factor_projection_v120(source)
    acquired = acquire_generic_artifact_subprogram_model_v121(
        adapter,
        library,
        source,
        v96.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )
    return config, adapter, acquired["partial"]


def test_v126_owns_episode_loop_and_retains_certificate_boundary():
    config, adapter, partial = _inputs()
    sequence = run_standalone_generic_owned_sequence_v126(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=(302, 303, 304),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    assert all(row["success"] for row in sequence["episodes"])
    assert sequence["owned_episode_loop_implementation_present"] is True
    assert sequence["retained_v113_state_carrier_present"] is False
    assert sequence["retained_v113_sequence_orchestration_present"] is False
    assert sequence["retained_v119_sequence_orchestration_present"] is False
    assert sequence["direct_generic_factor_program_plan_count"] > 0
    assert sequence["every_new_ground_query_followed_a_failed_certificate"] is True
    assert sequence["planner_consumed_compiled_successor_without_raw_transition_argument"] is True


def test_v126_import_surface_excludes_v113_and_v119_sequence_orchestrators():
    path = Path(__file__).resolve().parents[1] / "src/acfqp/standalone_generic_owned_sequence_v126.py"
    imported = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any(
        name.endswith("generic_incremental_abstract_successor_sequence_v113")
        or name.endswith("generic_genesis_authorized_program_branch_sequence_v119")
        for name in imported
    )
