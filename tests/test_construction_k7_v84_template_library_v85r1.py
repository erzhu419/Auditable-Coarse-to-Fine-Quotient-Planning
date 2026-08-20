import pytest

from acfqp.construction_k7_v84_template_library_v85r1 import (
    LIBRARY_ARTIFACT_ID,
    ConstructionK7V84TemplateLibraryV85R1Error,
    load_v84_template_library_v85r1,
)


def test_v85r1_template_library_is_self_contained_and_negative_authority():
    document = load_v84_template_library_v85r1()
    assert document["library_artifact_id"] == LIBRARY_ARTIFACT_ID
    assert document["source_program_count"] == 6
    assert document["compiled_template_library"]["role_free_template_count"] == 63
    assert document["offline_template_source_ground_support_labels"] == 515
    assert document["future_target_prediction_authority_present"] is False
    assert document["abstract_plan_safety_authority_present"] is False
    assert document["official_execution_allowed"] is False


def test_v85r1_template_library_rejects_wrong_path(monkeypatch, tmp_path):
    import acfqp.construction_k7_v84_template_library_v85r1 as producer

    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    monkeypatch.setattr(producer, "ARTIFACT_PATH", bad)
    with pytest.raises(ConstructionK7V84TemplateLibraryV85R1Error):
        load_v84_template_library_v85r1()
