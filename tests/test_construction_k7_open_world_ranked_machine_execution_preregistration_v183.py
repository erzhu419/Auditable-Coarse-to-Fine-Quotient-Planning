import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_open_world_ranked_machine_execution_preregistration_v183 as preregistration


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "src" / "acfqp" / "construction_k7_open_world_ranked_machine_independent_verifier_v183.py"


def test_v183_execution_preregistration_is_source_closed_and_outcome_free() -> None:
    frozen = preregistration.freeze_open_world_ranked_machine_execution_preregistration_v183()
    document = frozen.to_document()
    assert document["execution_preregistration_id"] == preregistration.EXPECTED_PREREGISTRATION_ID
    assert document["source_or_target_execution_started"] is False
    assert document["source_or_target_outcomes_accessed"] is False
    assert document["official_execution_allowed"] is False
    for fact in document["source_facts"]:
        raw = (ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]


def test_v183_output_root_is_now_the_exact_committed_success_inventory() -> None:
    document = preregistration.freeze_open_world_ranked_machine_execution_preregistration_v183().to_document()
    output_root = ROOT / document["output_root_relative_path"]
    assert tuple(sorted(path.name for path in output_root.iterdir())) == (
        "CAMPAIGN.json",
        "VERIFICATION.json",
    )


def test_v183_independent_verifier_has_no_producer_import() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("ranked_machine_campaign_v183" in name for name in imports)
    assert "run_open_world_ranked_machine_campaign_v183" not in source
