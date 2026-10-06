"""Fixed four-unit nonlinear scorers against retained sixteen-unit scorers."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import (
    FragmentController, OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS, _utility,
)
from acfqp.science.controlled_predictive_fragment_experience_v83 import sample_root
from acfqp.science.controlled_predictive_candidate_data_v100 import CandidateSelector as PrefixSelector
from acfqp.science.controlled_predictive_capacity_data_v103 import load_batch
from acfqp.science.controlled_predictive_capacity_ranking_v103 import fit_models, CandidateModel, FAMILIES, STEPS
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT / 'reports/controlled_predictive_root_coverage_v98'
FEATURE_SOURCE = ROOT / 'reports/controlled_predictive_query_ranking_v100'
REPLICA_SOURCE = ROOT / 'reports/controlled_predictive_replica_ranking_v102'
WIDTHS = (4, 16)
LIFECYCLES, ALLOCATIONS, BUDGETS = (9, 10), (8, 4), (256000, 512000)
CURRENT_METHODS = tuple(f'R{r}_H{h}_{family}_DIRECT' for r in ALLOCATIONS for h in WIDTHS for family in FAMILIES)
METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT_METHODS + tuple(n + '_FROZEN_HALF' for n in CURRENT_METHODS)
REPLICAS, PREFIX_REPLICAS, REFERENCE_REPLICAS, VALIDATION_ROOTS_PER_QUERY, WORKERS = 8, 32, 32, 2, 4
CONTRASTS = [(f'R{r}_H4_{family}_DIRECT{suffix}', f'R{r}_H16_{family}_DIRECT{suffix}')
    for suffix in ('', '_FROZEN_HALF') for r in ALLOCATIONS for family in FAMILIES]
CONTRASTS += [(n, n + '_FROZEN_HALF') for n in CURRENT_METHODS]
CONTRASTS += [(n, 'H2_ONLY') for n in CURRENT_METHODS]
CONTRASTS += [(f'R{r}_H4_REPLICA_DIRECT{suffix}', 'PREFIX_ONLY_DIRECT')
    for suffix in ('', '_FROZEN_HALF') for r in ALLOCATIONS]


class CandidateSelector(PrefixSelector):
    def select(self, board, query, allowed=None, work=None):
        result = super().select(board, query, allowed, work)
        if self.model is not None:
            result['score_semantics'] = 'rank_score'
        return result


def baseline_matches(model, retained):
    current = model.to_payload()
    return all(current[field] == retained[field] for field in
        ('parameters','mean','scale','checkpoint','training_episodes','family','hidden','uniform_gamma'))


def prefix_seed(life, query, replica):
    return 230000000000 + life * 10000000 + tuple(QUERIES).index(query) * 1000000 + replica * 1000


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def write_row(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')


def gate_category(old, new):
    before, after = old not in (None, 'H2'), new not in (None, 'H2')
    if before and after:
        return 'same_fragment' if old == new else 'changed_fragment'
    return 'disabled' if before else 'enabled' if after else 'both_h2'


def evaluate_game(method, selector, rule, life, checkpoint, replica, query, max_steps=2000):
    seed = 10390000 + life * 100 + replica
    if '_DIRECT' in method:
        selector = CandidateSelector(selector, rule, prefix_seed(life, query, replica), replicas=PREFIX_REPLICAS)
    controller = FragmentController(selector, query, rule, random.Random(seed + 1000000),
        mode='H2_ONLY' if method == 'H2_ONLY' else 'FRAGMENT')
    paths = []

    def act(board, step):
        before = controller.fragment_actions
        action = controller.choose(board, step)
        paths.append('fragment' if controller.fragment_actions > before else 'H2')
        return action

    game = experience.run_episode(seed, act, max_steps=max_steps)
    option, start = controller.selected_option, controller.initiation_step
    budget = int(option.split('_')[1]) if option not in (None, 'H2') else 0
    expected = min(budget, game['steps_count'] - start) if start is not None else 0
    correct = paths == ['fragment' if start is not None and start <= i < start + budget else 'H2'
                        for i in range(game['steps_count'])]
    outcome = [game['return_score'] / 2048, float(game['status'] == 'LOST'), float(game['status'] == 'WON')]
    row = dict(seed=seed, replica=replica, query=query, score=game['return_score'], status=game['status'],
        steps=game['steps_count'], max_rank=max(game['final_board']), utility=_utility(outcome, QUERIES[query]),
        seconds=game['seconds'], environment_counts=game['work'], planning_counts=dict(controller.work),
        selected_option=option, initiation_step=start, fragment_actions=controller.fragment_actions,
        duration_budget=budget, controller_events=len(controller.events),
        selector_checkpoint=selector.checkpoint if selector else None,
        committed_length_matches=correct and controller.fragment_actions == expected)
    row['candidate_evaluation'] = selector.last_log if '_DIRECT' in method else None
    return row, dict(method=method, query=query, episode=game,
        controller_events=controller.events, action_paths=paths,
        model_prefixes=selector.last_prefixes if '_DIRECT' in method else [])


def evaluate_checkpoint(life, checkpoint, folder, deployed, rule, replicas=REPLICAS, max_steps=2000):
    names = METHODS
    methods = {name: dict(games=[], costs=dict(evaluation_seconds=0.0)) for name in names}
    contrasts = CONTRASTS
    validation_roots, missing_roots = [], []
    changes = {f'{left}_minus_{right}': [] for left, right in contrasts}
    wiring = dict(pretrigger_prefixes_match=True, committed_lengths_match=True,
        single_initiations=True, model_uniforms_aligned=True, same_choice_histories_match=True,
        simulated_prefixes_paired=True, simulated_work_matches=True)
    with gzip.open(folder / 'evaluation_games.jsonl.gz', 'wt') as output, \
            gzip.open(folder / 'model_prefixes.jsonl.gz', 'wt') as simulated:
        for replica in range(replicas):
            for qi, query in enumerate(QUERIES):
                offset = (life + checkpoint + replica + qi) % len(names)
                group, histories, prefix_histories = {}, {}, {}
                for method in names[offset:] + names[:offset]:
                    tick = perf_counter()
                    game, raw = evaluate_game(method, deployed[method], rule, life, checkpoint,
                        replica, query, max_steps=max_steps)
                    prefix_rows = raw.pop('model_prefixes')
                    if '_DIRECT' in method:
                        prefix_histories[method] = [(prefix['option'], prefix['replica'], prefix['spawn_seed'],
                            prefix['planning_seed'], prefix['steps'], prefix['status']) for prefix in prefix_rows]
                        log = game['candidate_evaluation']
                        if log is not None:
                            wiring['simulated_work_matches'] &= all(log['wiring'].values())
                    for prefix in prefix_rows:
                        write_row(simulated, dict(method=method, query=query, episode=replica, **prefix))
                    write_row(output, raw)
                    methods[method]['costs']['evaluation_seconds'] += perf_counter() - tick
                    methods[method]['games'].append(game)
                    group[method] = game, raw
                    histories[method] = [(s['board'], s['action'], s['next_board']) for s in raw['episode']['steps']]
                    wiring['committed_lengths_match'] &= game['committed_length_matches']
                    wiring['single_initiations'] &= game['controller_events'] <= 1
                    wiring['model_uniforms_aligned'] &= game['planning_counts']['model_uniform_draws'] == 4 * game['steps']
                wiring['simulated_prefixes_paired'] &= all(
                    history == prefix_histories['PREFIX_ONLY_DIRECT'] for history in prefix_histories.values())
                h2_game, h2_raw = group['H2_ONLY']
                steps = h2_raw['episode']['steps']
                trigger = next((i for i, step in enumerate(steps)
                    if step['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                if replica < VALIDATION_ROOTS_PER_QUERY:
                    metadata = dict(life=life, query=query, episode=replica)
                    if trigger is None:
                        missing_roots.append(metadata)
                    else:
                        validation_roots.append(dict(metadata, board=steps[trigger]['board'],
                            source_seed=h2_game['seed'], step=trigger,
                            predictions={name: group[name][1]['controller_events'][0] for name in names[1:]}))
                for method in names[1:]:
                    game, raw = group[method]
                    if trigger is None:
                        same = histories[method] == histories['H2_ONLY'] and game['initiation_step'] is None
                    else:
                        same = (histories[method][:trigger] == histories['H2_ONLY'][:trigger]
                            and game['initiation_step'] == trigger
                            and raw['episode']['steps'][trigger]['board'] == steps[trigger]['board'])
                    wiring['pretrigger_prefixes_match'] &= same
                for left, right in contrasts:
                    old, new = group[right][0], group[left][0]
                    category = gate_category(old['selected_option'], new['selected_option'])
                    if category in ('both_h2', 'same_fragment'):
                        wiring['same_choice_histories_match'] &= histories[right] == histories[left]
                    changes[f'{left}_minus_{right}'].append(dict(seed=new['seed'], query=query, replica=replica,
                        category=category, old_option=old['selected_option'], new_option=new['selected_option']))
                print(json.dumps(dict(phase='paired_games', lifecycle=life, checkpoint=checkpoint,
                    query=query, replica=replica, scores={name: group[name][0]['score'] for name in names})), flush=True)
    if not all(wiring.values()):
        raise ValueError(f'controller execution mismatch: {wiring}')
    return dict(methods=methods, wiring=wiring, gate_changes=changes), validation_roots, missing_roots


def validate_roots(roots, missing, folder, rule):
    started = perf_counter()
    save(folder / 'validation_cohort.json', dict(roots=roots, missing_roots=missing))
    records = []
    with gzip.open(folder / 'validation_games.jsonl.gz', 'wt') as output:
        for retained in roots:
            root = {key: value for key, value in retained.items() if key != 'predictions'}
            # Selection is the actual natural-game event, fixed before these independent outcomes.
            _, raw, log = sample_root(root, rule, 103000 + root['life'], replicas=REFERENCE_REPLICAS)
            for row in raw:
                write_row(output, dict(root=root, **row))
            complete = (not log['censored_root'] and len(raw) == REFERENCE_REPLICAS * len(OPTIONS)
                and all(row['game']['status'] in ('WON', 'LOST') for row in raw))
            records.append(dict(root=root, predictions=retained['predictions'], terminal_log=log,
                reference_complete=complete, paired_reference=log['pair_deltas']))
            print(json.dumps(dict(phase='independent_reference', lifecycle=root['life'],
                query=root['query'], episode=root['episode'], complete=complete,
                transitions=log['ground_work'].get('sampled_transitions', 0))), flush=True)
    return dict(roots=records, missing_roots=missing, seconds=perf_counter() - started,
                new_selector_calls=0, new_model_transitions=0)


def construct_allocation(life, replicas, directory, payload):
    start = perf_counter()
    folder = directory / f'life_{life}' / f'replicas_{replicas}'
    folder.mkdir(parents=True, exist_ok=True)
    records, construction, metadata = [], [], {}
    cursor = 0
    for budget in BUDGETS:
        stage_dir = folder / f'budget_{budget}'
        stage_dir.mkdir()
        relative = Path(f'life_{life}') / f'replicas_{replicas}' / f'budget_{budget}'
        source = REPLICA_SOURCE / relative
        batch, data = load_batch(source, stage_dir)
        if data['start_cursor'] != cursor:
            raise ValueError('source batches must remain incremental')
        cursor = data['next_cursor']
        records.extend(batch)
        cutoff = data['episode_cutoff']
        models, log = fit_models(records, cutoff, hidden=4)
        suffix = '' if budget == BUDGETS[-1] else '_FROZEN_HALF'
        equivalents, sources = {}, {}
        for family in FAMILIES:
            retained_path = source / f'r{replicas}_{family.lower()}_direct{suffix.lower()}_model.json'
            retained = json.loads(retained_path.read_text())
            frozen = CandidateModel.from_payload(retained)
            equivalents[family] = baseline_matches(frozen, retained)
            sources[family] = str(retained_path)
            for hidden, model in ((4, models[family]), (16, frozen)):
                name = f'R{replicas}_H{hidden}_{family}_DIRECT{suffix}'
                path = stage_dir / f'{name.lower()}_model.json'
                row = model.to_payload()
                if (row['hidden'] != hidden or row['checkpoint'] != cutoff or row['family'] != family
                        or row['training_episodes'] != log['training_episodes']):
                    raise ValueError('capacity model width, family, age or training roster mismatch')
                save(path, row)
                metadata[name] = dict(replicas=replicas, budget=budget, episode_cutoff=cutoff,
                    family=family, hidden=hidden, parameter_count=hidden * 123, path=str(path))
        coverage = {q: {role: sorted(r['episode'] for r in records if r['query'] == q
            and (r['episode'] % 5 == 4) == (role == 'heldout')) for role in ('training','heldout')} for q in QUERIES}
        stage = dict(budget=budget, episode_cutoff=cutoff, data=data, fit_log=log,
            frozen_fit_log=json.loads((source / 'construction.json').read_text())['fit_log'],
            cumulative_roots=coverage, cumulative_root_count=len(records),
            baseline_equivalence=equivalents, baseline_sources=sources, frozen_baseline_count=3)
        construction.append(stage)
        save(stage_dir / 'construction.json', stage)
        if not all(equivalents.values()):
            raise ValueError('frozen wide models differ from V102')
        print(json.dumps(dict(phase='candidate_fit', lifecycle=life, replicas=replicas, budget=budget,
            roots=len(records), training_roots=log['training_roots'], hidden=4,
            frozen_baselines_match=all(equivalents.values()),
            losses={k:v['final_loss'] for k,v in log['models'].items()})), flush=True)
    result = dict(replicas=replicas, construction=construction, model_metadata=metadata,
        new_neural_model_fits=sum(s['fit_log']['counts']['neural_model_fits'] for s in construction),
        frozen_model_payloads_reused=sum(s['frozen_baseline_count'] for s in construction),
        new_training_environment_transitions=0, inherited_training_environment_transitions=sum(
            s['data']['inherited_acquisition']['used_transitions'] for s in construction), actual_wall_seconds=perf_counter()-start)
    save(folder / 'run.json', result)
    return result

def lifecycle_evaluation(life, directory, payload, allocations):
    start = perf_counter()
    folder = directory / f'life_{life}' / 'evaluation'
    folder.mkdir()
    rule = LearnedDynamics.from_payload(payload)
    metadata = {n:m for allocation in allocations for n,m in allocation['model_metadata'].items()}
    deployed = {'H2_ONLY': None, 'PREFIX_ONLY_DIRECT': None}
    for name in METHODS[2:]:
        row = metadata[name]
        model = CandidateModel.from_payload(json.loads(Path(row['path']).read_text()))
        if (model.checkpoint != row['episode_cutoff'] or model.family != row['family']
                or model.to_payload()['hidden'] != row['hidden']):
            raise ValueError('model width, family and age do not match deployment')
        deployed[name] = model
    save(folder / 'deployment.json', dict(model_metadata=metadata))
    evaluation, roots, missing = evaluate_checkpoint(life, BUDGETS[-1], folder, deployed, rule)
    evaluation['model_metadata'] = metadata
    evaluation['validation'] = validate_roots(roots, missing, folder, rule)
    result = dict(id=life, allocations=allocations, evaluation=evaluation,
        evaluation_wall_seconds=perf_counter()-start)
    save(directory / f'life_{life}' / 'run.json', result)
    return result


def snapshot(directory):
    paths = ['scripts/run_controlled_predictive_capacity_ranking_v103.py',
        'scripts/analyze_controlled_predictive_capacity_ranking_v103.py',
        'specs/CAPACITY_RANKING_V103.md', 'scripts/run_controlled_predictive_query_ranking_v100.py',
        'scripts/analyze_controlled_predictive_query_ranking_v100.py',
        'scripts/run_controlled_predictive_replica_ranking_v102.py',
        'scripts/analyze_controlled_predictive_replica_ranking_v102.py',
        'specs/REPLICA_RANKING_V102.md',
        'scripts/analyze_controlled_predictive_bellman_v94.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py', 'specs/QUERY_RANKING_V100.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name,version in (
        ('capacity_ranking',103),('capacity_data',103),('replica_ranking',102),('replica_data',102),('candidate_learning',100),('candidate_data',100),('paired_continuation_value',92),
        ('direct_value',95),('continuation_data',91),('joint_fragments',84),('fragments',83),
        ('fragment_experience',83),('policy_advantage',81),('decision_experience',78),('lifelong',77),
        ('lifelong_experience',77),('lifelong_planner',77),('relational_dynamics',69),
        ('effect_contract',74),('grouped_contract',73),('local_contract',72))]
    paths += ['src/acfqp/domains/standard_2048.py','src/acfqp/domains/g2048.py','src/acfqp/core.py']
    for relative in paths:
        path = directory / 'source' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)


def run(directory):
    start = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    payload = json.loads((SOURCE / 'supplied_dynamics.json').read_text())
    save(directory / 'supplied_dynamics.json', payload)
    report = dict(schema='acfqp.capacity_ranking.v103',status='running', platform=platform.platform(),
        executable=sys.executable, python=sys.version, inherited_data=str(SOURCE), inherited_feature_data=str(FEATURE_SOURCE),
        inherited_replica_data=str(REPLICA_SOURCE),
        inherited_v102_work=json.loads((REPLICA_SOURCE / 'analysis.json').read_text())['actual_executed_work'],
        inherited_v100_work=json.loads((FEATURE_SOURCE / 'analysis.json').read_text())['actual_executed_work'],
        settings=dict(lifecycles=list(LIFECYCLES),allocations=list(ALLOCATIONS),budgets=list(BUDGETS),
            methods=list(METHODS),contrasts=CONTRASTS,queries=QUERIES,evaluation_replicas=REPLICAS,
            prefix_replicas=PREFIX_REPLICAS,reference_replicas=REFERENCE_REPLICAS,
            validation_roots_per_query=VALIDATION_ROOTS_PER_QUERY,horizon=4,optimizer_steps=STEPS,
            feature_dim=121,hidden=4,widths=list(WIDTHS),frozen_hidden=16,learning_rate=.01,
            l2_coefficient=.001/1968,l2_reference_parameters=1968,initialization_seed=10001,
            training_model_prefixes_reused=True,reference_block_size=16,natural_seed_base=10390000,
            synthetic_seed_base=230000000000,reference_life_base=103000,max_steps=2000,workers=WORKERS),
        allocations=[],lifecycles=[])
    save(directory / 'run.json',report)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks={pool.submit(construct_allocation,life,r,directory,payload):life for life in LIFECYCLES for r in ALLOCATIONS}
        collected={life:[] for life in LIFECYCLES}
        for future in as_completed(tasks):
            life=tasks[future]; allocation=future.result()
            collected[life].append(allocation)
            report['allocations'].append(dict(life=life,**allocation))
            save(directory/'run.json',report)
        futures=[pool.submit(lifecycle_evaluation,life,directory,payload,
            sorted(collected[life],key=lambda r:-r['replicas'])) for life in LIFECYCLES]
        for future in as_completed(futures):
            report['lifecycles'].append(future.result())
            report['lifecycles'].sort(key=lambda r:r['id'])
            report['actual_wall_seconds']=perf_counter()-start
            save(directory/'run.json',report)
    report.update(status='complete',actual_wall_seconds=perf_counter()-start)
    save(directory/'run.json',report)
    print(json.dumps(dict(phase='complete',seconds=report['actual_wall_seconds'])),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output)
