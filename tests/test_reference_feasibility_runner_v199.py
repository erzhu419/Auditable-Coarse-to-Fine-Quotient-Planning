"""Synthetic scientific checks; the retained H4 inputs stay unopened."""
from collections import Counter
from fractions import Fraction
import json

import pytest

from scripts import run_controlled_predictive_reference_feasibility_v199 as runner


F = Fraction
REWARD_ONLY = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.)


def native(cells, rows, roots):
    return dict(cells=cells, rows=rows, roots=roots)


def outcome(probability, target, reward=F(0)):
    probability, reward = F(probability), F(reward)
    return [probability.numerator, probability.denominator, target, reward.numerator, reward.denominator]


def closure_fixture():
    # s1 favors LEFT, s2 favors DOWN.  Width1 merges them because every complete
    # action component is below1; the average model ties on reward and uses DOWN.
    return native([[0, 0, 'CUTOFF'], [1, 0, 'WON'], [2, 1, 'ACTIVE'],
        [3, 1, 'ACTIVE'], [4, 2, 'ACTIVE']], [
        [2, 'DOWN', [outcome(1, 0)]],
        [2, 'LEFT', [outcome(1, 0, F(2, 5))]],
        [3, 'DOWN', [outcome(F(1, 2), 0, F(2, 5)), outcome(F(1, 2), 1, F(2, 5))]],
        [3, 'LEFT', [outcome(1, 0)]],
        [4, 'DOWN', [outcome(1, 2)]],
        [4, 'LEFT', [outcome(1, 3)]]], [4])


def test_joint_policy_vectors_and_exact_sequential_eps():
    payload = native([[0, 0, 'LOST'], [1, 0, 'WON'], [2, 1, 'ACTIVE']], [
        [2, 'DOWN', [outcome(1, 0, 2)]], [2, 'LEFT', [outcome(1, 1, 1)]]], [2])
    kernel = runner.decode_kernel(payload)
    chosen = runner.solve(kernel, dict(reward_weight=1, failure_penalty=2, goal_bonus=1))
    assert chosen['policy'][2] == 'LEFT'
    assert chosen['values'][2] == (F(1), F(0), F(1))
    assert chosen['qvectors'][2, 'DOWN'] == (F(2), F(1), F(0))
    # The achievable winner cannot inherit DOWN's bigger reward component.
    assert chosen['values'][2] != (F(2), F(0), F(1))
    tied = native([[0, 0, 'CUTOFF'], [1, 1, 'ACTIVE']], [
        [1, 'LEFT', [outcome(1, 0, runner.EPSILON/2)]],
        [1, 'DOWN', [outcome(1, 0)]]], [1])
    assert runner.solve(runner.decode_kernel(tied), REWARD_ONLY)['policy'][1] == 'DOWN'


def test_average_model_uses_own_successors_and_replays_its_own_policy():
    counts = Counter()
    kernel = runner.decode_kernel(closure_fixture(), counts)
    oracle = runner.solve(kernel, REWARD_ONLY, counts)
    record, abstract, mapping = runner.compile_reference(kernel, {'q': oracle}, F(1), counts)
    assert mapping[2] == mapping[3]
    cell = mapping[2]
    down = abstract['rows'][cell, 'DOWN']
    assert {target: p for p, target, _ in down} == {mapping[0]: F(3, 4), mapping[1]: F(1, 4)}
    assert {r for _, _, r in down} == {F(1, 5)}
    assert record['metrics']['max_successor_tv'] == .25
    assert record['metrics']['max_reward_spread'] == .4
    planned = runner.solve(abstract, REWARD_ONLY, counts, 'abstract')
    root_cell = mapping[4]
    assert planned['values'][root_cell] == (F(1, 5), F(0), F(1, 4))
    lifted = {state: planned['policy'][mapping[state]] for state in (2, 3, 4)}
    replayed = runner.replay_policy(kernel, lifted, counts)
    assert oracle['policy'][2] == 'LEFT' and lifted[2] == 'DOWN'
    assert oracle['values'][4] == (F(2, 5), F(0), F(0))
    assert replayed[4] == (F(0), F(0), F(0))
    # Paying only the selected row during replay also certifies no oracle re-plan.
    assert counts['replay_dp_action_rows'] == 3
    assert counts['replay_dp_outcome_terms'] == 4
    assert counts['compiled_member_action_rows'] == len(kernel['rows'])


