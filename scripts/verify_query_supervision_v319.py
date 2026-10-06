#!/usr/bin/env python3
"""Independent V319 actual H2-query roots and paired grouped one-step supervision."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (ACTIONS, HeadVersions, TileRandom, close, equal_tree,
    json_file, literal_choose, physical_status, planning_counts, read_source_weights,
    require, sum_counts, check_representation)
from verify_greedy_targets_v317 import (FactualWorld, POST_RAW, feature_addresses,
    post_seed, predict_components, vector_swipes)

TASKS = ('A', 'B')
UPDATING_ARMS = ('FACTUAL_LOCAL', 'QUERY_LOCAL')
GROUPS = 16384
REPLICAS = 4


def selection_seed(life, task, round_index):
    return 319100000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def draw_seed(life, task, round_index):
    return 319500000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def evaluation_seed(life, task, episode):
    return 319900000000+life*1000000+TASKS.index(task)*100000+episode


def anchor_census(boards, games, fit_game_count, groups=GROUPS, radix=11):
    """Chronological complete FIT nonWIN actions with a factual predecessor in the same game."""
    candidates = []; start = 0
    for game in games[:fit_game_count]:
        stop = start+game['steps']
        candidates.extend(index for index in range(start+1, stop) if max(boards[index]) < radix)
        start = stop
    require(len(candidates) >= 2*groups,
        'frozen source condition requires its full twice-group-count anchor census without replacements')
    positions = np.linspace(0, len(candidates)-1, 2*groups, dtype=np.int64)
    return np.asarray(candidates, dtype=np.int64)[positions]


def query_paths(boards, ordinals, radix=11):
    """Chunked literal H2 prediction-call traversal, preserving every duplicate call."""
    boards = np.asarray(boards, dtype=np.int32).reshape(-1, 16)
    ordinals = np.asarray(ordinals, dtype=np.int64)
    counts = np.zeros(len(boards), dtype=np.int64)
    selected = np.zeros_like(boards)
    paths = np.full((len(boards), 4), -1, dtype=np.int64)
    for begin in range(0, len(boards), 512):
        source = boards[begin:begin+512]
        outer, _, outer_legal = vector_swipes(source, radix)
        local_counts = np.zeros(len(source), dtype=np.int64)
        for action in range(4):
            eligible = outer_legal[:, action] & (np.max(outer[:, action], axis=1) < radix)
            root_rows, cells = np.nonzero((outer[:, action] == 0) & eligible[:, None])
            roots = np.repeat(root_rows, 2); cells = np.repeat(cells, 2)
            ranks = np.tile(np.asarray([1, 2], dtype=np.int32), len(root_rows))
            spawned = outer[roots, action].copy(); spawned[np.arange(len(spawned)), cells] = ranks
            inner, _, inner_legal = vector_swipes(spawned, radix)
            calls = inner_legal & (np.max(inner, axis=2) < radix)
            spawn_rows, inner_actions = np.nonzero(calls)
            call_roots = roots[spawn_rows]
            root_totals = np.bincount(call_roots, minlength=len(source))
            offsets = np.cumsum(root_totals)-root_totals
            call_ordinals = np.arange(len(call_roots))-offsets[call_roots]+local_counts[call_roots]
            chosen = call_ordinals == ordinals[begin+call_roots]
            chosen_roots = call_roots[chosen]
            chosen_spawns = spawn_rows[chosen]; chosen_actions = inner_actions[chosen]
            selected[begin+chosen_roots] = inner[chosen_spawns, chosen_actions]
            paths[begin+chosen_roots] = np.column_stack((np.full(len(chosen_roots), action),
                cells[chosen_spawns], ranks[chosen_spawns], chosen_actions))
            local_counts += root_totals
        counts[begin:begin+len(source)] = local_counts
    return counts, selected, paths


def check_selector(preboards, query_ordinals, query_counts, validmask, seed, radix=11):
    counts, roots, paths = query_paths(preboards, query_ordinals, radix)
    require(np.array_equal(query_counts, counts) and np.array_equal(validmask, (counts > 0).astype(np.int32)),
        'all census query counts and validity come from actual nonWIN H2 prediction calls with multiplicity')
    # Invalid anchors consume the same one draw as every valid anchor.
    rng = TileRandom(seed); expected = []
    for count in counts:
        uniform = rng.random(); expected.append(int(uniform*count) if count else -1)
    require(np.array_equal(query_ordinals, np.asarray(expected, dtype=np.int64)),
        'one independent seeded uniform draw per census anchor selects the exact ordered call pool index')
    return roots, paths


def selected_positions(validmask, groups=GROUPS):
    valid = np.flatnonzero(validmask)
    require(len(valid) >= groups, 'source-condition failure preserves whole-cohort HOLD rather than replacing roots')
    return valid[np.linspace(0, len(valid)-1, groups, dtype=np.int64)]


def ground_uniforms(seed, groups, replicas=REPLICAS):
    rng = TileRandom(seed)
    return np.fromiter((rng.random() for _ in range(2*groups*replicas)), dtype=np.float64).reshape(groups, replicas, 2)


def ground_postspawn(roots, uniforms, probability, cells, ranks, replicas=REPLICAS):
    """Every replica resets the same afterstate before its separately paid spawn."""
    roots = np.asarray(roots, dtype=np.int32).reshape(-1, 16)
    require(cells.shape == ranks.shape == (len(roots), replicas), 'every explicit sampling group has all four physical members')
    require(uniforms.shape == (len(roots), replicas, 2), 'paired stage stream preserves both uniforms for each explicit member')
    expected_ranks = np.where(uniforms[:, :, 1] < 1.-probability, 1, 2).astype(np.int32)
    expected_cells = np.empty_like(cells)
    for group, board in enumerate(roots):
        empty = np.flatnonzero(board == 0)
        require(len(empty) > 0 and max(board) < 11, 'every query and factual afterstate reset is a legal nonWIN spawn origin')
        expected_cells[group] = empty[(uniforms[group, :, 0]*len(empty)).astype(np.int64)]
    require(np.array_equal(cells, expected_cells) and np.array_equal(ranks, expected_ranks),
        'every paired ground cell/rank follows its exact continuous root-major member-major reset RNG stream')
    result = np.repeat(roots[:, None, :], replicas, axis=1)
    result[np.arange(len(roots))[:, None], np.arange(replicas)[None, :], cells] = ranks
    return result


def teacher_targets(postspawn, teacher, radix=11):
    """Single combined DIRECT max supplies both components of every one-step target."""
    shape = postspawn.shape[:2]; boards = np.asarray(postspawn, dtype=np.int32).reshape(-1, 16)
    reward = np.zeros(len(boards)); win = np.zeros(len(boards))
    actions = np.full(len(boards), -1, dtype=np.int32); kinds = np.full(len(boards), 3, dtype=np.int32)
    stats = Counter()
    for begin in range(0, len(boards), 4096):
        batch = boards[begin:begin+4096]; moved, scores, legal = vector_swipes(batch, radix)
        winning = np.max(moved, axis=2) >= radix
        gain = scores.astype(np.float64)/2048.; predicted_reward = np.zeros_like(gain); probability = np.zeros_like(gain)
        tail = np.zeros_like(gain); analytic = legal & winning; lookups = legal & ~winning
        probability[analytic] = 1.; tail[analytic] = 4.
        if np.any(lookups):
            r, p = predict_components(moved[lookups], teacher, radix)
            predicted_reward[lookups] = r; probability[lookups] = p
            tail[lookups] = r+8.*(p-.5)
        utility = np.where(legal, gain+tail, -np.inf)
        selected = np.argmax(utility, axis=1); any_legal = np.any(legal, axis=1); rows = np.flatnonzero(any_legal)
        absolute = begin+rows; chosen = selected[rows]
        actions[absolute] = chosen; reward[absolute] = gain[rows, chosen]+predicted_reward[rows, chosen]
        win[absolute] = probability[rows, chosen]; kinds[absolute] = np.where(winning[rows, chosen], 2, 1)
        stats.update(samples=len(batch), legal_candidates=int(np.count_nonzero(legal)),
            winning_candidates=int(np.count_nonzero(analytic)), nonwinning_candidates=int(np.count_nonzero(lookups)),
            lost_samples=int(np.count_nonzero(~any_legal)))
    return reward.reshape(shape), win.reshape(shape), actions.reshape(shape), kinds.reshape(shape), dict(stats)


def read_post_facts(previous):
    """One necessary retained post-batch pass; initial worlds and prior audits are not repeated."""
    lives = {row['lifecycle']:row for row in previous['by_lifecycle']}; worlds = {}; rows = decoded = 0
    for parent in previous['parent_receipts']:
        with gzip.open(parent['trace_file'], 'rt') as stream:
            for line in stream:
                row = json.loads(line); decoded += 1
                if row['kind'] not in ('TRAIN', 'ACQUISITION_SNAPSHOT') or row.get('phase') not in ('A_R1', 'B_R1', 'A_R2', 'B_R2'):
                    continue
                life = lives[row['lifecycle']]; task = row['task']; round_index = int(row['phase'][-1])
                require(row['parent'] == parent['parent'] == life['parent'] == life['lifecycle'] % 4,
                    'retained query supervision anchors follow their actual frozen parent')
                key = life['lifecycle'], task, round_index
                if key not in worlds:
                    first = life['initial'][task]; actor = first['head_versions']['FIRST_LOCAL']
                    identity = dict(lifecycle=life['lifecycle'], parent=life['parent'], arm='FIXED_FIRST',
                        batch_id=row['phase'], phase=row['phase'], true_p_four=.1 if task == 'A' else .5,
                        model_p_four=first['planning_belief']['estimated_p_four'], task=task,
                        actor_head_updates=actor['updates'], collector_policy_kind='LOCAL_RISK', actor_version=actor,
                        stream_seed=post_seed(life['lifecycle'], task, round_index))
                    worlds[key] = FactualWorld(identity['stream_seed'], POST_RAW, identity['true_p_four'], identity, 'LOCAL_RISK')
                (worlds[key].train if row['kind'] == 'TRAIN' else worlds[key].checkpoint)(row); rows += 1
    require(set(worlds) == {(life, task, r) for life in range(16) for task in TASKS for r in (1, 2)}
        and all(world.snapshot is not None for world in worlds.values()), 'all retained sixteen-life A/B post batches are present without cohort selection')
    return worlds, dict(decoded_canonical_rows=decoded, reconstructed_post_rows=rows, retained_raw_tiles_reconstructed=64*POST_RAW)


def group_means(reward, win):
    rt, pt = np.zeros(len(reward)), np.zeros(len(win))
    for member in range(REPLICAS):
        rt += reward[:, member]; pt += win[:, member]
    return rt/REPLICAS, pt/REPLICAS


def check_group_arrays(arrays, roots, uniforms, probability, teacher, radix=11):
    require(arrays['roots'].dtype == np.int32 and np.array_equal(arrays['roots'], roots),
        'each saved supervision group starts at its exact selected QUERY or factual afterstate')
    shape = len(roots), REPLICAS
    for field in ('targetreward', 'targetwin'):
        require(arrays[field].dtype == np.float64 and arrays[field].shape == shape,
            'each group stores all four actual paired component targets')
    for field in ('selected_action', 'targetkind', 'spawn_cells', 'spawn_ranks'):
        require(arrays[field].dtype == np.int32 and arrays[field].shape == shape,
            'each group stores all four physical members and selected joint branches')
    postspawn = ground_postspawn(roots, uniforms, probability, arrays['spawn_cells'], arrays['spawn_ranks'])
    reward, win, actions, kinds, stats = teacher_targets(postspawn, teacher, radix)
    require(np.array_equal(arrays['selected_action'], actions) and np.array_equal(arrays['targetkind'], kinds),
        'every target selects one exact combined DIRECT branch with unchanged first-max and analytic WIN/LOST rules')
    require(np.allclose(arrays['targetreward'], reward, rtol=1e-12, atol=1e-12)
        and np.allclose(arrays['targetwin'], win, rtol=1e-12, atol=1e-12),
        'all new component labels come from the same frozen FIRST branch rather than current learner or separate maxima')
    rt, pt = group_means(arrays['targetreward'], arrays['targetwin'])
    require(arrays['mean_reward'].dtype == arrays['mean_win'].dtype == np.float64
        and arrays['mean_reward'].shape == arrays['mean_win'].shape == (len(roots),)
        and np.allclose(arrays['mean_reward'], rt, rtol=1e-12, atol=1e-12)
        and np.allclose(arrays['mean_win'], pt, rtol=1e-12, atol=1e-12),
        'actual group update inputs are the arithmetic means of their four real members')
    return stats, kinds


def check_supervision_work(value, roots, stats, kinds, seed, teacher_updates, true_probability):
    groups = len(roots); samples = groups*REPLICAS; lost = stats['lost_samples']
    chosen = samples-lost; legal = stats['legal_candidates']; predictions = stats['nonwinning_candidates']; wins = stats['winning_candidates']
    require(value['draw_seed'] == seed and value['p_true'] == true_probability
        and value['repeats'] == REPLICAS and value['teacher_updates'] == teacher_updates
        and value['target_rule'] == 'GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH',
        'both arms retain the same immutable FIRST one-step teacher and paired physical stream')
    expected = dict(rootgroups_supervised=groups, replica_targets=samples, supervision_start_spawns=samples,
        direct_choose_calls=chosen, direct_action_candidates=4*chosen, direct_legal_action_candidates=legal,
        teacher_predictions=predictions, teacher_reward_table_lookups=32*predictions,
        teacher_win_table_lookups=32*predictions, analytic_win_candidates=wins,
        bootstrap_targets=int(np.count_nonzero(kinds == 1)), analytic_win_targets=int(np.count_nonzero(kinds == 2)),
        terminal_lost_targets=lost, ground_teacher_branch_checks=chosen)
    require(Counter(value['counts']) == Counter(expected), 'all actual teacher targets candidate reads and branch checks are charged')
    environment = dict(post_action_spawns=samples, raw_tile_productions=samples, environment_random_draws=2*samples,
        sampled_transitions=chosen, ground_explicit_swipe_calls=chosen, ground_swipe_calls=4*samples+chosen,
        ground_state_status_calls=samples, ground_status_internal_swipe_calls=4*samples)
    require(Counter(value['environment_counts']) == Counter(environment),
        'exactly four new reset spawns per group and actual checked ground swipes receive physical charges')
    planning = dict(choose_calls=chosen, learned_swipe_calls=4*chosen, line_table_lookups=16*chosen,
        legal_swipes=legal, learned_terminal_checks=chosen+legal, value_predictions=predictions,
        table_lookups=32*predictions, terminal_goal_bypasses=wins, root_swipe_calls=4*chosen,
        root_legal_actions=legal, root_goal_actions=wins)
    require(Counter(value['planning_counts']) == Counter(planning),
        'DIRECT teacher work has no model spawn expansion or extra physical tile')
    check_representation(value['representation_counts'], 'LOCAL_RISK', predictions)


def check_group_fit(fit, arrays, initial_head):
    roots = arrays['roots']; n = len(roots); features = np.sort(feature_addresses(roots), axis=1)
    unique = int(n+np.count_nonzero(features[:, 1:] != features[:, :-1]))
    require(fit['method'] == 'GROUPED_LOCAL' and fit['alpha'] == .0025
        and fit['fitted_rootgroups'] == fit['trained_afterstates'] == n and fit['replicates'] == REPLICAS
        and fit['frozen_rootgroup_predictions']
        and fit['sampling_unit'] == 'ROOTGROUP_MEAN_OF_FIXED_TEACHER_ONE_STEP_REPLICAS',
        'current learner predicts and commits once per explicit root group without fake complete-game semantics')
    learning = dict(rootgroup_updates=n, current_predictions=n, table_lookups=64*n, table_updates=2*unique,
        table_update_occurrences=32*n, reward_predictions=n, win_predictions=n,
        reward_table_lookups=32*n, win_table_lookups=32*n, reward_table_updates=unique, win_parameter_updates=unique)
    require(Counter(fit['learning_counts']) == Counter(learning),
        'matched group/current prediction counts retain each arm actual distinct-address writes')
    targets = dict(rootgroups_targeted=n, reward_replica_reads=8*n, win_replica_reads=8*n,
        reward_target_mean_additions=4*n, win_target_mean_additions=4*n, target_mean_divisions=2*n,
        replica_noise_residuals=8*n, replica_noise_squares=8*n, replica_noise_accumulations=8*n,
        replica_noise_divisions=2, replica_noise_square_roots=2)
    require(Counter(fit['target_counts']) == Counter(targets), 'root means and replicate-noise work are charged without suffix or terminal-game targets')
    normalization = dict(rootgroups_processed=n, feature_extractions=n, feature_occurrences=32*n,
        feature_digit_reads=192*n, feature_address_multiply_adds=192*n, sort_calls=n, sort_items=32*n,
        denominator_occurrence_visits=32*n, rootgroup_unique_addresses=unique,
        reward_gradient_products=unique, win_gradient_products=unique, normalization_divisions=2*unique,
        parameter_update_multiplications=2*unique, rootgroup_parameter_commits=n, reward_rootgroup_commits=n,
        win_rootgroup_commits=n, reward_parameter_writes=unique, win_parameter_writes=unique, native_workspace_bytes=512)
    equal_tree({key:fit['normalization_counts'][key] for key in normalization}, normalization,
        'within-root occurrence normalization gives one actual dual-table commit per group')
    require(fit['normalization_counts']['sort_comparisons'] > 0, 'actual native sorting comparisons remain recorded')
    check_representation(fit['representation_counts'], 'LOCAL_RISK', n)
    rt, pt = arrays['mean_reward'], arrays['mean_win']
    noise = fit['replicate_noise']
    require(noise['definition'] == 'SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'
        and close(noise['reward_replica_rms'], float(np.sqrt(np.mean((arrays['targetreward']-rt[:, None])**2))))
        and close(noise['win_replica_rms'], float(np.sqrt(np.mean((arrays['targetwin']-pt[:, None])**2)))),
        'replicate noise uses population-centered member dispersion rather than a fabricated game statistic')
    for sample, index in ((fit['first_sample'], 0), (fit['last_sample'], n-1)):
        require(sample['rootgroup'] == index and close(sample['reward_target'], rt[index])
            and close(sample['risk_target'], pt[index])
            and close(sample['reward_error'], rt[index]-sample['reward_prediction'])
            and close(sample['risk_error'], pt[index]-sample['risk_probability'])
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(sample['risk_probability']-.5)),
            'actual current prediction examples consume the saved group means before their root commit')
    reward, probability = predict_components(roots[:1], initial_head)
    require(close(fit['first_sample']['reward_prediction'], reward[0])
        and close(fit['first_sample']['risk_probability'], probability[0]),
        'the first actual current prediction reads its own declared previous head rather than the teacher or other arm')
    return unique


def check_evaluation(value, life, task, belief, version):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2'
        and value['head_version'] == version and value['static_evaluation_valid'],
        'all new SOURCE FIRST and coverage learners use their actual selected bank belief and frozen head')
    games = value['game_summaries']
    require(len(games) == 32 and [game['seed'] for game in games] == [evaluation_seed(life, task, episode) for episode in range(32)],
        'each natural evaluation cell uses all thirty-two fresh paired V319 task seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'new coverage evaluation retains the natural frozen horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE', 'actual nonterminal cutoff stays explicit')
            bonus = 0.
        else:
            require(game['status'] in ('WON', 'LOST') and physical_status(game['final_board']) == game['status'],
                'every evaluation terminal label agrees with the actual physical final board')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'natural whole-game utility is separate from bootstrapped one-step labels')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    environment = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32, ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(value['counts']['environment']) == Counter(environment), 'all new natural evaluation random tiles and swipes are charged')
    planning_counts(value['counts']['planning'], steps, depth=2)
    if version is not None:
        check_representation(value['representation_counts'], 'LOCAL_RISK', value['counts']['planning'].get('value_predictions', 0))
    require(not value['counts'].get('learning', {}), 'evaluation never fits or generates root supervision')
    return mean(game['utility'] for game in games)


PAIRS = (('QUERY_LOCAL', 'FIRST_LOCAL'), ('QUERY_LOCAL', 'FACTUAL_LOCAL'), ('QUERY_LOCAL', 'SOURCE'),
    ('FACTUAL_LOCAL', 'FIRST_LOCAL'), ('FACTUAL_LOCAL', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT'


def check_contrast(saved, values):
    require(len(values) == 16 and close(saved['mean'], mean(values)), 'all sixteen paired lifecycle effects retain their actual signed mean')
    equal_tree(saved['lifecycle_deltas'], {str(life):value for life, value in enumerate(values)},
        'every existing FIRST cohort lifecycle remains in the new effect vector')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent, group in enumerate(groups)},
        'all four frozen SOURCE groups condition the paired bootstrap')
    require(saved['interval_scope'] == INTERVAL_SCOPE, 'coverage intervals retain reused-cohort conditional scope')
    low, high = saved['ci95']; minimum, maximum = mean(min(group) for group in groups), mean(max(group) for group in groups)
    require(minimum-1e-10 <= low <= high <= maximum+1e-10, 'interval retains its realized fixed-parent bootstrap feasible range')
    require(saved['improved_equal_worse'] == [sum(value > 0 for value in values), sum(value == 0 for value in values), sum(value < 0 for value in values)],
        'all adverse and equal new coverage effects remain in the result')


def effect_status(contrast, complete, retention=False):
    if not complete:
        return 'HOLD_CUTOFF'
    low, high = contrast['ci95']
    if (low >= 0.) if retention else (low > 0.):
        return 'SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN'
    return 'SUPPORTED_LOSS' if high < 0. else 'UNRESOLVED'


def check_analysis(summary, records, lives):
    equal_tree(summary['by_lifecycle'], records, 'all fresh coverage endpoints and immutable observed banks')
    require(summary['bootstrap_seed'] == 31900001 and summary['bootstrap_draws'] == 20000
        and summary['primary_contrast'] == 'QUERY_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        'single prespecified own-FIRST primary and exact paired bootstrap contract')
    pairs = {left+'_minus_'+right for left, right in PAIRS}
    require(set(summary['round_ab_contrasts']) == {'1', '2'} and set(summary['final_ab_contrasts']) == pairs,
        'both post-rounds retain all six separate own-FIRST coverage and SOURCE contrasts')
    for r in ('1', '2'):
        require(set(summary['round_ab_contrasts'][r]) == pairs, 'all prespecified round contrasts remain present')
        for left, right in PAIRS:
            name = left+'_minus_'+right
            ab = [mean(row['cells']['ROUND'+r+'_'+task][left]-row['cells']['ROUND'+r+'_'+task][right] for task in TASKS) for row in records]
            check_contrast(summary['round_ab_contrasts'][r][name], ab)
            for task in TASKS:
                key = 'ROUND'+r+'_'+task
                values = [row['cells'][key][left]-row['cells'][key][right] for row in records]
                check_contrast(summary['task_contrasts'][key][name], values)
        for task in TASKS:
            key = 'ROUND'+r+'_'+task
            equal_tree(summary['checkpoint_contrasts'][key], {arm:summary['task_contrasts'][key][arm+'_minus_FIRST_LOCAL'] for arm in UPDATING_ARMS},
                'checkpoint retention uses actual own-FIRST effects rather than SOURCE-adjusted gains')
    equal_tree(summary['final_ab_contrasts'], summary['round_ab_contrasts']['2'], 'final aggregate effect is the actual second-round endpoint')
    cutoffs = []
    for row in lives:
        for task in TASKS:
            initial = row['initial'][task]['evaluations']
            stages = [('FIRST', initial)]+[('ROUND'+r, {**initial, **{arm:row['rounds'][r][task]['arms'][arm]['evaluations'] for arm in UPDATING_ARMS}}) for r in ('1', '2')]
            for checkpoint, evaluations in stages:
                for arm, value in evaluations.items():
                    cutoffs.extend(dict(lifecycle=row['lifecycle'], task=task, arm=arm, checkpoint=checkpoint, seed=game['seed'])
                        for game in value['game_summaries'] if game['status'] == 'CUTOFF')
    complete = not cutoffs
    require(summary['complete_game_endpoints'] == complete and summary['cutoffs'] == cutoffs
        and summary['physical_evaluation_games'] == 6144, 'all new natural cells preserve every cutoff and count physical games once')
    final = summary['final_ab_contrasts']
    primary = effect_status(final['QUERY_LOCAL_minus_FIRST_LOCAL'], complete)
    coverage = effect_status(final['QUERY_LOCAL_minus_FACTUAL_LOCAL'], complete)
    retention = {task:effect_status(summary['checkpoint_contrasts']['ROUND2_'+task]['QUERY_LOCAL'], complete, True) for task in TASKS}
    preserved = all(status == 'SUPPORTED_NONDECREASE' for status in retention.values())
    expected = dict(primary_self_improvement_status=primary, primary_self_improvement_supported=primary == 'SUPPORTED_GAIN',
        coverage_intervention_status=coverage, coverage_intervention_supported=coverage == 'SUPPORTED_GAIN',
        factual_self_improvement_status=effect_status(final['FACTUAL_LOCAL_minus_FIRST_LOCAL'], complete),
        final_net_gain_status=effect_status(final['QUERY_LOCAL_minus_SOURCE'], complete), task_retention_status=retention,
        retained_improvement_supported=primary == 'SUPPORTED_GAIN' and preserved,
        coverage_mechanism_supported=primary == 'SUPPORTED_GAIN' and preserved and coverage == 'SUPPORTED_GAIN')
    equal_tree({key:summary[key] for key in expected}, expected, 'own-FIRST growth both-bank retention and coverage evidence remain separate')
    require('generative' in summary['evidence_scope'] and 'teacher is bootstrapped' in summary['evidence_scope']
        and 'ordinary online sampling-efficiency' in summary['evidence_scope'], 'coverage evidence explicitly retains reset access and teacher bias scope')




def expected_configuration(source_summary):
    return dict(schema='acfqp.query_supervision_freeze.v319', source_summary=str(Path(source_summary).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/QUERY_SUPERVISION_V319.md'),
        lifecycles=list(range(16)), parents=4, workers=4, tasks=list(TASKS), arms=list(UPDATING_ARMS),
        rounds=[1, 2], alpha=.0025, groups_per_arm_task_round=GROUPS, replicas_per_group=REPLICAS,
        census_anchors_per_task_round=2*GROUPS, true_probabilities={'A':.1, 'B':.5},
        teacher='IMMUTABLE_ACTUAL_V317_FIRST_LOCAL_V0_ALL_ROUNDS_AND_BOTH_ARMS',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        anchor='COMPLETE_FIT_NONWIN_CURRENT_AFTERSTATE_WITH_SAME_GAME_PREDECESSOR_POSTSPAWN',
        query_root='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        valid_selection='EQUIDISTANT_VALID_CENSUS_POSITIONS_SHARED_BETWEEN_ARMS',
        reset_access='ARBITRARY_AFTERSTATE_GENERATIVE_ACCESS_FOR_BOTH_ARMS',
        target='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH',
        update='GROUPED_LOCAL_CURRENT_PREDICTION_ONCE_PER_ROOTGROUP_MEAN_REPLICAS',
        max_steps=8192, evaluation_games_per_cell=32, seed_selector=319100000000,
        seed_ground=319500000000, collection_life_stride=10000000, collection_task_stride=1000000,
        collection_round_stride=100000, seed_evaluation=319900000000,
        bootstrap_seed=31900001, bootstrap_draws=20000,
        primary='QUERY_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        coverage='QUERY_LOCAL_minus_FACTUAL_LOCAL_FINAL_AB',
        retention='FINAL_QUERY_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_new_training_raw_tiles=8388608, expected_new_evaluation_games=6144,
        evidence_scope='FIXED_EXISTING_FIRST_COHORT_FOUR_FROZEN_PARENTS_GENERATIVE_ONE_STEP_SUPERVISION',
        stop_rule='WHOLE_COHORT_HOLD_IF_INSUFFICIENT_CENSUS_OR_CUTOFF_NO_REPLACEMENTS_OR_TUNING')


def artifact_arrays(receipt, fields, metadata):
    equal_tree(receipt['metadata'], metadata, 'actual saved artifact ownership teacher stream and sampling-unit metadata')
    path = Path(receipt['file'])
    require(path.stat().st_size == receipt['saved_bytes'], 'actual artifact compressed bytes match its save receipt')
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == set(fields)|{'metadata_json'}, 'new artifact retains exactly its declared physical arrays and metadata')
        equal_tree(json.loads(str(saved['metadata_json'])), metadata, 'actual NPZ ownership matches independently established teacher and roots')
        arrays = {name:saved[name] for name in fields}
    require(receipt['array_bytes'] == sum(array.nbytes for array in arrays.values()), 'actual array storage is charged separately from compressed file bytes')
    require(receipt['save_cpu_seconds'] >= 0. and receipt['save_wall_seconds'] >= 0., 'actual array save CPU and wall receipts remain contained in worker compute')
    return arrays


CENSUS_FIELDS = ('anchor_indices','validmask','query_ordinals','query_counts','selected_positions','selected_provenance')
GROUP_FIELDS = ('roots','targetreward','targetwin','selected_action','targetkind','spawn_cells','spawn_ranks','mean_reward','mean_win')
PROVENANCE_COLUMNS = ['root_action','spawn_cell','spawn_rank','inner_action','query_ordinal','total_leaf_queries']


def check_census(receipt, world, collector, teacher, version, life, parent, task, number, belief):
    boards = np.concatenate(world.afterstate_chunks); postspawn = np.concatenate(world.postspawn_chunks)
    fit_games = 4*len(world.games)//5; fit_end = world.ends[fit_games-1]
    dataset = collector['dataset']
    require(dataset['fit_game_count'] == fit_games and dataset['fit_step_end'] == fit_end,
        'anchor source complete FIT boundary is independently reconstructed rather than a selected subset')
    indices = anchor_census(boards, world.games, fit_games)
    metadata = dict(schema='acfqp.query_census.v319', lifecycle=life, parent=parent, task=task, round=number,
        groups=GROUPS, anchors=2*GROUPS, teacher_version=version, selection_seed=selection_seed(life,task,number),
        planning_probability=belief, selection_rule='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        source_batch=dict(actor_version=collector['actor_version'], batch_id=f'{task}_R{number}',
            fit_step_end=fit_end, fit_game_count=fit_games, stream_seed=post_seed(life,task,number)))
    arrays = artifact_arrays(receipt, CENSUS_FIELDS, metadata)
    for name in CENSUS_FIELDS:
        dtype = np.int32 if name == 'validmask' else np.int64
        require(arrays[name].dtype == dtype, 'census indices masks and query paths retain exact declared integer types')
    require(np.array_equal(arrays['anchor_indices'], indices) and arrays['validmask'].shape == (2*GROUPS,)
        and arrays['query_ordinals'].shape == arrays['query_counts'].shape == (2*GROUPS,),
        'all twice-group-count census anchors are the frozen evenly spaced eligible complete FIT indices')
    preboards = postspawn[indices-1]; natural_roots = boards[indices]
    query_roots, paths = check_selector(preboards, arrays['query_ordinals'], arrays['query_counts'], arrays['validmask'],
        selection_seed(life,task,number))
    positions = selected_positions(arrays['validmask'])
    provenance = np.column_stack((paths[positions], arrays['query_ordinals'][positions], arrays['query_counts'][positions]))
    require(np.array_equal(arrays['selected_positions'], positions) and np.array_equal(arrays['selected_provenance'], provenance)
        and receipt['selected_groups'] == GROUPS, 'both arms use the same prespecified valid census positions and exact ordered H2-call roots')
    nonwin = np.max(boards[:fit_end], axis=1) < 11
    starts = np.asarray([0]+world.ends[:fit_games-1], dtype=np.int64)
    eligible = int(np.count_nonzero(nonwin))-int(np.count_nonzero(nonwin[starts]))
    anchor_counts = dict(fit_states=fit_end,fit_games=fit_games,eligible_anchors=eligible,selected_anchors=2*GROUPS,
        requested_groups=GROUPS,excluded_winning_fit_states=fit_end-int(np.count_nonzero(nonwin)),
        excluded_game_first_nonwinning_states=int(np.count_nonzero(nonwin[starts])),index_array_bytes=16*GROUPS,
        preboard_array_bytes=128*GROUPS,natural_root_array_bytes=128*GROUPS)
    equal_tree(receipt['anchor_counts'], anchor_counts, 'actual census construction excludes game starts WIN HELDOUT and paid tails before querying')
    query = receipt['query']; count = int(np.sum(arrays['query_counts'])); valid = int(np.count_nonzero(arrays['validmask']))
    require(query['selection_seed'] == metadata['selection_seed'] and query['p_model'] == belief
        and query['teacher_updates'] == version['updates'] and query['provenance_columns'] == PROVENANCE_COLUMNS
        and query['selection_rule'] == metadata['selection_rule'], 'actual query receipt uses its frozen FIRST bank and declared selector')
    expected_counts = dict(anchors_queried=2*GROUPS, actual_nonwin_leaf_queries=count, pool_board_cells_written=16*count,
        pool_path_fields_written=4*count, selector_random_draws=2*GROUPS, valid_anchors=valid, selected_roots=valid)
    equal_tree({key:query['counts'][key] for key in expected_counts}, expected_counts,
        'every actual H2 leaf-call pool preserves multiplicity and one selector draw per anchor')
    maximum = int(np.max(arrays['query_counts']))
    capacity = 0 if not maximum else 1 << (maximum-1).bit_length()
    require(query['counts']['native_pool_bytes_peak'] == 96*capacity,
        'actual shared query pool peak includes the native board/path capacity once')
    planning_counts(query['planning_counts'], 2*GROUPS, depth=2)
    require(query['planning_counts']['value_predictions'] == count, 'all independently reconstructed leaf calls reconcile actual query table reads')
    check_representation(query['representation_counts'], 'LOCAL_RISK', count)
    probes = 0
    for name, expected_indices in (('first_probes', range(8)), ('last_probes', range(2*GROUPS-8,2*GROUPS))):
        require(len(query[name]) == 8, 'all predeclared first-eight last-eight census teacher probes are retained')
        for saved, index in zip(query[name], expected_indices):
            actual = literal_choose(preboards[index].tolist(), teacher.reward, teacher.terminal, 'LOCAL_RISK', belief)
            require(saved['anchor_index'] == index and saved['preboard'] == preboards[index].tolist()
                and saved['chosen_action'] == actual['action'] and saved['chosen_afterstate'] == natural_roots[index].tolist()
                and actual['afterstate'] == natural_roots[index].tolist() and close(saved['chosen_h2_value'],actual['value'])
                and saved['status'] == 'ACTIVE', 'bounded actual FIRST H2 decisions reproduce factual natural roots at prescribed census boundaries')
            equal_tree(saved['action_values'], actual['action_values'], 'all literal candidate H2 values bind census teacher choice to actual frozen weights')
            probes += 1
    return {'FACTUAL_LOCAL':natural_roots[positions], 'QUERY_LOCAL':query_roots[positions]}, probes


def check_lifecycle(row, old, worlds, source, checkpoint):
    life, parent = row['lifecycle'], row['parent']
    require(life == old['lifecycle'] and parent == old['parent'] == life%4, 'all reused lives retain their declared frozen SOURCE parent')
    heads = {}; teachers = {}; versions = {}; beliefs = {}; records = dict(lifecycle=life,parent=parent,cells={}); counts = Counter()
    for task in TASKS:
        initial = row['initial'][task]; original = old['initial'][task]
        equal_tree(initial['planning_belief'], original['planning_belief'], 'planning belief remains the actual observed immutable FIRST FIT bank belief')
        require(initial['context_id'] == original['context_id'] and initial['head_version'] == original['head_versions']['FIRST_LOCAL'],
            'the teacher is the actual reused FIRST v0 of its own context')
        version = initial['head_version']; identity = dict(lifecycle=life,parent=parent,context_id=initial['context_id'],arm='FIRST_LOCAL')
        teacher = HeadVersions(source,checkpoint,identity,'LOCAL_RISK'); teacher.apply(version); teachers[task] = teacher
        heads[task] = {}; versions[task] = {arm:version for arm in UPDATING_ARMS}; beliefs[task] = initial['planning_belief']['estimated_p_four']
        for arm in UPDATING_ARMS:
            head = HeadVersions(source,checkpoint,dict(identity,arm=arm),'LOCAL_RISK'); head.apply(version); heads[task][arm] = head
        initial_means = {arm:check_evaluation(value,life,task,beliefs[task],None if arm=='SOURCE' else version)
            for arm,value in initial['evaluations'].items()}
        require(set(initial_means) == {'SOURCE','FIRST_LOCAL'}, 'new initial evaluation contains exactly SOURCE and actual FIRST')
        records['cells']['FIRST_'+task] = initial_means
    for number in (1,2):
        r = str(number)
        for task in TASKS:
            stage = row['rounds'][r][task]; other = 'B' if task=='A' else 'A'; first = row['initial'][task]['head_version']
            require(stage['groups'] == GROUPS and stage['replicas'] == REPLICAS and stage['teacher_unchanged']
                and stage['teacher_version'] == first, 'all rounds and both arms retain the exact same immutable FIRST teacher')
            equal_tree(stage['inactive_head_versions_before'], versions[other], 'inactive context head versions precede this stage unchanged')
            collector = old['rounds'][r][task]['collectors']['FIXED_FIRST']
            roots, probes = check_census(stage['census'],worlds[life,task,number],collector,teachers[task],first,
                life,parent,task,number,beliefs[task]); counts['literal_teacher_H2_probes'] += probes
            uniform = ground_uniforms(draw_seed(life,task,number),GROUPS)
            cell = dict(records['cells']['FIRST_'+task])
            for arm in UPDATING_ARMS:
                item = stage['arms'][arm]; head = heads[task][arm]; version = item['head_version']
                require(item['updates_before'] == versions[task][arm]['updates'] == head.receipts[-1]['updates']
                    and item['updates_after'] == version['updates'] == item['updates_before']+GROUPS,
                    'each actual private head advances exactly once per rootgroup from its own previous version')
                metadata = dict(schema='acfqp.query_supervision_groups.v319', lifecycle=life,parent=parent,task=task,
                    round=number,arm=arm,groups=GROUPS,replicas=REPLICAS,
                    sampling_unit='ROOTGROUP_FOUR_INDEPENDENT_FRESH_GROUND_SPAWNS', teacher_version=first,
                    draw_seed=draw_seed(life,task,number),true_probability=.1 if task=='A' else .5,
                    census_file=stage['census']['file'],target_rule='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH')
                artifact = item['supervision']['group_artifact']; arrays = artifact_arrays(artifact,GROUP_FIELDS,metadata)
                stats, kinds = check_group_arrays(arrays,roots[arm],uniform,metadata['true_probability'],teachers[task])
                check_supervision_work(item['supervision'],roots[arm],stats,kinds,metadata['draw_seed'],first['updates'],metadata['true_probability'])
                writes = check_group_fit(item['fit'],arrays,head)
                head.apply(version); versions[task][arm] = version
                cell[arm] = check_evaluation(item['evaluations'],life,task,beliefs[task],version)
                counts.update(physical_supervision_samples=GROUPS*REPLICAS,fitted_rootgroups=GROUPS,
                    independently_checked_joint_targets=GROUPS*REPLICAS,independently_checked_selected_actions=GROUPS*REPLICAS,
                    actual_parameter_writes_per_head=writes,group_artifact_array_bytes=artifact['array_bytes'],new_head_versions=1)
                counts.update({'target_kind_'+str(kind):int(np.count_nonzero(kinds==kind)) for kind in (1,2,3)})
            for key in ('rootgroup_updates','current_predictions','reward_predictions','win_predictions','table_lookups'):
                require(stage['arms']['FACTUAL_LOCAL']['fit']['learning_counts'][key] == stage['arms']['QUERY_LOCAL']['fit']['learning_counts'][key],
                    'both arms receive equal rootgroup supervision and current prediction budgets')
            equal_tree(stage['inactive_head_versions_after'], versions[other], 'inactive actual bank versions survive the entire stage without updates')
            records['cells']['ROUND'+r+'_'+task] = cell
    equal_tree(row['final_head_versions'], versions, 'all final private head versions retain their actual own context and lineage')
    return records, counts


def check_accounting(document, previous, worlds, replay):
    lives, account = document['by_lifecycle'], document['accounting']
    stages = [row['rounds'][r][task] for row in lives for r in ('1','2') for task in TASKS]
    evaluations = [value for row in lives for initial in row['initial'].values() for value in initial['evaluations'].values()]
    evaluations += [stage['arms'][arm]['evaluations'] for stage in stages for arm in UPDATING_ARMS]
    items = [stage['arms'][arm] for stage in stages for arm in UPDATING_ARMS]
    census = [stage['census'] for stage in stages]; groups = [item['supervision']['group_artifact'] for item in items]
    heads = [item['head_version'] for item in items]; expected_arms = {}
    common = sum_counts(value['query']['counts'] for value in census)
    common_cpu = sum(value['query']['cpu_seconds']+value['anchor_cpu_seconds'] for value in census)
    for arm in UPDATING_ARMS:
        selected = [stage['arms'][arm] for stage in stages]
        expected_arms[arm] = dict(new_training_raw_tiles=4194304, rootgroups=1048576,
            training_environment_counts=sum_counts(item['supervision']['environment_counts'] for item in selected),
            supervision_counts=sum_counts(item['supervision']['counts'] for item in selected),
            supervision_planning_counts=sum_counts(item['supervision']['planning_counts'] for item in selected),
            supervision_representation_counts=sum_counts(item['supervision']['representation_counts'] for item in selected),
            fit_counts=sum_counts(item['fit']['learning_counts'] for item in selected),
            normalization_counts=sum_counts(item['fit']['normalization_counts'] for item in selected),
            supervision_cpu_seconds=sum(item['supervision']['cpu_seconds'] for item in selected),
            fit_cpu_seconds=sum(item['fit']['cpu_seconds'] for item in selected),
            economic_census_query_counts=common,economic_census_cpu_seconds=common_cpu)
    worker = sum(parent['cpu_seconds'] for parent in document['parent_receipts'])
    compiler = sum(parent['compiler_cpu_seconds'] for parent in document['parent_receipts'])
    coordinator = account['coordinator_cpu_seconds']; cpu = worker+compiler+coordinator
    inherited = previous['accounting']['economic_source_and_target_cpu_seconds']
    expected = dict(source_physical_training_repeated=False,initial_adaptation_repeated=False,new_training_raw_tiles=8388608,
        per_arm=expected_arms,retained_raw_tiles_reconstructed=4194304,
        retained_trace_records_parsed=sum(row['extraction']['parsed_records'] for row in lives),
        retained_compressed_trace_bytes_read=sum(row['extraction']['compressed_bytes_read'] for row in lives),
        retained_selected_training_records=sum(row['extraction']['selected_training_records'] for row in lives),
        retained_fact_read_cpu_seconds=sum(row['extraction']['cpu_seconds'] for row in lives),new_evaluation_games=6144,
        new_evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        new_evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),physical_census_query_counts=common,
        physical_census_planning_counts=sum_counts(value['query']['planning_counts'] for value in census),
        physical_census_representation_counts=sum_counts(value['query']['representation_counts'] for value in census),
        census_files=64,census_saved_bytes=sum(value['saved_bytes'] for value in census),group_files=128,
        group_saved_bytes=sum(value['saved_bytes'] for value in groups),group_array_bytes=sum(value['array_bytes'] for value in groups),
        new_head_files=128,new_head_saved_bytes=sum(value['saved_bytes'] for value in heads),worker_cpu_seconds=worker,
        compiler_cpu_seconds=compiler,coordinator_cpu_seconds=coordinator,new_experiment_cpu_seconds=cpu,
        inherited_successful_source_and_v317_cpu_seconds=inherited,economic_source_v317_and_experiment_cpu_seconds=inherited+cpu)
    equal_tree({key:account[key] for key in expected}, expected, 'all new physical/economic shared queries groups reads files and CPU close once')
    require(account['retained_trace_records_parsed'] == replay['decoded_canonical_rows']
        and account['retained_selected_training_records'] == 64*POST_RAW//256
        and account['retained_compressed_trace_bytes_read'] == sum(parent['trace_bytes'] for parent in previous['parent_receipts']),
        'only the prescribed retained post batches are reconstructed while all four trace reads receive physical cost')
    size = 4*11**6
    for row in lives:
        life = row['lifecycle']; extraction = row['extraction']
        expected_bytes = sum(136*worlds[life,task,r].ends[-1]+12*len(worlds[life,task,r].games) for task in TASKS for r in (1,2))
        require(extraction['new_raw_tiles'] == 0 and extraction['reconstructed_raw_tiles'] == 4*POST_RAW
            and extraction['dataset_array_bytes'] == expected_bytes and 0. <= extraction['reconstruction_cpu_seconds'] <= extraction['cpu_seconds'],
            'retained complete factual arrays and reconstruction compute are paid reads without relabeling old acquisition as new')
        for task, setups in row['head_setups'].items():
            require(set(setups) == {'FIRST_LOCAL',*UPDATING_ARMS}, 'each bank allocates exactly one restored teacher and two private learner heads')
            for arm, setup in setups.items():
                counts = setup['setup_counts']
                require(counts['source_parameters_copied'] == size and counts['source_weight_bytes_copied'] == 8*size
                    and counts['allocated_weight_parameters'] == 2*size and counts['allocated_weight_bytes'] == 16*size
                    and counts['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                    'all restored and private heads charge actual two-table initialization allocation')
                if arm != 'FIRST_LOCAL':
                    require(counts['first_parameters_copied'] == 2*size and counts['first_weight_bytes_copied'] == 16*size,
                        'both learners initialize by an actual private dual-table copy of the same FIRST teacher')
                else:
                    equal_tree(setup['restored_version'], row['initial'][task]['head_version'], 'teacher restoration names the actual frozen FIRST sparse checkpoint')
    require(worker >= 0. and compiler >= 0. and coordinator >= 0. and account['wall_seconds'] > 0.
        and 'not added twice' in account['scope'] and 'unknown' in account['scope'],
        'actual new compute is closed once and preserves unknown historical dynamics/failed-attempt costs')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.query_supervision.v319' and document['status'] in ('EXPERIMENT_COMPLETE','HOLD_CUTOFF'),
        'normal V319 complete grouped-supervision terminal receipt')
    source_path = Path(document['source_summary']).resolve(); previous = json_file(source_path)
    prior = json_file(source_path.parent/'audit.json'); prior_execution = json_file(source_path.parent/'audit_execution.json')
    require(previous['schema'] == 'acfqp.greedy_targets.v317' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid'] and prior_execution['exit_code'] == 0,
        'new query supervision uses the prior successful independently audited FIRST cohort without rerunning its full audit')
    config = expected_configuration(source_path)
    equal_tree(json_file(directory/'configuration.json'), config, 'frozen exact V319 groups streams reset access target and evidence contract')
    equal_tree(document['settings'], config, 'terminal scientific settings retain the full frozen grouped supervision contract')
    equal_tree(document['source_provenance'], previous['source_provenance'], 'all four SOURCE parents are unchanged audited fresh V312 provenance')
    require(document['scientific_gate'] == 'EXPLORATORY_NO_U006_AUTHORIZATION', 'coverage experiment preserves its exploratory scientific scope')
    lives = document['by_lifecycle']; old_lives = {row['lifecycle']:row for row in previous['by_lifecycle']}
    require([row['lifecycle'] for row in lives] == list(range(16)) and [row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all sixteen existing FIRST lives and all four frozen parent groups remain unconditional')
    worlds, replay = read_post_facts(previous); sources = {row['parent']:row for row in previous['source_provenance']['parents']}
    weights = {}; records = []; counts = Counter()
    for row in lives:
        parent = row['parent']; source = sources[parent]
        if parent not in weights:
            weights[parent] = read_source_weights(source['checkpoint'])
        record, inventory = check_lifecycle(row,old_lives[row['lifecycle']],worlds,weights[parent],source['checkpoint'])
        records.append(record); counts.update(inventory)
        print(json.dumps(dict(event='independent_query_supervision_life_checked',lifecycle=row['lifecycle'])),flush=True)
    check_analysis(document['summary'],records,lives); check_accounting(document,previous,worlds,replay)
    require(document['status'] == ('EXPERIMENT_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'any actual cutoff remains whole-cohort HOLD and never creates a replacement cohort')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,prior_v317_audit_status=prior['status'],
        prior_full_audit_repeated=False,**replay,**dict(counts),census_files=64,group_files=128,
        teacher_version_and_immutable_bank_beliefs_valid=True,all_census_paths_and_selector_draws_checked=True,
        every_new_physical_spawn_and_joint_target_checked=True,actual_group_means_and_normalized_writes_valid=True,
        new_training_raw_tiles=8388608,new_evaluation_games=6144,complete_game_endpoints=document['summary']['complete_game_endpoints'],
        primary_status=document['summary']['primary_self_improvement_status'],retained_improvement_supported=document['summary']['retained_improvement_supported'],
        coverage_status=document['summary']['coverage_intervention_status'],new_experiment_cpu_seconds=document['accounting']['new_experiment_cpu_seconds'],
        economic_source_v317_and_experiment_cpu_seconds=document['accounting']['economic_source_v317_and_experiment_cpu_seconds'],
        limitations='Conditional on four audited V312 parents and the reused sixteen-life FIRST cohort. '
            'One necessary retained post-batch physical reconstruction establishes the new census and roots; no prior full audit is repeated. '
            'Both arms have arbitrary-afterstate generative reset access, and their targets use the frozen bootstrapped FIRST teacher. '
            'These are explicit four-member one-step groups, not terminal MC games. All query paths, selector draws, physical supervision spawns, '
            'joint targets, group means and actual address-write counts are independently checked. FIRST H2 choice linkage is checked at fixed boundary probes; '
            'private parameter fits, new evaluation games and bootstrap draws are not independently rerun. '
            'Historical dynamics and archived failed-attempt CPU remain unknown.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    try:
        result = audit(args.output)
    except (ValueError,KeyError,FileNotFoundError,IndexError) as error:
        result = dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (args.output/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
