"""Freeze V100 heldout roots and scalar predictions before independent resampling."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
from time import perf_counter

from acfqp.science.controlled_predictive_candidate_learning_v100 import CandidateModel, FAMILIES
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES


def _read(path):
    return json.loads(path.read_text())


def _records(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def load_cohort(source: Path, output: Path):
    """Use retained features and full-budget models; never fit or simulate here."""
    started = perf_counter()
    source, output = Path(source), Path(output)
    run = _read(source / 'run.json')
    analysis = _read(source / 'analysis.json')
    if run['status'] != 'complete' or not analysis['complete']:
        raise ValueError('V101 requires the completed V100 source')
    full_budget = max(run['settings']['budgets'])
    model_folder = output / 'models'
    model_folder.mkdir(parents=True, exist_ok=False)
    shared, roster = {}, []
    counts = Counter(new_neural_model_fits=0, new_tree_fits=0, new_optimizer_steps=0,
                     new_environment_transitions=0, new_model_transitions=0)
    inherited_acquisition = 0
    for lifecycle in sorted(run['lifecycles'], key=lambda row: row['id']):
        life = lifecycle['id']
        for allocation in sorted(lifecycle['allocations'], key=lambda row: -row['replicas']):
            replicas = allocation['replicas']
            stages = sorted(allocation['construction'], key=lambda row: row['budget'])
            full = stages[-1]
            if full['budget'] != full_budget:
                raise ValueError('allocation lacks its full-budget checkpoint')
            cutoff = full['episode_cutoff']
            records = []
            for stage in stages:
                folder = source / f'life_{life}' / f'replicas_{replicas}' / f"budget_{stage['budget']}"
                records.extend(_records(folder / 'candidate_roots.jsonl.gz'))
            counts['retained_candidate_records_read'] += len(records)
            eligible = [row for row in records if row['episode'] < cutoff]
            keys = [(row['query'], row['episode']) for row in eligible]
            coverage = {query: {role: sorted(row['episode'] for row in eligible
                if row['query'] == query and (row['episode'] % 5 == 4) == (role == 'heldout'))
                for role in ('training', 'heldout')} for query in QUERIES}
            if len(keys) != len(set(keys)) or coverage != full['cumulative_roots']:
                raise ValueError('retained root roster differs from full-budget construction')
            training = {query: coverage[query]['training'] for query in QUERIES}
            if training != full['fit_log']['training_episodes']:
                raise ValueError('full-budget fitting roster differs from retained training roots')
            models, metadata = {}, {}
            for family in FAMILIES:
                entry = allocation['model_metadata'][f'R{replicas}_{family}_DIRECT']
                source_path = Path(entry['path'])
                payload = _read(source_path)
                if (entry['replicas'] != replicas or entry['family'] != family
                        or entry['budget'] != full_budget or entry['episode_cutoff'] != cutoff
                        or payload['family'] != family or payload['checkpoint'] != cutoff
                        or payload['training_episodes'] != training):
                    raise ValueError('supplied full model family, age or training roots do not match')
                copied = model_folder / f'life_{life}_r{replicas}_{family.lower()}.json'
                shutil.copyfile(source_path, copied)
                models[family] = CandidateModel.from_payload(payload)
                metadata[family] = dict(entry, path=str(copied), source_path=str(source_path),
                    checkpoint=payload['checkpoint'], training_episodes=deepcopy(training))
                counts['model_loads'] += 1
                counts['model_copies'] += 1
            selected = [row for row in eligible if row['episode'] % 5 == 4]
            ids = []
            for record in sorted(selected, key=lambda row: (tuple(QUERIES).index(row['query']), row['episode'])):
                root_id = f"life_{life}_{record['query']}_{record['episode']}"
                ids.append(root_id)
                common = dict(id=root_id, life=life, query=record['query'], episode=record['episode'],
                    board=record['board'], retained_features=record['features'],
                    prefix_utilities=record['prefix_utilities'], prefix_seed=record['prefix_seed'])
                if root_id in shared:
                    if any(shared[root_id][key] != value for key, value in common.items()):
                        raise ValueError('shared root board, features or prefix stream differs between allocations')
                else:
                    shared[root_id] = dict(common, allocations=[])
                predictions = {}
                for family, model in models.items():
                    scores = model.score_candidates(record['features'], counts)
                    counts['prediction_calls'] += 1
                    option = OPTIONS[max(range(len(OPTIONS)), key=lambda i: scores[i])]
                    predictions[family] = dict(scores=scores, option=option,
                        score_semantics='rank_score' if family == 'PAIRWISE_RANK' else 'utility_estimate')
                shared[root_id]['allocations'].append(dict(replicas=replicas,
                    old_utilities=record['utilities'], predictions=predictions, model_metadata=deepcopy(metadata)))
            roster.append(dict(life=life, replicas=replicas, cutoff=cutoff, roots=ids,
                               training_episodes=training, heldout_episodes={q: coverage[q]['heldout'] for q in QUERIES}))
            inherited_acquisition += allocation['inherited_training_environment_transitions']
    roots = sorted(shared.values(), key=lambda row: (row['life'], tuple(QUERIES).index(row['query']), row['episode']))
    executed = analysis['actual_executed_work']
    inherited = {key: executed[key] for key in ('new_neural_model_fits', 'new_optimizer_steps',
        'new_tree_fits', 'new_training_environment_transitions', 'newly_sampled_environment_transitions',
        'new_simulated_transitions')}
    inherited.update(manifest=str(source / 'analysis.json'),
        inherited_training_environment_transitions=inherited_acquisition,
        scope='Previously executed source work; read from manifests and not repeated by V101.')
    log = dict(source=str(source), unique_roots=len(roots), allocated_roots=sum(len(r['allocations']) for r in roots),
        shared_roots=sum(len(r['allocations']) > 1 for r in roots), allocation_rosters=roster,
        counts=dict(counts), inherited_source_work=inherited, seconds=perf_counter() - started,
        scope='All full-budget heldout roots; saved features and models only; no reference outcomes used.')
    return roots, log
