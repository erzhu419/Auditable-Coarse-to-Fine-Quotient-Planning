"""Validate fixed consequence candidates by actual source-game planning utility."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import gzip
import importlib
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_utility_selection_v118 import select_utility
from acfqp.science.controlled_predictive_utility_history_v118 import source_capsule
from acfqp.science.controlled_predictive_context_experience_v116 import policy_game
from acfqp.science.controlled_predictive_lifelong_experience_v77 import targets
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from scripts.run_controlled_predictive_consolidation_v117 import bound_model, save, append, PHASES, QUERIES, POLICIES

SOURCE_RUN = ROOT / 'reports/controlled_predictive_consolidation_v117/run.json'
TRACKS = ('SHARED', 'SPLIT', 'MSE_SELECTED', 'UTILITY_SELECTED')
METHODS = ('H2_ONLY',) + tuple(track + '_PLAN' for track in TRACKS)
CANDIDATES = ('KEEP', 'NEW_SHARED', 'NEW_SPLIT')
LIFECYCLES = (0, 1, 2, 3)
VALIDATION_REPLICAS, PREDICTION_REPLICAS, CONTROL_REPLICAS, MAX_STEPS, WORKERS = 4, 2, 2, 2000, 4
VERSION_BASE, PLANNING_OFFSET = 118 * 100_000_000, 50_000_000


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_utility_consolidation_v118')
    files = {Path(__file__).resolve(), ROOT / 'specs/UTILITY_CONSOLIDATION_V118.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                files.add(path)
    files.update((ROOT / 'src/acfqp/science').glob('controlled_predictive_*contract_v7[234].py'))
    for path in files:
        target = directory / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def control_game(method, query, replica, seed, p_true, rule, module_id, payload):
    model = None if payload is None else bound_model(payload, module_id)
    fallback = model is not None and not model.can_route(module_id)
    knowledge = None if fallback else model
    rng, work, decisions = random.Random(seed + PLANNING_OFFSET), Counter(), []
    def act(board, step):
        chosen = planner.choose(board, QUERIES[query], knowledge, rule, rng, depth=2, work=work)
        decisions.append({key: chosen[key] for key in ('action', 'value', 'metrics', 'policy', 'branches', 'action_values')})
        return chosen['action']
    game = run_episode(seed, act, p_true, MAX_STEPS)
    q = QUERIES[query]
    result = dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=q['reward_weight'] * game['return_score'] / 2048
            - q['failure_penalty'] * (game['status'] == 'LOST') + q['goal_bonus'] * (game['status'] == 'WON'),
        environment_counts=game['work'], planning_counts=dict(work),
        prediction_counts={} if model is None else dict(model.counts), seconds=game['seconds'],
        fallback_h2=fallback, routed_module_id=module_id)
    row = dict(method=method, query=query, replica=replica, seed=seed, result=result)
    return row, dict(**row, episode=game, decisions=decisions)


def source_validation(life, batch, models, previous, rule, module_id, stream):
    candidates = dict(KEEP=previous, NEW_SHARED=models['SHARED'], NEW_SPLIT=models['SPLIT'])
    games = []
    for candidate in CANDIDATES:
        for query in QUERIES:
            for replica in range(VALIDATION_REPLICAS):
                seed = VERSION_BASE + 1_000_000 + life * 100000 + batch * 10000 + replica
                row, raw = control_game(candidate, query, replica, seed, PHASES[batch][1], rule,
                    module_id, candidates[candidate])
                row['candidate'] = raw['candidate'] = candidate
                games.append(row); append(stream, raw)
    choice = select_utility(games, queries=tuple(QUERIES), replicas=VALIDATION_REPLICAS)
    selected = bound_model(candidates[choice['selected_candidate']], module_id).to_payload()
    return selected, choice, games


def prediction_games(life, batch, template, module_id, versions, stream):
    models = {version: {track: bound_model(payload, module_id) for track, payload in group.items()}
        for version, group in versions.items()}
    rows = []
    for policy_index, policy in enumerate(POLICIES):
        for replica in range(PREDICTION_REPLICAS):
            seed = VERSION_BASE + 2_000_000 + life * 100000 + batch * 10000 + policy_index * 100 + replica
            game, work = policy_game(seed, policy, template, PHASES[batch][1], MAX_STEPS)
            records = targets(game, policy, policy_index * PREDICTION_REPLICAS + replica, stride=4, horizons=(30,31))
            for row in records:
                row['context_module_id'] = module_id
            predictions = {version: {track: model.predict_records(records) for track, model in group.items()}
                for version, group in models.items()}
            evaluated = [dict(record, predictions={version: {track: values[i] for track, values in group.items()}
                for version, group in predictions.items()}) for i, record in enumerate(records)]
            rows.append(dict(policy=policy, replica=replica, seed=seed, status=game['status'],
                steps=game['steps_count'], environment_counts=game['work'], planning_counts=work,
                seconds=game['seconds'], records=evaluated))
            append(stream, dict(policy=policy, replica=replica, episode=game))
    return rows, {version: {track: dict(model.counts) for track, model in group.items()}
        for version, group in models.items()}


def lifecycle_run(source, directory, dynamics_payload):
    started, life = perf_counter(), source['life']
    folder = directory / f'life_{life}'; folder.mkdir()
    template = LearnedDynamics.from_payload(dynamics_payload)
    previous, origin, archives = None, None, {}
    source_before = deepcopy(source)
    result = dict(life=life, phases=[], checks={})
    for batch, source_phase in enumerate(source['phases']):
        name, p_true = PHASES[batch]
        inherited = source_phase['checkpoint']
        router = SpawnMemory.from_payload(inherited['router_payload'])
        module_id, rule = router.module_id, router.to_rule(template)
        router_before = deepcopy(router.to_payload())
        phase_dir = folder / name; phase_dir.mkdir()
        cp = dict(phase=name, router_p4=float(dict(rule.spawn_distribution)[2]), router_module_id=module_id,
            models=deepcopy(inherited['models']), mse_selected_origin=deepcopy(inherited['mse_selected_origin']))
        phase = dict(name=name, p4=p_true, checkpoint=cp); result['phases'].append(phase)
        with gzip.open(phase_dir / 'source_validation_games.jsonl.gz', 'wt') as stream:
            if batch == 0:
                selected = bound_model(cp['models']['SHARED'], module_id).to_payload()
                choice = dict(selected_candidate='NEW_SHARED', selection_complete=True, summaries={},
                    acceptance={}, reason='bootstrap_shared')
                games = []
            else:
                selected, choice, games = source_validation(life, batch, cp['models'], previous, rule, module_id, stream)
        if choice['selected_candidate'] != 'KEEP':
            origin = dict(batch=batch, mode=choice['selected_candidate'].removeprefix('NEW_'))
        cp.update(selection=choice, source_validation_games=games, utility_selected_origin=deepcopy(origin))
        cp['models']['UTILITY_SELECTED'] = deepcopy(selected)
        previous = deepcopy(selected)
        versions = dict(CURRENT=cp['models'])
        if name == 'A_RETURN':
            versions.update(archives)
        before, archives_before = deepcopy(cp['models']), deepcopy(archives)
        with gzip.open(phase_dir / 'predictive_games.jsonl.gz', 'wt') as stream:
            cp['predictive_tests'], cp['prediction_counts'] = prediction_games(
                life, batch, template, module_id, versions, stream)
        cp['control_evaluations'] = []
        methods = METHODS + (('UTILITY_B_END_PLAN',) if name == 'A_RETURN' else ())
        with gzip.open(phase_dir / 'control_games.jsonl.gz', 'wt') as stream:
            for method in methods:
                if method == 'H2_ONLY':
                    payload = None
                elif method == 'UTILITY_B_END_PLAN':
                    payload = archives['B_END']['UTILITY_SELECTED']
                else:
                    payload = cp['models'][method.removesuffix('_PLAN')]
                for query in QUERIES:
                    for replica in range(CONTROL_REPLICAS):
                        seed = VERSION_BASE + 3_000_000 + life * 100000 + batch * 10000 + replica
                        row, raw = control_game(method, query, replica, seed, p_true, rule, module_id, payload)
                        cp['control_evaluations'].append(row); append(stream, raw)
        cp['checks'] = dict(new_games_never_update_router=router_before == router.to_payload(),
            evaluation_preserves_models=before == cp['models'] and archives_before == archives,
            deterministic_program_preserved=rule.program == template.program)
        if name in ('A', 'B'):
            archives[name + '_END'] = deepcopy(cp['models'])
        save(folder / 'lifecycle.json', result)
        print(json.dumps(dict(event='phase_complete', life=life, phase=name, selected=choice['selected_candidate'],
            complete=choice['selection_complete'], origin=origin)), flush=True)
    result['checks'] = dict(inherited_source_unchanged=source_before == source)
    result['actual_wall_seconds'] = perf_counter() - started
    save(folder / 'lifecycle.json', result)
    return result


def run(directory):
    started = perf_counter(); directory.mkdir(parents=True, exist_ok=False)
    capsule = source_capsule(json.loads(SOURCE_RUN.read_text()))
    save(directory / 'source_capsule.json', capsule); snapshot(directory)
    settings = dict(lifecycles=list(LIFECYCLES), phases=[dict(name=n,p4=p) for n,p in PHASES],
        policies=list(POLICIES), tracks=list(TRACKS), methods=list(METHODS), candidates=list(CANDIDATES), queries=QUERIES,
        horizons=[30,31], stride=4, source_validation_replicas=VALIDATION_REPLICAS,
        prediction_replicas=PREDICTION_REPLICAS, control_replicas=CONTROL_REPLICAS, max_steps=MAX_STEPS,
        workers=WORKERS, version_base=VERSION_BASE, planning_offset=PLANNING_OFFSET)
    report = dict(schema='acfqp.utility_consolidation.v118.run', status='running', settings=settings,
        source_capsule_file='source_capsule.json', source_run_path=str(SOURCE_RUN),
        platform=platform.platform(), executable=sys.executable, python=sys.version, lifecycles=[],
        runner_checks=dict(no_new_fits=True, no_old_outer_evidence_in_capsule=True,
            fixed_source_utility_rule=True, separated_new_environment_and_planning_streams=True))
    save(directory / 'run.json', report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(lifecycle_run, source, directory, capsule['supplied_dynamics']): source['life']
            for source in capsule['lifecycles']}
        for future in as_completed(tasks):
            life = future.result()
            if life['life'] != tasks[future]:
                raise ValueError('lifecycle identity differs from submitted history')
            report['lifecycles'].append(life); report['lifecycles'].sort(key=lambda row: row['life'])
            report['actual_wall_seconds'] = perf_counter() - started
            save(directory / 'run.json', report)
    report['status'] = 'complete'; report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    print(json.dumps(dict(status='complete', lifecycles=len(report['lifecycles']), seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
