"""Budget-matched old/new factual replay after the same retained A1 critic."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from .b_mechanism_v299 import sum_counts
from .experience_replay_analysis_v307 import ARMS, BOOTSTRAP_SEED, INTERVAL_SCOPE, summarize
from .experience_selection_v307 import build_replay
from .history_control_v304 import scientific_identity
from .native_replay_fit_v307 import fit_masked_split
from .native_split_risk_v301 import fit_split, evaluate_split
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .policy_actor_data_v306 import FixedPolicyData
from .policy_data_v306 import new_head, retained_a1
from .retained_critic_v287 import compact_dataset


def evaluation_seed(life, episode):
    return 307900000000+life*1000000+episode


def configuration(a1_summary, current_summary):
    return dict(schema='acfqp.experience_replay_freeze.v307',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/EXPERIENCE_REPLAY_V307.md'),
        a1_summary=str(Path(a1_summary).resolve()), current_summary=str(Path(current_summary).resolve()),
        lifecycles=list(range(64)), parents=4, arms=ARMS, retained_actor='CURRENT_DATA', true_p_four=.1,
        alpha=.0025, query=QUERY, representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK',
        initialization='IDENTICAL_RETAINED_V303_A1_REWARD_AND_RISK',
        training_budget='ALL_CURRENT_FIT_NONWINNING_AFTERSTATES_PER_LIFECYCLE',
        mixed_quotas='FLOOR_HALF_OLD_A1_AND_REMAINING_CURRENT',
        game_selection='FIT_INDEX_MIDPOINT_BREADTH_FIRST_FULL_GAMES_THEN_ONE_QUANTILE_MASK_PER_SOURCE',
        game_order='CHRONOLOGICAL_WITHIN_SOURCE_THEN_OLD_NEW_ALTERNATING_OLD_FIRST',
        targets='ORIGINAL_COMPLETE_NATURAL_GAME_SUFFIX_AND_WIN_LABEL',
        fit_scope='ORIGINAL_80_PERCENT_COMPLETE_GAME_PREFIX_NO_HELDOUT_OR_TAIL',
        planning_probability='FIXED_ORIGINAL_A1_OBSERVED_BELIEF',
        seed_evaluation=307900000000, evaluation_games=32, max_steps=MAX_STEPS,
        bootstrap_draws=20000, bootstrap_seed=BOOTSTRAP_SEED,
        primary='MIXED_REPLAY_minus_NEW_ONLY', retention='MIXED_REPLAY_minus_A1_FROZEN_CI_LOWER_NONNEGATIVE',
        interval_scope=INTERVAL_SCOPE, new_training_environment_observations=0, new_evaluation_games=8192,
        stop_rule='NO_MIXING_ALPHA_BUDGET_OR_CHECKPOINT_TUNING_ON_THE_RETAINED_COHORTS')


def retained_current(receipt, lives, reconstruction):
    completed = []; data = None; active = None
    with gzip.open(receipt['trace_file'], 'rt') as stream:
        for line in stream:
            row = json.loads(line); reconstruction['canonical_rows_read'] += 1
            if row['arm']!='CURRENT_DATA':
                reconstruction['skipped_rows'] += 1
                continue
            life = row['lifecycle']
            if data is None:
                data = FixedPolicyData(life, receipt['parent']); active = life
            if life!=active or row['parent']!=receipt['parent']:
                raise ValueError('Retained current-policy history order changed')
            if row['kind']=='TRAIN':
                data.consume(row)
            elif row['kind']=='ACQUISITION_SNAPSHOT':
                previous = lives[life]['acquisitions']['CURRENT_DATA']
                if row['training']!=previous['training'] or row['snapshot']!=previous['snapshot']:
                    raise ValueError('Retained current-policy acquisition changed')
                dataset = data.finish(row['training'])
                dataset['costs']['processing_cpu_seconds'] = lives[life]['datasets']['CURRENT_DATA']['costs']['processing_cpu_seconds']
                if compact_dataset(dataset)!=lives[life]['datasets']['CURRENT_DATA']:
                    raise ValueError('Retained current-policy factual labels changed')
                reconstruction['cpu_seconds'] += data.cpu_seconds
                reconstruction['counts'] = sum_counts((reconstruction['counts'], data.processing))
                reconstruction['stages'] += 1; completed.append(life)
                data = None; active = None
                yield life, dataset
            else:
                raise ValueError('Unexpected retained current-policy record')
    if data is not None or completed!=receipt['lifecycle_ids']:
        raise ValueError('Retained current-policy histories are incomplete')


def _new_identity(fit):
    return scientific_identity({key:value for key,value in fit.items()
        if key not in ('candidate_fitted_games', 'selected_games', 'selection_counts')})


def _evaluate(leaf, life, belief, runtime):
    before = leaf.updates
    result = evaluate_split(leaf, belief['estimated_p_four'], .1,
        [evaluation_seed(life, episode) for episode in range(32)], runtime, max_steps=MAX_STEPS)
    if leaf.updates!=before:
        raise ValueError('Static V307 evaluation updated its parameters')
    return dict(result, estimated_p_four=belief['estimated_p_four'], static_evaluation_valid=True)


def _run_lifecycle(template, previous, current_receipt, old_data, current_data, runtime):
    life = previous['lifecycle']; belief = previous['evaluation_beliefs']['A']
    source, source_setup = new_head(template, runtime); source.freeze()
    initial, initial_setup = new_head(template, runtime)
    initial_fit = fit_split(initial, old_data, runtime, alpha=.0025); initial.freeze()
    if scientific_identity(initial_fit)!=scientific_identity(previous['stages']['A1']['arms']['LOCAL_RISK']['fit']):
        raise ValueError('V307 initial A1 fit did not reproduce V303')
    replay = build_replay(old_data, current_data)
    arms = {}
    for arm in ARMS:
        if arm in ('SOURCE', 'A1_FROZEN'):
            leaf, setup = (source, source_setup) if arm=='SOURCE' else (initial, initial_setup)
            before = leaf.updates
            fit = dict(method='NONE', trained_afterstates=0, learning_counts={}, target_counts={}, seconds=0., cpu_seconds=0.)
        else:
            leaf, setup = new_head(template, runtime, initial); before = leaf.updates
            fit = fit_masked_split(leaf, replay['datasets'][arm], replay['masks'][arm], runtime, alpha=.0025)
            if fit['trained_afterstates']!=replay['budget'] or leaf.updates-before!=replay['budget']:
                raise ValueError('V307 replay supervised-state budgets differ')
            if arm=='NEW_ONLY' and _new_identity(fit)!=scientific_identity(current_receipt['arms']['CURRENT_DATA']['fit']):
                raise ValueError('Unchanged new-only fit did not reproduce V306 CURRENT_DATA')
            leaf.freeze()
        evaluated = _evaluate(leaf, life, belief, runtime)
        arms[arm] = dict(fit=fit, head_setup=setup, head_updates_before=before,
            head_updates_after=leaf.updates, evaluation=evaluated)
        print(json.dumps(dict(event='experience_replay_arm_complete', lifecycle=life, arm=arm,
            updates=leaf.updates, utility=sum(game['utility'] for game in evaluated['game_summaries'])/32)), flush=True)
        if arm in ('NEW_ONLY', 'MIXED_REPLAY'):
            del leaf
    if source.updates or initial.updates!=initial_fit['trained_afterstates'] or template.updates:
        raise ValueError('V307 immutable source/A1 carriers changed')
    return dict(lifecycle=life, parent=previous['parent'], evaluation_belief=belief,
        initial_fit=initial_fit, initial_head_setup=initial_setup,
        inputs=dict(OLD_A1=compact_dataset(old_data), CURRENT_DATA=compact_dataset(current_data)),
        replay=dict(budget=replay['budget'], available=replay['available'], plans=replay['plans'],
            selection_counts=replay['counts'], selection_cpu_seconds=replay['cpu_seconds']), arms=arms)


def _run_parent(source, a1_receipt, current_receipt, old_lives, current_lives, output):
    started, cpu_started = perf_counter(), process_time()
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']; runtime = Path(output)/'runtime'/f'parent_{parent}'
    template, setup = load_leaf(source, runtime)
    reconstructions = {key:dict(canonical_rows_read=0, skipped_rows=0, stages=0, counts={}, cpu_seconds=0.)
        for key in ('OLD_A1', 'CURRENT_DATA')}
    old_stream = retained_a1(a1_receipt, old_lives, reconstructions['OLD_A1'])
    current_stream = retained_current(current_receipt, current_lives, reconstructions['CURRENT_DATA'])
    rows = []
    for (life, old), (current_life, current) in zip(old_stream, current_stream, strict=True):
        if life!=current_life:
            raise ValueError('Old and current retained lifecycle inventories differ')
        row = _run_lifecycle(template, old_lives[life], current_lives[life], old, current, runtime)
        rows.append(row)
        (Path(output)/'lifecycle_receipts'/f'life_{life:02d}.json').write_text(json.dumps(row, allow_nan=False)+'\n')
        del old, current
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=rows, source_setup=setup, reconstruction=reconstructions,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-children.ru_utime-children.ru_stime)


def build_accounting(current, lives, parents, cpu, wall):
    inherited = current['accounting']
    fits = {arm:[row['arms'][arm]['fit'] for row in lives] for arm in ARMS}
    evaluations = {arm:[row['arms'][arm]['evaluation'] for row in lives] for arm in ARMS}
    initial = [row['initial_fit'] for row in lives]
    budget = sum(row['replay']['budget'] for row in lives)
    result = dict(new_training_environment_observations=0, new_training_acquisitions=0,
        inherited_a1_raw_tiles=inherited['inherited_a1_raw_tiles'],
        inherited_current_raw_tiles=inherited['new_training_raw_tiles_by_actor']['CURRENT_DATA'],
        economic_training_raw_tiles_per_arm={arm:inherited['economic_training_raw_tiles_per_arm'][
            'CURRENT_DATA' if arm in ('NEW_ONLY', 'MIXED_REPLAY') else arm] for arm in ARMS},
        inherited_costs_per_arm={arm:inherited['inherited_costs_per_arm']['SOURCE'] for arm in ARMS},
        matched_supervised_state_budget_per_updating_arm=budget,
        new_processed_training_samples={arm:sum(fit['trained_afterstates'] for fit in values) for arm,values in fits.items()},
        initial_replayed_training_samples=sum(fit['trained_afterstates'] for fit in initial),
        initial_refit_counts=sum_counts(fit['learning_counts'] for fit in initial),
        initial_refit_cpu_seconds=sum(fit['cpu_seconds'] for fit in initial),
        selection_counts=sum_counts(row['replay']['selection_counts'] for row in lives),
        selection_cpu_seconds=sum(row['replay']['selection_cpu_seconds'] for row in lives),
        fit_cpu_seconds={arm:sum(fit['cpu_seconds'] for fit in values) for arm,values in fits.items()},
        private_head_weight_bytes_created={arm:sum(row['arms'][arm]['head_setup']['private_weight_bytes'] for row in lives) for arm in ARMS},
        head_setup_counts={arm:sum_counts(row['arms'][arm]['head_setup']['setup_counts'] for row in lives) for arm in ARMS},
        head_setup_cpu_seconds={arm:sum(row['arms'][arm]['head_setup']['setup_cpu_seconds'] for row in lives) for arm in ARMS},
        new_evaluation_games=sum(len(evaluation['game_summaries']) for values in evaluations.values() for evaluation in values),
        evaluation_counts_per_arm={arm:{kind:sum_counts(evaluation['counts'][kind] for evaluation in values)
            for kind in ('environment', 'planning')} for arm,values in evaluations.items()},
        evaluation_representation_counts={arm:sum_counts(evaluation['representation_counts'] for evaluation in values) for arm,values in evaluations.items()},
        evaluation_cpu_seconds_per_arm={arm:sum(evaluation['cpu_seconds'] for evaluation in values) for arm,values in evaluations.items()},
        reconstruction_counts={source:sum_counts(parent['reconstruction'][source]['counts'] for parent in parents)
            for source in ('OLD_A1', 'CURRENT_DATA')},
        reconstruction_cpu_seconds={source:sum(parent['reconstruction'][source]['cpu_seconds'] for parent in parents)
            for source in ('OLD_A1', 'CURRENT_DATA')},
        worker_cpu_seconds=sum(parent['cpu_seconds'] for parent in parents),
        compiler_cpu_seconds=sum(parent['compiler_cpu_seconds'] for parent in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall, historical_total_compute_closed=False,
        accounting_scope='Old A1 and V306 current raw are retained paid inputs, with no new training sampling. '
            'SOURCE/A1 references pay their source/dynamics/A1 history; both updating arms also pay the retained '
            'current cohort. Old replay does not charge extra acquisition. Exact supervised-state budgets do not '
            'equalize game/address commits or computation. Actual reconstruction/refit, full A1 copies, selection, '
            'masked fits and new evaluations are charged; component CPU is contained in worker CPU. '
            'Historical interrupted V303 total CPU remains unavailable.')
    for field, key in (('fit_counts', 'learning_counts'), ('fit_target_counts', 'target_counts'),
        ('fit_normalization_counts', 'normalization_counts'), ('fit_representation_counts', 'representation_counts'),
        ('fit_selection_counts', 'selection_counts'), ('fit_setup_counts', 'setup_counts')):
        result[field] = {arm:sum_counts({name:value for name,value in fit.get(key, {}).items()
            if not name.endswith('_peak')} for fit in values) for arm,values in fits.items()}
    return result


def run(a1_summary, current_summary, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V307 already frozen or complete')
    a1_path, current_path = Path(a1_summary).resolve(), Path(current_summary).resolve()
    old, current = json.loads(a1_path.read_text()), json.loads(current_path.read_text())
    for path in (a1_path, current_path):
        audit = json.loads(path.with_name('audit.json').read_text())
        if audit['status']!='PASS' or not audit['independent_valid']:
            raise ValueError('V307 retained input requires its passing independent audit')
    if current['source_provenance']!=old['source_provenance'] or current['settings']['source_summary']!=str(a1_path):
        raise ValueError('V307 old and current histories must inherit the same original SOURCE/A1')
    settings = configuration(a1_path, current_path)
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n')
    (output/'lifecycle_receipts').mkdir()
    old_lives = {row['lifecycle']:row for row in old['by_lifecycle']}
    current_lives = {row['lifecycle']:row for row in current['by_lifecycle']}
    old_receipts = {row['parent']:row for row in old['parent_receipts']}
    current_receipts = {row['parent']:row for row in current['parent_receipts']}
    started, cpu_started = perf_counter(), process_time(); parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source, old_receipts[source['parent']], current_receipts[source['parent']],
            old_lives, current_lives, output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parent = job.result(); parents.append(parent)
            (output/f"parent_{parent['parent']}_receipt.json").write_text(json.dumps(
                {key:value for key,value in parent.items() if key!='lifecycles'}, indent=2)+'\n')
    parents.sort(key=lambda parent:parent['parent'])
    lives = sorted((row for parent in parents for row in parent['lifecycles']), key=lambda row:row['lifecycle'])
    analysis = summarize(lives)
    result = dict(schema='acfqp.experience_replay.v307', status='EXPERIMENT_COMPLETE', scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings, source_provenance=old['source_provenance'], by_lifecycle=lives,
        parent_receipts=[dict({key:value for key,value in parent.items() if key!='lifecycles'},
            lifecycle_ids=[row['lifecycle'] for row in parent['lifecycles']]) for parent in parents],
        summary=analysis, accounting=build_accounting(current, lives, parents, process_time()-cpu_started, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='experience_replay_complete', primary=analysis['paired_contrasts']['MIXED_REPLAY_minus_NEW_ONLY'],
        retention=analysis['replay_retention_status'])), flush=True)
    return result
