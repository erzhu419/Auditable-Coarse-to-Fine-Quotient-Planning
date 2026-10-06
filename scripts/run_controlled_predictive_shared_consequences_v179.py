"""Fit one shared action-conditioned vector model on retained exact H3 labels."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import importlib
from itertools import combinations
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import controlled_predictive_shared_consequences_v179 as core
from scripts import run_controlled_predictive_exact_h3_v177 as prior

SOURCE = ROOT/'reports/controlled_predictive_afterstate_structure_v178'
RUNTIME = ROOT/'reports/v179_runtime_tmp'
OUTPUT = ROOT/'reports/controlled_predictive_shared_consequences_v179'
EPSILON = 1e-12


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def shared_choices(roots, model, inherited):
    choices, work = {}, Counter()
    for cohort in ('SOURCE', 'TARGET'):
        rows = []
        for root in roots[cohort]:
            decision = core.choose_action(model, root)
            work.update(decision['work']); work.update(decision['feature_work'])
            rows.append(dict(root_id=root['root_id'], mode='TREE',
                canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                fallback=decision['fallback'], decision=decision))
        rows.extend(deepcopy(row) for row in inherited[cohort] if row['mode'] in ('ONE', 'FALLBACK'))
        choices[cohort] = rows
    return choices, dict(work)


def paired_contrast(roots, shared, baseline):
    contrasts = {}
    for cohort in ('SOURCE', 'TARGET'):
        indices = [{row['root_id']: row for row in summary['cohorts'][cohort]['root_records']}
            for summary in (shared, baseline)]
        records, groups = [], defaultdict(list)
        for root in roots[cohort]:
            a, b = [index[root['root_id']]['modes']['TREE'] for index in indices]
            vector = [a['components'][k]-b['components'][k] for k in range(3)]
            row = dict(root_id=root['root_id'], source_id=root['source_id'], components=vector,
                utility=prior.utility(vector), shared_action=a['action'], baseline_action=b['action'],
                shared_regret=a['regret'], baseline_regret=b['regret'])
            records.append(row); groups[root['source_id']].append(vector)
        group_rows = [dict(source_id=group, roots=len(vectors), components=prior.mean_vectors(vectors),
            utility=prior.utility(prior.mean_vectors(vectors))) for group, vectors in sorted(groups.items())]
        aggregates = {}
        for weighting in ('ROOT_MEAN', 'DESIGN_GROUP_MEAN'):
            rows = records if weighting == 'ROOT_MEAN' else group_rows
            vector = prior.mean_vectors([row['components'] for row in rows])
            aggregates[weighting] = dict(components=vector, utility=prior.utility(vector))
        contrasts[cohort] = dict(roots=len(records), primary_weighting=(
            'DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN'), aggregates=aggregates,
            diagnostics=dict(improved_roots=sum(row['utility'] > EPSILON for row in records),
                worsened_roots=sum(row['utility'] < -EPSILON for row in records),
                equal_value_roots=sum(abs(row['utility']) <= EPSILON for row in records),
                action_changes=sum(row['shared_action'] != row['baseline_action'] for row in records),
                new_positive_regret_roots=sum(row['baseline_regret'] <= EPSILON < row['shared_regret'] for row in records),
                resolved_positive_regret_roots=sum(row['shared_regret'] <= EPSILON < row['baseline_regret'] for row in records)),
            groups=group_rows, root_records=records)
    return contrasts


def alias_bound(roots, labels, shared_summary):
    """Optimistic per-root ceiling after collapsing indistinguishable actions."""
    cohorts = {}
    for cohort in ('SOURCE', 'TARGET'):
        exact = {row['root_id']: row for row in labels[cohort]}
        index = {row['root_id']: row for row in shared_summary['cohorts'][cohort]['root_records']}
        records, grouped = [], defaultdict(list)
        for root in roots[cohort]:
            vectors = exact[root['root_id']]['action_components']
            classes = {}
            for action in core.ACTIONS:
                if action in root['legal_actions']:
                    classes.setdefault(tuple(root['action_features'][action]), []).append(action)
            feature_groups, pairs = [], []
            for features, actions in classes.items():
                representative = actions[0]
                for action in actions[1:]:
                    if root['immediate_rewards'][action] > root['immediate_rewards'][representative]+EPSILON:
                        representative = action
                feature_groups.append(dict(features=list(features), actions=actions, representative=representative))
                for a, b in combinations(actions, 2):
                    observed = [vectors[a][k]-vectors[b][k] for k in range(3)]
                    immediate = root['immediate_rewards'][a]-root['immediate_rewards'][b]
                    continuation = [observed[0]-immediate, *observed[1:]]
                    pairs.append(dict(actions=[a, b], features=list(features), true_components=observed,
                        immediate_reward_difference=immediate, continuation_components=continuation,
                        continuation_utility=prior.utility(continuation)))
            representatives = sorted((group['representative'] for group in feature_groups), key=core.ACTIONS.index)
            restricted = representatives[0]
            for action in representatives[1:]:
                if prior.utility(vectors[action]) > prior.utility(vectors[restricted])+EPSILON:
                    restricted = action
            modes = index[root['root_id']]['modes']
            difference = [vectors[restricted][k]-modes['ONE']['components'][k] for k in range(3)]
            row = dict(root_id=root['root_id'], source_id=root['source_id'], feature_groups=feature_groups,
                restricted_action=restricted, one_action=modes['ONE']['action'], oracle_action=modes['ORACLE']['action'],
                restricted_components=vectors[restricted], restricted_minus_one_components=difference,
                restricted_minus_one_utility=prior.utility(difference),
                oracle_minus_restricted=modes['ORACLE']['utility']-prior.utility(vectors[restricted]),
                same_feature_pairs=pairs)
            records.append(row); grouped[root['source_id']].append(row)
        def aggregate(rows):
            vector = prior.mean_vectors([row['restricted_components'] for row in rows])
            difference = prior.mean_vectors([row['restricted_minus_one_components'] for row in rows])
            return dict(restricted_components=vector, restricted_utility=prior.utility(vector),
                restricted_minus_one_components=difference, restricted_minus_one_utility=prior.utility(difference),
                oracle_minus_restricted=sum(row['oracle_minus_restricted'] for row in rows)/len(rows))
        group_rows = [dict(source_id=group, roots=len(rows), **aggregate(rows))
            for group, rows in sorted(grouped.items())]
        cohorts[cohort] = dict(roots=len(records), primary_weighting=(
            'DESIGN_GROUP_MEAN' if cohort == 'SOURCE' else 'ROOT_MEAN'),
            aggregates=dict(ROOT_MEAN=aggregate(records), DESIGN_GROUP_MEAN=aggregate(group_rows)),
            diagnostics=dict(identical_feature_pairs=sum(len(row['same_feature_pairs']) for row in records),
                roots_with_alias=sum(bool(row['same_feature_pairs']) for row in records),
                conflicting_continuation_pairs=sum(any(abs(x) > EPSILON for x in pair['continuation_components'])
                    for row in records for pair in row['same_feature_pairs']),
                lost_headroom_roots=sum(row['oracle_minus_restricted'] > EPSILON for row in records)),
            groups=group_rows, root_records=records)
    return cohorts


def summarize(roots, labels, choices, models):
    # This empty adapter reuses vector statistics only; SHARED is not a tree.
    summaries = {name: prior.summarize(roots, labels, choices[name], {'TREE': (
        dict(nodes=[], candidate_records=[]) if name == 'SHARED' else models[name])})
        for name in ('SHARED', 'STRUCTURE', 'RAW')}
    summaries['SHARED'].pop('learned_splits'); summaries['SHARED'].pop('candidate_reasons')
    summaries['SHARED']['model_kind'] = 'SHARED'
    return dict(schema='acfqp.shared_consequences.v179.summary', complete=True, **summaries,
        shared_minus_raw=paired_contrast(roots, summaries['SHARED'], summaries['RAW']),
        shared_minus_structure=paired_contrast(roots, summaries['SHARED'], summaries['STRUCTURE']),
        feature_alias=alias_bound(roots, labels, summaries['SHARED']),
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0)


def capture_code(output):
    importlib.import_module('scripts.analyze_controlled_predictive_shared_consequences_v179')
    paths = {Path(module.__file__).resolve() for module in list(sys.modules.values())
        if getattr(module, '__file__', None) and Path(module.__file__).suffix == '.py'
        and any(str(Path(module.__file__).resolve()).startswith(str(ROOT/folder)+'/')
            for folder in ('src', 'scripts'))}
    paths.update(ROOT/relative for relative in (
        'scripts/run_controlled_predictive_shared_consequences_v179.py',
        'scripts/analyze_controlled_predictive_shared_consequences_v179.py',
        'specs/SHARED_CONSEQUENCES_V179.md',
        'tests/test_shared_consequences_core_v179.py', 'tests/test_shared_consequences_runner_v179.py',
        'tests/test_shared_consequences_analysis_v179.py',
        'reports/v179_runtime_tmp/run_checks.py', 'reports/v179_runtime_tmp/run_stage.py'))
    for path in sorted(paths):
        destination = output/'source_code'/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, destination)
    save(output/'source_manifest.json', dict(files=[str(path.relative_to(ROOT)) for path in sorted(paths)]))


def run(output=OUTPUT):
    begun = perf_counter(); output.mkdir(parents=True, exist_ok=False)
    record = dict(schema='acfqp.shared_consequences.v179.run', status='preparing', phase_history=[],
        runtime=dict(python=sys.version.split()[0], executable=sys.executable), costs={},
        new_environment_samples=0, new_source_games=0, new_native_weight_updates=0,
        inherited_cost_refs=[dict(path=str(SOURCE/'run.json'), fields=['costs', 'inherited_cost_refs']),
            dict(path=str(SOURCE/'analysis.json'), fields=['costs']),
            dict(path=str(ROOT/'reports/v178_runtime_tmp/stage_checks.json'), fields=['attempts']),
            *[dict(path=str(ROOT/f'reports/v178_runtime_tmp/{kind}_checks.json'), fields=['attempts'])
                for kind in ('core', 'runner', 'analyzer')]],
        test_refs=[str(RUNTIME/f'{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    inputs, work = [], Counter()
    def read(path, name):
        raw = path.read_bytes(); target = output/'inputs'/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        work.update(json_read_operations=1, input_bytes_read=len(raw))
        inputs.append(dict(path=str(path), saved_ref=str(target.relative_to(output)), bytes=len(raw), phase=record['status']))
        save(output/'input_manifest.json', inputs); return json.loads(raw)
    def phase(name):
        record['status'] = name
        record['phase_history'].append(dict(phase=name, seconds_since_start=perf_counter()-begun,
            input_reads=work['json_read_operations']))
        save(output/'run.json', record); print(json.dumps(dict(event=name, seconds=perf_counter()-begun)), flush=True)
    try:
        capture_code(output)
        stage = read(ROOT/'reports/v178_runtime_tmp/stage_checks.json', 'stage_checks.json')
        if not stage['valid']:
            raise ValueError('required inherited V178 stage is not valid')
        inherited_run = read(SOURCE/'run.json', 'run.json')
        if inherited_run['status'] != 'complete':
            raise ValueError('inherited exact-label experiment is incomplete')
        roots = read(SOURCE/'roots.json', 'roots.json')
        old_models = read(SOURCE/'models.json', 'models.json')
        old_choices = read(SOURCE/'choices.json', 'choices.json')
        source_labels = read(ROOT/'reports/controlled_predictive_exact_h3_v177/source_labels.json', 'source_labels.json')
        feature_work = Counter(); tick = perf_counter()
        for cohort in ('SOURCE', 'TARGET'):
            for root in roots[cohort]:
                root['action_features'] = core.action_features_from_root(root, feature_work)
        record['costs']['feature_construction'] = dict(counts=dict(feature_work), seconds=perf_counter()-tick)
        save(output/'roots.json', roots)
        features = {root['root_id']: root['action_features'] for cohort in ('SOURCE', 'TARGET') for root in roots[cohort]}
        examples = [dict(deepcopy(row), action_features=features[row['root_id']]) for row in source_labels]
        phase('source_fit'); tick = perf_counter(); shared = core.fit_model(examples, 0)
        record['costs']['learning'] = dict(seconds=perf_counter()-tick,
            fit_counts=shared['fit_counts'], feature_counts=shared['feature_counts'])
        models = dict(SHARED=shared, STRUCTURE=old_models['STRUCTURE'], RAW=old_models['RAW'], ONE=old_models['ONE'])
        save(output/'models.json', models); phase('models_frozen')
        tick = perf_counter(); shared_rows, decision_work = shared_choices(roots, shared, old_choices['RAW'])
        record['costs']['choice_counts'] = decision_work; record['costs']['choice_seconds'] = perf_counter()-tick
        choices = dict(SHARED=shared_rows, STRUCTURE=old_choices['STRUCTURE'], RAW=old_choices['RAW'])
        save(output/'choices.json', choices); phase('target_choices_frozen'); phase('target_labels')
        labels = read(SOURCE/'labels.json', 'labels.json')
        if labels['SOURCE'] != source_labels:
            raise ValueError('source labels differ from their inherited standalone copy')
        save(output/'labels.json', labels); summary = summarize(roots, labels, choices, models)
        save(output/'summary.json', summary); record['costs']['input_counts'] = dict(work)
        record['seconds'] = perf_counter()-begun; phase('complete'); save(output/'run.json', record)
        print(json.dumps(summary['SHARED']['cohorts']['TARGET']['aggregates']['ROOT_MEAN']), flush=True)
        return record
    except Exception as error:
        record.update(status='failed', seconds=perf_counter()-begun,
            failure=dict(type=type(error).__name__, message=str(error)))
        record['costs']['input_counts'] = dict(work); save(output/'run.json', record); raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); run(args.output)


if __name__ == '__main__':
    main()
