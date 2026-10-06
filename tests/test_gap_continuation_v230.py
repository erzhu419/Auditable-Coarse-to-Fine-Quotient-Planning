from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from scripts import run_gap_continuation_v230 as runner


def member(samples):
    result = runner.old.empty()
    for op in runner.old.OPERATORS:
        result[op]['DELIVERY'] = samples
    return result


def row():
    return dict(life=2, index=42, case={'context': 'B'}, batches=[
        dict(operator='SHORT_PASS', increments={'DELIVERY': 256, 'LOST': 0}, spent=256),
        dict(operator='DETOUR_PASS', increments={'DELIVERY': 128, 'LOST': 0, 'RECOVERY': 0}, spent=384)])


def test_reference_fees_include_both_contexts_and_only_preceding_history():
    source = dict(a=[member(384) for _ in range(3)], b=[member(128) for _ in range(3)])
    history = [dict(index=3, spent=384), dict(index=30, spent=320),
               dict(index=42, spent=384), dict(index=43, spent=384)]
    fees = runner.reference_costs(row(), source, history)
    assert fees == dict(source_paid_samples=4608, history_paid_samples=704,
                        historical_targets=2, prefix_paid_samples=256)
    prefix = runner.prefix_counts(row())
    assert prefix['SHORT_PASS']['DELIVERY'] == 256
    assert sum(prefix['DETOUR_PASS'].values()) == 0


def test_suffix_seeds_define_same_operator_stream_for_each_method():
    seeds = runner.suffix_seeds(2, 42)
    assert seeds == dict(zip(runner.old.OPERATORS, (260594, 260595, 260596)))
    assert runner.suffix_seeds(2, 42) == seeds
    assert set(seeds.values()).isdisjoint(runner.suffix_seeds(2, 44).values())


def test_paid_loop_charges_fixture_suffix_and_keeps_library_frozen(monkeypatch):
    original_state = {'fixture': [1, 2]}
    monkeypatch.setattr(runner, 'frozen_state', lambda record, source: deepcopy(original_state))

    def plan(counts, case, state, work):
        samples = sum(sum(op.values()) for op in counts.values())
        return dict(utility_lower=F(2), goal_impossible=False, query_ready=samples >= 272)

    monkeypatch.setattr(runner, 'candidate_plan', plan)
    monkeypatch.setattr(runner.old, 'choose', lambda *args: {'operator': 'DETOUR_PASS'})

    def fixture_draw(generator, law, operator, increments, samples, work, progress):
        increments['DELIVERY'] += samples
        work['controlled_samples'] += samples
        progress['draw_end'] += samples

    monkeypatch.setattr(runner, 'draw', fixture_draw)
    source = dict(a=[member(384) for _ in range(3)], b=[member(128) for _ in range(3)])
    history = [dict(index=3, spent=384)]
    result = runner.continue_one(row(), source, history, 'OLD_V229', None)
    assert result['fees']['additional_paid_samples'] == result['work']['controlled_samples'] == 16
    assert result['fees']['total_reference_paid_samples'] == 4608+384+256+16
    assert result['batches'][0]['draw_start'] == 0 and result['batches'][0]['draw_end'] == 16
    assert result['prefix_operator_samples']['SHORT_PASS'] == 256
    assert result['suffix_operator_samples']['DETOUR_PASS'] == 16
    assert result['library_frozen'] and result['library_before'] == result['library_after'] == original_state
    assert result['commits'] == 0 and result['completed']
