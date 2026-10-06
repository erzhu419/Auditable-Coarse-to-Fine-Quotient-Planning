import json
from fractions import Fraction as F

from scripts import probe_acquisition_budget_v237 as probe


def retained_inputs(tmp_path, monkeypatch):
    v236, v231, output = [tmp_path/name for name in ('v236', 'v231', 'output')]
    for directory in (v236, v231):
        directory.mkdir()
        (directory/'analysis.json').write_text(json.dumps({'valid': True}))
    rows = [dict(life=life, index=index, arm='ORACLE_GAP', origin='V235_countermodel',
        kind='failure', phase='A_RETURN', case={'context': 'A'}, identity=1,
        fees={'total_reference_paid_samples': 999999, 'source_paid_samples': 4608},
        query='risk', chosen='DETOUR_RETURN', other='SHORT', family='S_D_FULL',
        training_counts={}, validation_counts={}, parameters={}) for life, index in probe.ROSTER]
    (v236/'records.json').write_text(json.dumps(rows))
    costs = [dict(life=life, arm=arm, source_samples=4608, total_samples=total)
        for life, pair in enumerate(((14144, 12112), (17072, 17024), (17168, 16352)))
        for arm, total in zip(('ORACLE_BALANCED', 'ORACLE_GAP'), pair)]
    (v231/'summary.json').write_text(json.dumps({'life_summaries': costs}))
    monkeypatch.setattr(probe, 'V236', v236)
    monkeypatch.setattr(probe, 'V231', v231)
    monkeypatch.setattr(probe, 'OUTPUT', output)
    return output


def test_headroom_uses_matched_lifecycle_costs_and_keeps_original_source_costs(tmp_path, monkeypatch):
    retained_inputs(tmp_path, monkeypatch)
    rows = probe.prepare_inputs()
    assert [row['budget_reference']['headroom'] for row in rows] == [2032, 48, 816]
    assert sum(row['budget_reference']['headroom'] for row in rows) == 2896
    assert all(row['budget_reference']['source_paid_samples_per_arm'] == 4608 for row in rows)
    assert all(row['fees']['total_reference_paid_samples'] == 999999 for row in rows)
    assert all('not_REBUILD' in row['budget_reference']['scope'] for row in rows)


def test_fixed_inputs_are_saved_before_oracle_truth_and_bounds_are_evaluated(tmp_path, monkeypatch):
    output = retained_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(probe, 'capture', lambda: None)

    def load_truth(rows):
        frozen = json.loads((output/'inputs.json').read_text())
        protocol = json.loads((output/'protocol.json').read_text())
        assert len(frozen) == 3 and all('truth_parameters' not in row for row in frozen)
        assert protocol['phases'] == ['protocol_frozen', 'inputs_frozen']
        return [dict(row, truth_parameters={'S': {'DELIVERY': F(9, 10)}}) for row in rows]

    def evaluate(row):
        assert (output/'oracle_inputs.json').exists()
        assert json.loads((output/'protocol.json').read_text())['phases'][-1] == 'oracle_truth_loaded'
        return dict(row, bounds={'expected_samples_lower': '1000', 'budget_insufficient': row['life'] > 0})

    monkeypatch.setattr(probe, 'load_truth', load_truth)
    monkeypatch.setattr(probe, 'evaluate', evaluate)
    summary = probe.run()
    assert summary['necessary_expected_samples_lower_sum'] == 3000
    assert summary['matched_total_headroom'] == 2896 and summary['total_budget_insufficient']
    assert summary['budget_insufficient_lives'] == [1, 2]
    assert not summary['matched_rebuild_reference_available'] and not summary['query_certificates_obtained']
