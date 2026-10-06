"""Wrong pairing, selection leakage and interval arithmetic must change validity."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_program_headroom_analysis_v165 as audit
from acfqp.science import controlled_predictive_program_headroom_v165 as core

TEMP = Path(__file__).resolve().parents[1]/'reports/v165_runtime_tmp'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failures = request.session.testsfailed
    yield
    TEMP.mkdir(parents=True, exist_ok=True)
    path = TEMP/'analyzer_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    payload['attempts'].append({'tests': sum(i.module.__name__ == __name__ for i in request.session.items),
                               'failures': request.session.testsfailed-failures,
                               'new_environment_samples': 0, 'real_training_updates': 0,
                               'scope': 'Synthetic pairing, independent selections, unknown leaves and interval arithmetic.'})
    path.write_text(json.dumps(payload, indent=2)+'\n')


def fixture_data():
    candidates, programs, roots, branches, rows = [], [], [], [], []
    for life in range(4):
        for query in ('risk1', 'risk8'):
            candidate = dict(candidate_id=f'P{life}', first_action='LEFT', probe_action='DOWN',
                             true_suffix=['UP']*3, false_suffix=['RIGHT']*3)
            candidates.append(dict(heldout_life=life, query=query, candidates=[candidate]))
            programs.append(dict(heldout_life=life, query=query,
                                 programs={name: dict(candidate_id=candidate['candidate_id'], mapping=mapping)
                                           for name, mapping in [('LEARNED', dict(true='A', false='B')),
                                                                 ('GLOBAL', dict(true='A', false='A'))]}))
            for slot in range(4):
                roots.append(dict(root_id=f'{life}:{query}:{slot}', life=life, query=query, slot=slot, board=[0]*16))
    for root in roots:
        for fold in range(4):
            if fold == root['life']: continue
            for suffix in range(4):
                predicate = None if suffix == 3 and root['slot'] == 0 else True
                for arm in ('H2', 'A', 'B'):
                    mode = 'H2' if arm == 'H2' else f'P{fold}_{arm}'
                    plan = dict(branch_id=f"{root['root_id']}:{fold}:{suffix}:{mode}", root_id=root['root_id'],
                                heldout_life=fold, suffix=suffix, mode=mode, seed=root['life']*1000+root['slot']*10+suffix)
                    branches.append(plan)
                    gain = 0. if arm == 'H2' or predicate is None else (1. if root['slot'] % 2 == 0 else -1.)*(1 if arm == 'A' else -1)
                    vector = [2.+gain, 0., 1.]
                    module = dict(predicate=predicate, actual_word=['LEFT'], actual_probe='DOWN',
                                  prefix_steps=1 if predicate is None else 4, attempts=1 if predicate is None else 4,
                                  exit_reason='terminal' if predicate is None else 'budget', exit_step=1 if predicate is None else 4)
                    rows.append(dict(plan, query=root['query'], score=vector[0]*2048, steps=10,
                                     status='WON', components=vector, utility=audit._utility(vector, root['query']), module=module))
    return candidates, programs, roots, branches, rows


def evaluated(data):
    roster = core.build_roster(*data[:4])
    result = core.evaluate(roster, data[4])
    return roster, result


def test_independent_matching_and_arithmetic_agree():
    data = fixture_data(); roster, result = evaluated(data)
    checked = audit.audit(*data, roster, result)
    assert checked['valid'], [c for c in checked['checks'] if not c['passed']]
    for cell in result['splits']['primary']['cells']:
        assert cell['leaf_evidence']['false']['support'] == 0
        assert cell['leaf_evidence']['false']['utility_delta_A_minus_B'] is None
        assert cell['bit_refit_mapping']['false'] == 'B'


def test_donor_not_replaced_when_first_match_has_missing_branch():
    data = fixture_data()
    first = next(r for r in data[3] if r['root_id'] == '0:risk1:0' and r['heldout_life'] == 1)
    data[3].remove(first)
    roster = audit.independent_roster(*data[:4])
    assert roster['cells'][0]['donor']['heldout_life'] == 1
    assert not roster['complete']
    assert not audit.independent_evaluate(roster, data[4])['complete']


def test_selection_decision_does_not_read_scoring_values():
    data = fixture_data(); roster = audit.independent_roster(*data[:4])
    before = audit.independent_evaluate(roster, data[4])
    changed = deepcopy(data[4])
    for row in changed:
        if row['suffix'] >= 2 and row['mode'].endswith('_B') and row['module']['predicate'] is not None:
            row['components'][0] += 50
            row['utility'] = audit._utility(row['components'], row['query'])
    after = audit.independent_evaluate(roster, changed)
    assert [r['selected_arm'] for r in before['splits']['primary']['root_rows']] == [r['selected_arm'] for r in after['splits']['primary']['root_rows']]
    assert [r['selected_arm'] for r in before['splits']['reverse']['root_rows']] != [r['selected_arm'] for r in after['splits']['reverse']['root_rows']]


@pytest.mark.parametrize('corruption', ['seed', 'none_path', 'nonterminal', 'utility'])
def test_bad_paid_triplet_invalidates_whole_diagnostic(corruption):
    data = fixture_data(); roster = audit.independent_roster(*data[:4])
    row = next(r for r in data[4] if r['root_id'] == '0:risk1:0' and r['heldout_life'] == 1 and r['suffix'] == 3 and r['mode'] == 'P1_B')
    if corruption == 'seed': row['seed'] += 1
    elif corruption == 'none_path': row['module']['exit_step'] += 1
    elif corruption == 'nonterminal': row.update(status='CUTOFF', utility=None)
    else: row['utility'] += 1
    assert not audit.independent_evaluate(roster, data[4])['complete']


def test_mutated_decision_interval_or_split_fails_audit():
    data = fixture_data(); roster, good = evaluated(data)
    for corruption in ('decision', 'ci', 'split'):
        result = deepcopy(good)
        primary = result['splits']['primary']
        if corruption == 'decision': primary['root_rows'][0]['selected_arm'] = 'B'
        elif corruption == 'ci': primary['comparisons'][0]['metrics']['utility']['conditional_suffix_ci95'][0] -= .1
        else: primary['selection_suffixes'], primary['scoring_suffixes'] = primary['scoring_suffixes'], primary['selection_suffixes']
        assert not audit.audit(*data, roster, result)['valid']


def test_fixed_weight_variance_propagation():
    # Each two-suffix root difference [0,2] has mean variance 1; four roots
    # and four histories give aggregate mean variance 1/16.
    roots = [audit._moments([0., 2.]) for _ in range(4)]
    history = audit._pool(roots)
    aggregate = audit._pool([history]*4)
    assert aggregate['mean'] == 1 and aggregate['mean_variance'] == 1/16
    assert aggregate['conditional_suffix_ci95'] == pytest.approx([.51, 1.49])
