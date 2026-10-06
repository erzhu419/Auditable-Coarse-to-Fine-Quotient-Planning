"""Actual candidate restoration, new streams, own-FIRST primary and cutoff HOLD."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_win_confirmation_v323 as audit


def previous():
    return json.loads((ROOT/'reports/component_heads_v322/summary.json').read_text())


def actual_candidate(task='A'):
    document = previous(); row = document['by_lifecycle'][0]
    source = document['source_provenance']['parents'][0]
    first = row['initial'][task]['head_version']
    item = {key: row['cells'][task]['WIN_ONLY'][key] for key in ('head_version', 'assembly')}
    identity = dict(lifecycle=0, parent=0, context_id=row['initial'][task]['context_id'], arm='WIN_ONLY')
    return dict(item=item, first_version=first, source_weights=audit.read_source_weights(source['checkpoint']),
        checkpoint=source['checkpoint'], identity=identity)


@pytest.mark.parametrize('task', ['A', 'B'])
def test_actual_saved_candidate_restores_first_then_existing_win_only_delta(task):
    # A sparse WIN-only delta interpreted as a complete table discards FIRST_R.
    value = actual_candidate(task)
    first, candidate = audit.check_candidate(**value)
    assert np.array_equal(first.reward, candidate.reward)
    assert not np.array_equal(first.terminal, candidate.terminal)
    assert candidate.version == 1 and candidate.receipts[-1] == value['item']['head_version']
    assert candidate.receipts[-1]['updates'] == first.receipts[-1]['updates']


@pytest.mark.parametrize('field', ['base_file', 'updates', 'version'])
def test_candidate_cannot_skip_first_change_training_or_select_another_version(field):
    value = actual_candidate(); value['item'] = deepcopy(value['item'])
    receipt = value['item']['head_version']
    receipt[field] = None if field == 'base_file' else receipt[field]+1
    with pytest.raises(ValueError, match='actual frozen WIN_ONLY'):
        audit.check_candidate(**value)


def test_candidate_component_ownership_cannot_change_after_selection():
    value = actual_candidate(); value['item'] = deepcopy(value['item'])
    value['item']['assembly']['reward_source'] = 'NSTEP_QUERY'
    with pytest.raises(ValueError, match='component ownership'):
        audit.check_candidate(**value)


def fresh_evaluation(arm='WIN_ONLY'):
    # Use real previously produced natural endpoints; only finite reader fixtures
    # duplicate them to exercise the new 64-stream/count contract, never science.
    row = previous()['by_lifecycle'][0]
    if arm == 'SOURCE':
        document = json.loads((ROOT/'reports/reward_targets_v321/summary.json').read_text())
        value = deepcopy(document['by_lifecycle'][0]['final_evaluations']['A']['SOURCE'])
    else:
        value = deepcopy(row['cells']['A'][arm]['evaluation'])
    value['game_summaries'] = [deepcopy(game) for game in value['game_summaries']*2]
    for episode, game in enumerate(value['game_summaries']): game['seed'] = audit.evaluation_seed(0, 'A', episode)
    value['counts'] = {section: {name: count*2 for name, count in counts.items()}
        for section, counts in value['counts'].items()}
    if 'representation_counts' in value:
        value['representation_counts'] = {name: count*2 for name, count in value['representation_counts'].items()}
    return value, row['initial']['A']['planning_belief']['estimated_p_four']


@pytest.mark.parametrize('arm', audit.ARMS)
def test_all_supported_new_arm_summaries_bind_sixtyfour_paired_seeds_and_paid_work(arm):
    value, belief = fresh_evaluation(arm)
    result = audit.check_evaluation(value, 0, 'A', belief, value['head_version'])
    assert result == np.mean([game['utility'] for game in value['game_summaries']])


@pytest.mark.parametrize('field', ['seed', 'head', 'raw', 'utility', 'status'])
def test_wrong_new_seed_head_raw_utility_or_endpoint_is_rejected(field):
    value, belief = fresh_evaluation(); version = deepcopy(value['head_version'])
    if field == 'seed': value['game_summaries'][0]['seed'] -= 2000000000
    elif field == 'head': value['head_version'] = previous()['by_lifecycle'][0]['initial']['A']['head_version']
    elif field == 'raw': value['counts']['environment']['raw_tile_productions'] += 1
    elif field == 'utility': value['game_summaries'][0]['utility'] += 1.
    else: value['game_summaries'][0]['status'] = 'LOST'
    with pytest.raises(ValueError): audit.check_evaluation(value, 0, 'A', belief, version)


def test_new_reader_configuration_matches_producer():
    from acfqp.science.win_confirmation_run_v323 import configuration
    source = ROOT/'reports/component_heads_v322/summary.json'
    assert audit.expected_configuration(source) == configuration(source)


def records(rows):
    return [dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={task: {arm:
        float(np.mean([game['utility'] for game in value['game_summaries']]))
        for arm, value in evaluations.items()} for task, evaluations in row['evaluations'].items()}) for row in rows]


def test_paired_primary_cannot_use_source_or_omit_adverse_lives():
    from test_win_confirmation_analysis_v323 import cohort
    from acfqp.science.win_confirmation_analysis_v323 import summarize
    rows = cohort(); result = summarize(rows)
    audit.check_analysis(result, records(rows), rows)
    wrong = deepcopy(result); wrong['primary'] = wrong['final_ab_contrasts']['WIN_ONLY_minus_SOURCE']
    with pytest.raises(ValueError, match='sole primary cannot'):
        audit.check_analysis(wrong, records(rows), rows)
    wrong = deepcopy(result); wrong['primary']['lifecycle_values']['0'] += 1.
    with pytest.raises(ValueError, match='paired vector'):
        audit.check_analysis(wrong, records(rows), rows)


@pytest.mark.parametrize('arm', audit.ARMS)
def test_any_of_three_new_arm_cutoffs_holds_all_terminal_inference(arm):
    from test_win_confirmation_analysis_v323 import cohort
    from acfqp.science.win_confirmation_analysis_v323 import summarize
    rows = cohort(); rows[3]['evaluations']['B'][arm]['game_summaries'][2]['status'] = 'CUTOFF'
    result = summarize(rows); audit.check_analysis(result, records(rows), rows)
    assert result['primary'] is None and not result['bootstrap_executed']
    wrong = deepcopy(result); wrong['task_contrasts']['A']['WIN_ONLY_minus_FIRST_LOCAL'] = dict(mean=1.)
    with pytest.raises(ValueError, match='suppresses every terminal'):
        audit.check_analysis(wrong, records(rows), rows)


def test_retention_remains_a_separate_evidence_requirement():
    from test_win_confirmation_analysis_v323 import cohort
    from acfqp.science.win_confirmation_analysis_v323 import summarize
    rows = cohort(); result = summarize(rows)
    wrong = deepcopy(result); wrong['retained_execution_gain_supported'] = not result['retained_execution_gain_supported']
    with pytest.raises(ValueError, match='separate conditions'):
        audit.check_analysis(wrong, records(rows), rows)
