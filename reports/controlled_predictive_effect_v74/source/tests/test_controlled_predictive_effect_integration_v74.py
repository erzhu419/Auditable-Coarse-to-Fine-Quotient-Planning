"""One fixed H3 fixture checks unchanged models and both new procedural routers."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOARD = (1, 1, 3, 4, 3, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10)
LEDGER = dict(board=list(BOARD), builds=[], rule_compilations=0, route_count=0,
    routes_by_h=Counter(), reference_support_work=Counter(),
    reference_routing_work=Counter(), routing_work={})


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def science(filename, name):
    return module(ROOT / 'src/acfqp/science' / filename, name)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = ROOT / 'reports/controlled_predictive_effect_v74.integration_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope='One fixed dense development board at H3; no registered target roots.',
        ground_calls=0, fit_calls=0, planning_calls=0, model_builds=len(LEDGER['builds']), **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def active_encoding(build):
    return {key: cell for key, cell in build.encoding.items() if build.model.terminal[cell] == 'ACTIVE'}


def test_early_and_shared_effects_keep_exact_cells_joints_and_routes():
    contract = science('controlled_predictive_compositional_contract_v69.py', 'v74_test_contract')
    dynamics = science('controlled_predictive_relational_dynamics_v69.py', 'v74_test_dynamics')
    terminal_module = science('controlled_predictive_symbolic_successors_v71.py', 'v74_test_terminal')
    baseline_module = science('controlled_predictive_local_builder_v72.py', 'v74_test_baseline')
    late_module = science('controlled_predictive_grouped_builder_v73.py', 'v74_test_late')
    effect_module = science('controlled_predictive_effect_builder_v74.py', 'v74_test_effect')
    worker = module(ROOT / 'scripts/query_controlled_predictive_effect_v74.py', 'v74_test_worker')
    rule = dynamics.LearnedDynamics.from_payload(json.loads((ROOT /
        'reports/controlled_predictive_composition_v69/learned_rule.json').read_text()))
    terminal = terminal_module.compile_rule(rule)
    LEDGER['rule_compilations'] += 1

    baseline = baseline_module.build_model(BOARD, 3, rule, terminal, 'COMPOSED')
    LEDGER['builds'].append(dict(method='V72_BASE', counts=baseline.counts,
                                elapsed_seconds=baseline.elapsed_seconds))
    baseline_payload = contract.model_payload(baseline)
    expected = active_encoding(baseline)
    reference_package = dict(kernel=baseline_payload, router=dict(kind='LOCAL_H1',
        labels=[[h, list(board), cell] for (h, board), cell in expected.items()]))
    compiled, loaded_rule = contract.load_model(baseline_payload)
    reference_route, _ = worker.make_router(reference_package, compiled, loaded_rule)
    # Recover only this fixture's omitted H1 observations using V72's decoder.
    for (h, observation), _ in tuple(expected.items()):
        if h != 2:
            continue
        _, moves = rule.classify(observation, LEDGER['reference_support_work'])
        for _, moved, score in moves:
            for _, status, child, _ in terminal.successors(moved, score, 1, LEDGER['reference_support_work']):
                if status == 'ACTIVE':
                    cell = reference_route(child, 1, LEDGER['reference_routing_work'])
                    assert cell is not None
                    expected[1, child] = cell

    late = late_module.build_model(BOARD, 3, rule, terminal, grouping=True)
    LEDGER['builds'].append(dict(method='V73_LATE', counts=late.counts,
                                elapsed_seconds=late.elapsed_seconds))
    assert contract.model_payload(late) == baseline_payload
    expected_high = {key: cell for key, cell in expected.items() if key[0] > 2}
    for shared in (False, True):
        name = 'V74_SHARED' if shared else 'V74_EARLY'
        candidate = effect_module.build_model(BOARD, 3, rule, terminal, share_successors=shared)
        LEDGER['builds'].append(dict(method=name, counts=candidate.counts,
                                    elapsed_seconds=candidate.elapsed_seconds))
        assert contract.model_payload(candidate) == baseline_payload
        assert active_encoding(candidate) == active_encoding(late) == expected_high
        assert candidate.counts['unique_h2_geometries'] == sum(h == 2 for h, _ in expected)
        assert all(h > 2 for h, _ in candidate.encoding)
        package = dict(schema='acfqp.observation_package.v74', kernel=contract.model_payload(candidate),
            router=dict(kind='SHARED_EFFECT_H2' if shared else 'EFFECT_H2', grouping=True,
                labels=[[h, list(board), cell] for (h, board), cell in expected_high.items()]))
        compiled, candidate_rule = contract.load_model(package['kernel'])
        route, _ = worker.make_router(package, compiled, candidate_rule)
        work = Counter()
        for (h, observation), cell in expected.items():
            LEDGER['route_count'] += 1
            LEDGER['routes_by_h'][h] += 1
            assert route(observation, h, work) == cell
        LEDGER['routing_work'][name] = dict(work)
    assert len(LEDGER['builds']) == 4
    assert all(LEDGER['routes_by_h'][h] > 0 for h in (1, 2, 3))
