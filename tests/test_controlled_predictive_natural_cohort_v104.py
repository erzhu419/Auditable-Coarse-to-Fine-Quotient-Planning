"""Restore every natural root from retained decisions and reuse the old references."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_natural_cohort_v104 as module


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_natural_cohort_v104.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0,
        scope='synthetic retained natural-game and reference fixtures only'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def write_rows(path, rows):
    with gzip.open(path, 'wt') as handle:
        for row in rows:
            handle.write(json.dumps(row) + '\n')


def retained_source(tmp_path):
    source, output = tmp_path / 'v103', tmp_path / 'v104'
    source.mkdir()
    output.mkdir()
    lifecycles, traces = [], {}
    for life in module.LIFECYCLES:
        folder = source / f'life_{life}' / 'evaluation'
        folder.mkdir(parents=True)
        methods = {name: dict(games=[]) for name in module.METHODS}
        references, raw = [], []
        for replica in range(8):
            for query in module.QUERIES:
                seed = 10390000 + life * 100 + replica
                board = [life - 8] * 9 + [replica + 1] + [0] * 6
                prefix = [life - 8] * 8 + [replica + 1] + [0] * 7
                predictions = {}
                for index, method in enumerate(module.METHODS):
                    option = None if method == 'H2_ONLY' else module.OPTIONS[index % 5]
                    event = dict(step=1, board=board, option=option, predicted_advantage=None,
                        value=0 if option == 'H2' else 1,
                        predictions={candidate: dict(value=0 if candidate == 'H2' else
                            (1 if candidate == option else -1)) for candidate in module.OPTIONS},
                        score_semantics='prefix_utility' if method == 'PREFIX_ONLY_DIRECT' else 'rank_score')
                    events = [] if method == 'H2_ONLY' else [event]
                    if events:
                        predictions[method] = deepcopy(event)
                    score = 2048 + index * 4
                    game = dict(seed=seed, replica=replica, query=query, score=score,
                        utility=score / 2048 - (4 if query == 'risk_goal' else 0), status='LOST', steps=3,
                        selected_option=option, initiation_step=None if method == 'H2_ONLY' else 1,
                        controller_events=len(events))
                    methods[method]['games'].append(game)
                    raw.append(deepcopy(dict(method=method, query=query,
                        episode=dict(seed=seed, return_score=score, status='LOST', steps_count=3,
                            steps=[dict(board=prefix), dict(board=board), dict(board=[1] * 16)]),
                        controller_events=events, action_paths=[])))
                if replica < 2:
                    references.append(dict(root=dict(life=life, query=query, episode=replica,
                        board=board, source_seed=seed, step=1), predictions=predictions,
                        terminal_log=dict(trajectories=160, ground_work=dict(sampled_transitions=480),
                            planning_counts=dict(model_uniform_draws=1920), outcomes=dict(LOST=160)),
                        reference_complete=True, paired_reference={'retained_reference_value': replica + life / 10}))
        # Actual V103 rotates method execution order; reversing rows also preserves the recovered order.
        traces[life] = raw[::-1]
        write_rows(folder / 'evaluation_games.jsonl.gz', traces[life])
        lifecycles.append(dict(id=life, evaluation=dict(methods=methods,
            validation=dict(roots=references, missing_roots=[]))))
    run = dict(status='complete', settings=dict(methods=list(module.METHODS), lifecycles=[9, 10],
        queries=module.QUERIES, evaluation_replicas=8, contrasts=[[module.CURRENT[0], 'H2_ONLY']]),
        lifecycles=lifecycles)
    work = dict(new_neural_model_fits=24, new_optimizer_steps=24000,
        newly_sampled_environment_transitions=123456, new_simulated_transitions=512000,
        inherited_training_environment_transitions=2048000)
    (source / 'run.json').write_text(json.dumps(run))
    (source / 'analysis.json').write_text(json.dumps(dict(complete=True, primary_complete=True, actual_executed_work=work)))
    return source, output, run, traces, work


def test_all_roots_original_events_and_eight_references_reused_without_sampling(tmp_path, monkeypatch):
    source, output, run, traces, work = retained_source(tmp_path)
    reads, original_rows = Counter(), module._rows
    def counted_rows(path):
        reads[str(path)] += 1
        return original_rows(path)
    monkeypatch.setattr(module, '_rows', counted_rows)
    roots, log = module.load_cohort(source, output)
    assert len(roots) == 32
    assert [root['id'] for root in roots] == [f'life_{life}_{query}_{replica}'
        for life in (9, 10) for query in module.QUERIES for replica in range(8)]
    assert reads == {str(source / f'life_{life}' / 'evaluation/evaluation_games.jsonl.gz'): 1 for life in (9, 10)}
    assert log['counts']['source_natural_games'] == log['counts']['raw_rows_read'] == 832
    assert log['counts']['retained_prediction_events'] == 800
    assert log['counts']['inherited_reference_roots'] == 8 and log['counts']['new_reference_roots'] == 24
    assert log['counts']['roots'] == 32 and log['inherited_v103_work'] == work
    assert log['source_terminal'] is True
    for field in ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                  'new_selector_calls', 'neural_candidate_predictions'):
        assert log['counts'][field] == 0
    for root in roots:
        assert len(root['natural']) == 26 and len(root['predictions']) == 25
        assert set(root['natural']['H2_ONLY']) == set(module.NATURAL_FIELDS)
        old = next(life for life in run['lifecycles'] if life['id'] == root['life'])['evaluation']
        for method, event in root['predictions'].items():
            raw = next(row for row in traces[root['life']] if row['method'] == method
                       and row['query'] == root['query'] and row['episode']['seed'] == root['source_seed'])
            assert event == raw['controller_events'][0]
        if root['episode'] < 2:
            reference = next(row for row in old['validation']['roots']
                if row['root']['query'] == root['query'] and row['root']['episode'] == root['episode'])
            assert root['reference_origin'] == 'inherited' and root['inherited_reference'] == reference
        else:
            assert root['reference_origin'] == 'new' and root['inherited_reference'] is None
    assert json.loads((output / 'cohort.json').read_text()) == dict(roots=roots, log=log)


def test_missing_natural_method_trace_is_not_silently_excluded(tmp_path):
    source, output, _, traces, _ = retained_source(tmp_path)
    write_rows(source / 'life_9/evaluation/evaluation_games.jsonl.gz', traces[9][1:])
    with pytest.raises(ValueError, match='complete method and query roster'):
        module.load_cohort(source, output)


@pytest.mark.parametrize('change', ['choice', 'root'])
def test_changed_decision_must_match_original_summary_and_trace(tmp_path, change):
    source, output, _, traces, _ = retained_source(tmp_path)
    raw = next(row for row in traces[9] if row['controller_events'])
    if change == 'choice':
        raw['controller_events'][0]['option'] = 'SNAKE_1'
        assert raw['controller_events'][0]['option'] != module.OPTIONS[25 % 5]
    else:
        raw['controller_events'][0]['board'] = list(raw['controller_events'][0]['board'])
        raw['controller_events'][0]['board'][0] += 1
    write_rows(source / 'life_9/evaluation/evaluation_games.jsonl.gz', traces[9])
    with pytest.raises(ValueError, match='retained decision differs'):
        module.load_cohort(source, output)


def test_inherited_reference_predictions_must_be_original_decisions(tmp_path):
    source, output, run, _, _ = retained_source(tmp_path)
    reference = run['lifecycles'][0]['evaluation']['validation']['roots'][0]
    reference['predictions']['PREFIX_ONLY_DIRECT']['value'] += 1
    (source / 'run.json').write_text(json.dumps(run))
    with pytest.raises(ValueError, match='inherited reference root or predictions differ'):
        module.load_cohort(source, output)