def test_all_queries_joint_profiles_signed_floor_and_exact_legal_masks():
    payload = native([[0, 0, 'CUTOFF'], [1, 0, 'WON'], [2, 1, 'ACTIVE'],
        [3, 1, 'ACTIVE'], [4, 2, 'ACTIVE'], [5, 2, 'ACTIVE']], [
        [2, 'DOWN', [outcome(1, 0, 1)]], [2, 'LEFT', [outcome(1, 1)]],
        [3, 'DOWN', [outcome(1, 0, 1)]],
        [4, 'DOWN', [outcome(1, 2)]], [5, 'DOWN', [outcome(1, 3)]]], [4, 5])
    kernel = runner.decode_kernel(payload)
    reward = runner.solve(kernel, REWARD_ONLY)
    goal = runner.solve(kernel, dict(reward_weight=1, failure_penalty=0, goal_bonus=2))
    _, _, reward_mapping = runner.compile_reference(kernel, {'reward': reward}, F(0))
    assert reward_mapping[4] == reward_mapping[5]
    record, _, joint_mapping = runner.compile_reference(kernel, {'reward': reward, 'goal': goal}, F(0))
    assert joint_mapping[4] != joint_mapping[5]
    assert joint_mapping[0] != joint_mapping[1]  # status remains exact
    _, _, coarse = runner.compile_reference(kernel, {'reward': reward, 'goal': goal}, F(100))
    assert coarse[2] != coarse[3]  # even huge bins never merge different legal masks
    assert coarse[3] != coarse[4]  # layer remains exact
    negative = native([[0, 0, 'CUTOFF'], [1, 1, 'ACTIVE']], [
        [1, 'DOWN', [outcome(1, 0, -F(1, 1000))]]], [1])
    signed = runner.decode_kernel(negative)
    profile = runner.solve(signed, REWARD_ONLY)
    key = runner.partition_key(signed, {'q': profile}, 1, F(1, 4))
    assert key[3] == (-1, 0, 0)
    # Compact encoded bytes include the actual schema/cells/rows/roots payload.
    assert record['metrics']['serialized_bytes'] == len(runner.compact_bytes(record['model']))


def test_five_controlled_inputs_shared_curve_phases_and_paid_failure(tmp_path, monkeypatch):
    base = tmp_path/'synthetic_inputs'
    base.mkdir()
    (base/'manifest.json').write_text(json.dumps(dict(status='complete'))+'\n')
    queries = {f'q{index:02d}': REWARD_ONLY for index in range(14)}
    payload = native([[10, 0, 'CUTOFF'], [20, 1, 'ACTIVE']], [
        [20, 'DOWN', [outcome(1, 10, F(1, 4))]]], [20])
    for name in runner.CASE_NAMES:
        directory = base/name
        directory.mkdir()
        (directory/'FULL.model.json').write_text(json.dumps(payload)+'\n')
        (directory/'portable_inputs.json').write_text(json.dumps(dict(queries=queries))+'\n')
    monkeypatch.setattr(runner, 'INPUT_BASE', base)
    # The synthetic test does not read or retain real source/runtime files.
    monkeypatch.setattr(runner, 'freeze_source', lambda output: None)
    output = tmp_path/'success'
    result = runner.run(output)
    assert [(row['phase'], row['input_reads']) for row in result['phases']] == [
        ('protocol_frozen', 0), ('inputs_retained', 5), ('profiles_frozen', 5),
        ('curve_complete', 5), ('complete', 5)]
    counts = result['costs']
    assert counts['input_files_read'] == counts['input_files_retained'] == 5
    assert counts['oracle_dp_calls'] == 14
    assert counts['abstract_dp_calls'] == counts['replay_dp_calls'] == 84
    assert all(counts[key] == 0 for key in runner.ZERO_COUNTS)
    compiled = json.loads((output/'compiled.json').read_text())
    assert len(compiled['models']) == 6 and len(compiled['root_bindings']) == 2
    assert [row['union_root'] for row in compiled['root_bindings']] == [1, 3]
    summary = json.loads((output/'summary.json').read_text())
    assert summary['positive_control_valid']
    assert all(len(row['queries']) == 14 for row in summary['curve'])
    input_records = json.loads((output/'input_manifest.json').read_text())['records']
    assert len(input_records) == 5
    for row in input_records:
        from pathlib import Path
        assert Path(row['original']).read_bytes() == (output/row['saved']).read_bytes()
    (base/'manifest.json').write_text(json.dumps(dict(status='failed'))+'\n')
    failed = tmp_path/'failure'
    with pytest.raises(runner.ReferenceExecutionError) as caught:
        runner.run(failed)
    assert caught.value.record['operation'] == 'inputs'
    assert caught.value.record['costs']['input_files_read'] == 5
    retained = json.loads((failed/'run.json').read_text())
    assert retained['status'] == 'failed' and retained['costs']['input_files_retained'] == 5
    assert retained['costs'].get('oracle_dp_calls', 0) == 0
