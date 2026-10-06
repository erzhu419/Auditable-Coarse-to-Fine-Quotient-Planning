"""Original policy/fee preservation and qualification-before-truth ordering."""
from copy import deepcopy
import json

from scripts import run_joint_query_qualification_v235 as runner


def fake_certificates(operators, case, choices, cache):
    cache.setdefault(('fixed_profile_a',), object())
    cache.setdefault(('fixed_profile_b',), object())
    decisions = {'reward': dict(policy='WAIT', certified=True)}
    comparisons = []
    for query in ('goal', 'risk'):
        chosen = choices[query]['policy']
        cc = [dict(other=other, certified=True, family='S_D_FULL')
              for other in runner.core.POLICIES if other!=chosen]
        decisions[query] = dict(policy=chosen, certified=True, comparisons=cc)
        comparisons.extend(cc)
    return dict(queries=decisions, all_ready=True, comparison_records=comparisons)


def test_fixed_policy_full_paid_rows_and_fees_are_preserved(monkeypatch):
    tape = runner.rows(runner.V234/'tapes.jsonl.gz')[0]
    previous = runner.rows(runner.V232/'inputs.jsonl.gz')[0]
    old = runner.rows(runner.V234/'records.jsonl.gz')[0]
    original, calls = deepcopy(tape), []

    def checked(operators, case, choices, cache):
        calls.append(deepcopy((operators, case, choices)))
        return fake_certificates(operators, case, choices, cache)

    monkeypatch.setattr(runner.core, 'certificates', checked, raising=False)
    result = runner.qualify(tape, previous, old, {})
    assert calls == [(tape['operators'], tape['case'], previous['terminal_plan']['queries'])]
    assert runner.policies(result['queries']) == runner.policies(previous['terminal_plan']['queries'])
    assert result['fees'] == tape['fees']
    assert result['row_lengths'] == {op: len(seq) for op, seq in tape['operators'].items()}
    assert result['new_observations'] == result['new_paid_samples'] == 0
    assert result['unique_profile_calls'] == 2 and result['profile_cache_hits'] == 4
    assert tape == original


def test_all_24_certificates_are_saved_before_saved_truth_is_read(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'OUTPUT', tmp_path)
    monkeypatch.setattr(runner, 'capture', lambda: None)
    monkeypatch.setattr(runner.core, 'certificates', fake_certificates, raising=False)
    original_score = runner.score_frozen
    scored_sizes = []

    def checked_score(results, previous):
        protocol = json.loads((tmp_path/'run.json').read_text())
        assert protocol['phases'][-1] == 'certificates_frozen'
        assert len(runner.rows(tmp_path/'records.jsonl.gz')) == len(results) == 24
        assert (tmp_path/'tapes.jsonl.gz').read_bytes() == (runner.V234/'tapes.jsonl.gz').read_bytes()
        scored_sizes.append(len(results))
        return original_score(results, previous)

    monkeypatch.setattr(runner, 'score_frozen', checked_score)
    summary = runner.run()
    assert scored_sizes == [24]
    assert summary['records'] == 24
    assert summary['new_observations'] == summary['new_paid_samples'] == 0
    assert not summary['scientific_gate_changed']
