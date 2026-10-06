"""Independent precision arithmetic on synthetic paired component outcomes."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics

import pytest

from acfqp.science import controlled_predictive_module_precision_v158 as core
from scripts import analyze_controlled_predictive_module_precision_v158 as audit
from scripts import run_controlled_predictive_module_precision_v158 as runner

TEMP = Path(__file__).resolve().parents[1] / 'reports/v158_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP / 'analyzer_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, environment_samples=0,
        native_calls=0, production_source_reads=0, synthetic_work=dict(WORK),
        scope='In-memory paired arithmetic, conditional SE, cutoffs and frozen settings.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def roots():
    return [dict(root_id=f'{life}:{query}:{source}:{slot}', life=life,
        query=query, source_method=source, slot=slot,
        prediction=dict(advantage=1. if slot % 2 else -1., accept=bool(slot % 2)))
        for life in range(4) for query in ('risk1', 'risk8')
        for source in ('H2', 'LEARN8') for slot in range(4)]


@pytest.fixture
def paired_fixture():
    root_rows = roots()
    outcomes = []
    for root in root_rows:
        slot = root['slot']
        for split in ('TRAIN', 'EVAL'):
            for suffix in range(32):
                if split == 'TRAIN':
                    advantage = ((-1. if suffix < 8 else 1.) if slot == 0 else
                                 (1. if suffix < 8 else -1.) if slot == 1 else
                                 1. if slot == 2 else -1.)
                else:
                    advantage = (1. + root['life'] / 4 + int(root['query'] == 'risk8') / 8
                        + int(root['source_method'] == 'LEARN8') / 16 + slot / 32
                        + (suffix - 15.5) / 16)
                weight = 1 if root['query'] == 'risk1' else 8
                for mode in ('H_GATE', 'M_GATE'):
                    components = [2., 0., 1.] if mode == 'H_GATE' else [2. + advantage + 2 * weight, 1., 0.]
                    outcomes.append(dict(**{k: root[k] for k in ('root_id', 'life', 'query', 'source_method', 'slot')},
                        branch_id=f'{root["root_id"]}:{split}:{suffix}:{mode}', split=split,
                        suffix=suffix, mode=mode, seed=runner.branch_seed(root, split, suffix),
                        status='WON' if mode == 'H_GATE' else 'LOST', score=4 * suffix,
                        steps=2, components=components))
    WORK['synthetic_compact_records_created'] += len(outcomes)
    assert len(root_rows) == 64 and len(outcomes) == 8192
    return root_rows, outcomes


def independent_and_core(root_rows, outcomes):
    train = audit.paired_outcomes(root_rows, outcomes, 'TRAIN')
    evaluation = audit.paired_outcomes(root_rows, outcomes, 'EVAL')
    core_train = core.build_pairs(root_rows, outcomes, 'TRAIN')
    core_eval = core.build_pairs(root_rows, outcomes, 'EVAL')
    assert audit.equivalent(train, core_train) and audit.equivalent(evaluation, core_eval)
    selected = audit.selectors(root_rows, train)
    expected = core.freeze_selectors(root_rows, core_train)
    assert audit.equivalent(selected, expected)
    result = audit.evaluate(selected, evaluation)
    assert audit.equivalent(list(result), list(core.evaluate(expected, core_eval)))
    WORK['analyzer_numeric_evaluations'] += 1
    WORK['core_numeric_evaluations'] += 1
    return selected, result


def test_all_outputs_agree_and_precision_contrast_uses_paired_eval_variance(paired_fixture):
    root_rows, outcomes = paired_fixture
    selected, (rows, summary, comparisons) = independent_and_core(root_rows, outcomes)
    assert len(selected) == len(rows) == 192 and len(summary) == 18 and len(comparisons) == 6
    assert all(row['complete'] for row in rows + summary + comparisons)
    index = {(row['root_id'], row['budget']): row for row in selected}
    assert [index[root_rows[0]['root_id'], n]['accept'] for n in (8, 16, 32)] == [False, False, True]
    assert index[root_rows[0]['root_id'], 16]['train_advantage'] == 0.
    for query in ('risk1', 'risk8'):
        contrast = next(row for row in comparisons if row['query'] == query and row['source_method'] == 'ALL')['gain']
        # Sixteen of the thirty-two roots change decision; every root has the same suffix variance.
        root_mean_variance = statistics.variance([(s - 15.5) / 16 for s in range(32)]) / 32
        expected_se = math.sqrt(16 * root_mean_variance / 32 ** 2)
        assert contrast['mean'] == pytest.approx(-1 / 128)
        assert contrast['conditional_suffix_se'] == pytest.approx(expected_se)
        assert contrast['conditional_suffix_ci95'] == pytest.approx([-1 / 128 - 1.96 * expected_se, -1 / 128 + 1.96 * expected_se])
        high, low = [next(row for row in summary if row['query'] == query and row['source_method'] == 'ALL'
                         and row['budget'] == n)['gains']['vs_old'] for n in (32, 8)]
        assert contrast['mean'] == pytest.approx(high['mean'] - low['mean'])
        assert contrast['conditional_suffix_se'] ** 2 != pytest.approx(
            high['conditional_suffix_se'] ** 2 + low['conditional_suffix_se'] ** 2)
    unchanged = next(row for row in rows if row['slot'] == 2 and row['budget'] == 32)
    assert unchanged['gains']['vs_accept']['sample_variance'] == 0.


def test_cutoffs_preserve_budget_scope_and_never_turn_missing_zero_gain_into_zero(paired_fixture):
    root_rows, outcomes = paired_fixture
    root_id = root_rows[0]['root_id']
    next(row for row in outcomes if (row['root_id'], row['split'], row['suffix'], row['mode'])
         == (root_id, 'TRAIN', 31, 'M_GATE'))['status'] = 'CUTOFF'
    selected, (rows, summary, _) = independent_and_core(root_rows, outcomes)
    assert [row['complete'] for row in selected if row['root_id'] == root_id] == [True, True, False]
    assert all(row['complete'] for row in summary if row['budget'] in (8, 16))
    assert not next(row for row in rows if row['root_id'] == root_id and row['budget'] == 32)['gains']['vs_old']['complete']
    next(row for row in outcomes if (row['root_id'], row['split'], row['suffix'], row['mode'])
         == (root_id, 'EVAL', 7, 'H_GATE'))['status'] = 'CUTOFF'
    _, (rows, summary, comparisons) = independent_and_core(root_rows, outcomes)
    zero_coefficient = next(row for row in rows if row['root_id'] == root_id and row['budget'] == 8)
    assert zero_coefficient['accept'] is False and zero_coefficient['old_accept'] is False
    for name in ('vs_old', 'vs_reject'):
        gain = zero_coefficient['gains'][name]
        assert gain['samples'][7] is None and all(value == 0 for i, value in enumerate(gain['samples']) if i != 7)
        assert not gain['complete'] and gain['mean'] is None and gain['mean_variance'] is None
    assert all(row['complete'] == (row['query'] != 'risk1' or row['source_method'] == 'LEARN8') for row in summary + comparisons)


def test_independent_seed_roster_and_settings_match_the_frozen_runner():
    root_rows = roots()
    actual = audit.branch_roster(root_rows)
    assert actual == runner.branch_roster(root_rows)
    assert len(actual) == len({row['branch_id'] for row in actual}) == 8192
    assert len({row['seed'] for row in actual}) == 4096
    assert audit.expected_settings() == runner.settings()
    WORK['independent_roster_rows'] += len(actual)
