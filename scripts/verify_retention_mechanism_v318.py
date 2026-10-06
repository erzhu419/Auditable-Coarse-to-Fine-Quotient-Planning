#!/usr/bin/env python3
"""Independent V318 exact-state localization and frozen-FIRST diagnostic reader."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

import numpy as np

from verify_closed_loop_v313 import (ACTIONS, HeadVersions, close, equal_tree,
    json_file, physical_status, planning_counts, read_source_weights, require,
    sum_counts, swipe, check_representation)
from verify_greedy_targets_v317 import (FactualWorld, POST_RAW, feature_addresses,
    greedy_target_metadata, greedy_targets, post_seed, predict_components)

ENCODING = 'CELL_0_LOW_NIBBLE_UINT64'
NEW_VIEWS = ('R1_OWN_LOCAL', 'R2_OWN_LOCAL', 'R2_FIRST_FULL', 'R2_FIRST_LOCAL')
VIEWS = ('FIRST', 'R1_OWN_FULL', 'R1_OWN_LOCAL', 'R2_OWN_FULL',
    'R2_OWN_LOCAL', 'R2_FIRST_FULL', 'R2_FIRST_LOCAL')
MECHANISMS = {
    'TARGET_FIRST_FULL_MINUS_OWN_FULL': (('R2_FIRST_FULL', 1.), ('R2_OWN_FULL', -1.)),
    'LOCAL_OWN_MINUS_FULL_OWN': (('R2_OWN_LOCAL', 1.), ('R2_OWN_FULL', -1.)),
    'TARGET_BY_LOCAL_INTERACTION': (('R2_FIRST_LOCAL', 1.), ('R2_FIRST_FULL', -1.),
        ('R2_OWN_LOCAL', -1.), ('R2_OWN_FULL', 1.)),
    'R1_LOCAL_MINUS_FULL': (('R1_OWN_LOCAL', 1.), ('R1_OWN_FULL', -1.)),
}


def board_keys(boards):
    """Lossless supported full-board encoding, with cell zero in the low nibble."""
    cells = np.asarray(boards, dtype=np.int32).reshape(-1, 16)
    require(np.all((cells >= 0) & (cells < 16)), 'supported ranks fit the actual four-bit full-board encoding')
    result = np.zeros(len(cells), dtype=np.uint64)
    for cell in range(16):
        result |= cells[:, cell].astype(np.uint64) << np.uint64(4*cell)
    return result


def exact_fit_support(boards, fit_end, radix=11):
    cells = np.asarray(boards, dtype=np.int32)[:fit_end]
    selected = cells[np.max(cells, axis=1) < radix]
    return np.unique(board_keys(selected))


def support_contains(keys, board, counts):
    key = int(board_keys([board])[0]); low, high = 0, len(keys)
    counts.update(membership_queries=1, encoded_board_cells=16)
    while low < high:
        middle = low+(high-low)//2
        counts['key_comparisons'] += 1
        if int(keys[middle]) < key:
            low = middle+1
        else:
            high = middle
    if low < len(keys):
        counts['key_comparisons'] += 1
        return int(keys[low]) == key
    return False


def leaf_components(board, head, radix=11):
    addresses = feature_addresses([board], radix)[0]
    reward = sum(float(head.reward[index]) for index in addresses)
    logit = sum(float(head.terminal[index]) for index in addresses)
    probability = 1./(1.+math.exp(-logit)) if logit >= 0. else math.exp(logit)/(1.+math.exp(logit))
    return reward, probability, reward+8.*(probability-.5)


def literal_localized_choose(board, updated, base, keys, probability, radix=11):
    """Gate both actual tables together at each nonWIN H2 prediction afterstate."""
    counts = Counter(); choices = {}
    if max(board) >= radix:
        return dict(action=None, afterstate=list(board), score=0, tail_value=4., value=4.,
            status='WON', action_values={}, support_counts={})

    def direct(position):
        if max(position) >= radix:
            return 4.
        inner = {}
        for action in ACTIONS:
            after, score = swipe(position, action)
            if after == list(position):
                continue
            if max(after) >= radix:
                tail = 4.
            else:
                on_support = support_contains(keys, after, counts)
                counts['updated_head_queries' if on_support else 'base_head_queries'] += 1
                tail = leaf_components(after, updated if on_support else base, radix)[2]
            inner[action] = score/2048.+tail
        return max(inner.values()) if inner else -4.

    for action in ACTIONS:
        after, score = swipe(board, action)
        if after == list(board):
            continue
        if max(after) >= radix:
            tail = 4.
        else:
            empty = [cell for cell, value in enumerate(after) if value == 0]
            tail = 0.
            for cell in empty:
                for rank in (1, 2):
                    spawned = list(after); spawned[cell] = rank
                    weight = (1.-probability if rank == 1 else probability)/len(empty)
                    tail += weight*direct(spawned)
        choices[action] = dict(afterstate=after, score=score, tail_value=tail, value=score/2048.+tail)
    if not choices:
        return dict(action=None, afterstate=list(board), score=0, tail_value=-4., value=-4.,
            status='LOST', action_values={}, support_counts=dict(counts))
    selected = max(choices, key=lambda action: choices[action]['value'])
    return dict(action=selected, **choices[selected], status='ACTIVE', action_values=choices, support_counts=dict(counts))


def read_a_facts(previous):
    """The only necessary old raw pass: reconstruct all A post batches, no initial/B audit."""
    lives = {row['lifecycle']: row for row in previous['by_lifecycle']}
    worlds = {}; decoded = selected_rows = 0
    for parent in previous['parent_receipts']:
        with gzip.open(parent['trace_file'], 'rt') as stream:
            for line in stream:
                row = json.loads(line); decoded += 1
                if row['kind'] not in ('TRAIN', 'ACQUISITION_SNAPSHOT') or row.get('phase') not in ('A_R1', 'A_R2'):
                    continue
                life = lives[row['lifecycle']]; round_index = int(row['phase'][-1])
                require(row['parent'] == parent['parent'] == life['parent'] == life['lifecycle'] % 4,
                    'all sixteen A diagnostics retain their actual frozen SOURCE parent')
                key = life['lifecycle'], round_index
                if key not in worlds:
                    first = life['initial']['A']; actor = first['head_versions']['FIRST_LOCAL']
                    identity = dict(lifecycle=life['lifecycle'], parent=life['parent'], arm='FIXED_FIRST',
                        batch_id=row['phase'], phase=row['phase'], true_p_four=.1,
                        model_p_four=first['planning_belief']['estimated_p_four'], task='A',
                        actor_head_updates=actor['updates'], collector_policy_kind='LOCAL_RISK',
                        actor_version=actor, stream_seed=post_seed(life['lifecycle'], 'A', round_index))
                    worlds[key] = FactualWorld(identity['stream_seed'], POST_RAW, .1, identity, 'LOCAL_RISK')
                world = worlds[key]
                (world.train if row['kind'] == 'TRAIN' else world.checkpoint)(row)
                selected_rows += 1
    require(set(worlds) == {(life, round_index) for life in range(16) for round_index in (1, 2)}
        and all(world.snapshot is not None for world in worlds.values()),
        'unconditional diagnostics include both fixed-FIRST A rounds for every one of the sixteen lives')
    return worlds, dict(decoded_canonical_rows=decoded, reconstructed_A_rows=selected_rows,
        reconstructed_A_raw_tiles=32*POST_RAW)


def apply_counterfactual_version(head, receipt):
    require(head.version == 1 and receipt['arm'] == 'FIRST_BOOTSTRAP_LOCAL'
        and receipt['version'] == 2 and receipt['base_file'] == head.file,
        'frozen-FIRST target intervention branches from the actual GREEDY v1 current head')
    identity = dict(head.identity, arm='FIRST_BOOTSTRAP_LOCAL')
    require(receipt['schema'] == 'acfqp.head_version.v313' and receipt['head_kind'] == 'LOCAL_RISK'
        and all(receipt[key] == value for key, value in identity.items())
        and receipt['source_checkpoint'] == head.source_checkpoint and receipt['default_terminal'] == 0.,
        'actual counterfactual head retains its own lifecycle context and fresh SOURCE lineage')
    path = Path(receipt['file'])
    require(path.stat().st_size == receipt['saved_bytes'], 'actual counterfactual sparse head saved bytes')
    metadata_keys = ('schema', 'head_kind', 'lifecycle', 'parent', 'context_id', 'arm', 'version',
        'updates', 'file', 'base_file', 'source_checkpoint', 'default_terminal', 'parameter_count',
        'reward_indices_count', 'terminal_indices_count')
    with np.load(path, allow_pickle=False) as artifact:
        require(set(artifact.files) == {'reward_indices', 'reward_values', 'terminal_indices',
            'terminal_values', 'metadata_json'}, 'counterfactual version preserves the two actual sparse tables')
        equal_tree(json.loads(str(artifact['metadata_json'])), {key:receipt[key] for key in metadata_keys},
            'saved FIRST-bootstrap counterfactual version ownership')
        for name, weights in (('reward', head.reward), ('terminal', head.terminal)):
            indices, values = artifact[name+'_indices'], artifact[name+'_values']
            require(indices.dtype == np.int64 and values.dtype == np.float64 and indices.ndim == values.ndim == 1
                and len(indices) == len(values) == receipt[name+'_indices_count']
                and np.all((indices >= 0) & (indices < weights.size))
                and np.all(indices[1:] > indices[:-1]) and np.all(np.isfinite(values))
                and np.all(weights[indices] != values), 'counterfactual sparse writes are actual distinct changed addresses')
            weights[indices] = values
    require(receipt['parameter_count'] == head.reward.size and receipt['scan_parameters'] == 2*head.reward.size
        and receipt['copy_parameters'] == receipt['copy_bytes'] == 0
        and receipt['changed_parameters'] == receipt['reward_indices_count']+receipt['terminal_indices_count'],
        'immutable v1 reference removes any comparison snapshot copy while charging both actual table scans')
    head.identity = identity; head.version = 2; head.file = str(path)


def check_support(receipt, boards, dataset, identity, source_batch):
    fit_end, n = dataset['fit_step_end'], dataset['fit_game_count']
    keys = exact_fit_support(boards, fit_end)
    nonwin = int(np.count_nonzero(np.max(boards[:fit_end], axis=1) < 11))
    metadata = dict(schema='acfqp.exact_fit_support.v318', **identity, task='A',
        source_batch=source_batch, goal_rank=11, encoding=ENCODING,
        fit_step_end=fit_end, fit_game_count=n, trained_nonwin_steps=nonwin, unique_count=len(keys))
    equal_tree(receipt['metadata'], metadata, 'exact support ownership follows its actual fixed FIRST complete FIT batch')
    path = Path(receipt['file'])
    require(path.stat().st_size == receipt['saved_bytes'], 'actual support artifact saved bytes')
    with np.load(path, allow_pickle=False) as artifact:
        require(set(artifact.files) == {'keys', 'metadata_json'}, 'support artifact contains only exact keys and actual ownership metadata')
        equal_tree(json.loads(str(artifact['metadata_json'])), metadata, 'saved exact-support metadata')
        require(artifact['keys'].dtype == np.uint64 and np.array_equal(artifact['keys'], keys),
            'all and only unique nonWIN FIT full boards enter exact support; HELDOUT and tails never enter')
    counts = dict(fit_boards_examined=fit_end, fit_board_cells_examined=16*fit_end,
        winning_fit_boards_excluded=fit_end-nonwin, encoded_fit_boards=nonwin,
        encoded_fit_board_cells=16*nonwin, support_sort_calls=1,
        support_sort_input_keys=nonwin, unique_support_keys=len(keys))
    require(receipt['encoding'] == ENCODING and receipt['goal_rank'] == 11
        and receipt['unique_count'] == len(keys) and receipt['bytes'] == 8*len(keys),
        'exact support physical unique-key storage and lossless encoding are charged')
    equal_tree(receipt['counts'], counts, 'actual support examines every complete FIT row and encodes selected nonWIN rows once')
    require(receipt['cpu_seconds'] >= 0. and receipt['save_cpu_seconds'] >= 0., 'support construction and save retain actual CPU receipts')
    return keys


def check_support_queries(counts, predictions):
    queries = counts.get('membership_queries', 0)
    require(queries == predictions and counts.get('encoded_board_cells', 0) == 16*queries
        and counts.get('base_head_queries', 0)+counts.get('updated_head_queries', 0) == queries,
        'one exact support gate selects both component tables for each actual nonWIN H2 leaf prediction')
    require(counts.get('key_comparisons', 0) >= 0, 'actual binary-search comparisons remain charged')


def check_evaluation(value, life, belief, localized):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2',
        'every diagnostic view uses its unchanged actual FIRST bank belief and H2 planner')
    games = value['game_summaries']
    require(len(games) == 32 and [game['seed'] for game in games] ==
        [317900000000+life*1000000+episode for episode in range(32)],
        'new model interventions use the exact paired V317 A natural-game seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'all diagnostic natural games retain their actual frozen horizon')
        status = game['status']
        if status == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE',
                'every diagnostic cutoff remains explicit and blocks family support')
            bonus = 0.
        else:
            require(status in ('WON', 'LOST') and physical_status(game['final_board']) == status,
                'diagnostic game final board preserves its natural WIN/LOST label')
            bonus = 4. if status == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'diagnostic intervention keeps original terminal game utility')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    environment = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32, ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    equal_tree(value['counts']['environment'], environment, 'all new physical evaluation tiles and swipes are charged once')
    planning_counts(value['counts']['planning'], steps, depth=2)
    predictions = value['counts']['planning'].get('value_predictions', 0)
    check_representation(value['representation_counts'], 'LOCAL_RISK', predictions)
    require(not value['counts'].get('learning', {}), 'all diagnostic evaluation views remain frozen without fitting')
    if localized:
        check_support_queries(value['support_counts'], predictions)
    else:
        require(not value.get('support_counts', {}), 'full-head evaluation does not perform exact-state gate work')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games), wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games), cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[episode for episode, game in enumerate(games) if game['status'] == 'CUTOFF'], steps=steps)


def effect_status(interval, complete):
    if not complete:
        return 'HOLD_CUTOFF'
    return 'SUPPORTED_GAIN' if interval[0] > 0. else 'SUPPORTED_LOSS' if interval[1] < 0. else 'UNRESOLVED'


def check_effect(saved, values, complete, family):
    require(len(values) == 16 and close(saved['mean'], mean(values)), 'every diagnostic effect keeps all sixteen signed lifecycle deltas')
    equal_tree(saved['lifecycle_deltas'], {str(life):value for life, value in enumerate(values)},
        'all retained lifecycle effects are paired within their actual A bank')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent, group in enumerate(groups)},
        'diagnostic resampling is conditional on all four frozen parent groups')
    minimum, maximum = mean(min(group) for group in groups), mean(max(group) for group in groups)
    low, high = saved['ci95']
    require(minimum-1e-10 <= low <= high <= maximum+1e-10, 'pointwise effect interval retains the fixed-parent feasible range')
    require(saved['improved_equal_worse'] == [sum(value > 0. for value in values),
        sum(value == 0. for value in values), sum(value < 0. for value in values)],
        'adverse diagnostic lifecycles remain in the realized effect signs')
    if family:
        lower, upper = saved['ci98_75']
        require(minimum-1e-10 <= lower <= low <= high <= upper <= maximum+1e-10,
            'the four-effect Bonferroni 98.75 percent interval encloses its pointwise 95 percent interval')
        require(saved['status98_75'] == effect_status((lower, upper), complete),
            'mechanism support uses the prespecified family interval rather than the pointwise interval')
    else:
        lower, upper = saved['ci98_75']
        require(minimum-1e-10 <= lower <= low <= high <= upper <= maximum+1e-10
            and saved['status95'] == effect_status((low, high), complete),
            'own-FIRST comparisons remain secondary pointwise effects')


def sample_positions(boards, fit_end, complete_end, split):
    start, stop = (0, fit_end) if split == 'FIT' else (fit_end, complete_end)
    eligible = np.flatnonzero(np.max(boards[start:stop], axis=1) < 11)+start
    require(len(eligible) > 0, 'each prescribed complete FIT/HELDOUT split contains nonWIN diagnostic states')
    samples = eligible if len(eligible) <= 64 else eligible[np.linspace(0, len(eligible)-1, 64, dtype=np.int64)]
    return list(dict.fromkeys((int(samples[0]), int(samples[-1]))))


def read_targets(artifact, metadata):
    equal_tree(artifact['metadata'], metadata, 'actual native target artifact bootstrap and current-head ownership')
    path = Path(artifact['file']); steps = metadata['fitted_steps']
    require(path.stat().st_size == artifact['saved_bytes'], 'actual native target saved bytes')
    result = []
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == {'targetreward', 'targetwin', 'targetkind', 'selected_action', 'metadata_json'},
            'actual greedy target artifact retains the paired values, kind, selected branch and explicit metadata')
        equal_tree(json.loads(str(saved['metadata_json'])), metadata, 'saved actual native target metadata')
        for key, dtype in (('targetreward', np.float64), ('targetwin', np.float64), ('targetkind', np.int32), ('selected_action', np.int32)):
            value = saved[key]
            require(value.dtype == dtype and value.shape == (steps,), 'each actual target array covers every complete FIT row')
            result.append(value)
    require(artifact['save_cpu_seconds'] >= 0., 'target serialization CPU remains recorded inside worker CPU')
    return tuple(result)


def check_reproduction(reproduction, old_fit, previous_version):
    fit = reproduction['fit']
    for key in ('head_exact', 'targets_exact', 'matched_counts'):
        require(reproduction[key] is True, 'actual reproduction must precede inference and match parameters targets and counts')
    require(reproduction['reward_max_abs_diff'] == reproduction['risk_max_abs_diff'] == 0.,
        'producer parameter-reproduction comparison reports exact equality rather than a tolerance')
    for key in ('method', 'alpha', 'fitted_games', 'fitted_steps', 'trained_afterstates', 'learning_counts',
                'normalization_counts', 'target_counts', 'bootstrap_counts', 'bootstrap_planning_counts',
                'representation_counts', 'first_sample', 'last_sample'):
        equal_tree(fit[key], old_fit[key], 'new actual reproduction retains unchanged native fit work and sample receipts')
    metadata = greedy_target_metadata(previous_version, fit['fitted_games'], fit['fitted_steps'])
    now = read_targets(fit['target_artifact'], metadata)
    old = read_targets(old_fit['target_artifact'], metadata)
    require(all(np.array_equal(a, b) for a, b in zip(now, old)),
        'all newly reproduced native targets exactly match the already audited V317 actual targets')
    return sum(value.nbytes for value in now), len(now[0])


def check_first_targets(fit, boards, postspawn, games, n, first, first_version, current_version, old_fit):
    require(fit['method'] == 'FIRST_BOOTSTRAP_LOCAL' and fit['alpha'] == .0025
        and fit['bootstrap_mode'] == 'FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD'
        and fit['bootstrap_version'] == first_version and fit['current_start_version'] == current_version
        and fit['frozen_game_start_predictions'] and fit['frozen_batch_start_bootstrap'],
        'target intervention freezes FIRST v0 bootstrap while current residuals begin at actual own v1')
    steps = sum(game['steps'] for game in games[:n])
    metadata = dict(greedy_target_metadata(first_version, n, steps), schema='acfqp.frozen_first_greedy_targets.v318',
        bootstrap_mode='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD', current_start_version=current_version)
    actual = read_targets(fit['target_artifact'], metadata)
    expected = greedy_targets(boards, postspawn, games, n, first)
    require(np.array_equal(actual[2], expected[2]) and np.array_equal(actual[3], expected[3]),
        'every frozen-FIRST target retains its exact single combined-greedy chosen branch and terminal kind')
    require(np.allclose(actual[0], expected[0], rtol=1e-12, atol=1e-12)
        and np.allclose(actual[1], expected[1], rtol=1e-12, atol=1e-12),
        'every actual reward and WIN target reads the frozen FIRST head on the same independently chosen branch')
    for key in ('fitted_games', 'fitted_steps', 'trained_afterstates', 'learning_counts',
                'normalization_counts', 'representation_counts', 'bootstrap_counts', 'bootstrap_planning_counts'):
        equal_tree(fit[key], old_fit[key], 'FIRST target intervention keeps identical factual states address work and candidate query counts')
    kinds = expected[2]
    target_counts = dict(terminal_game_labels=n, goal_checks=steps,
        skipped_winning_afterstates=int(np.count_nonzero(kinds == 0)), postspawn_board_reads=int(np.count_nonzero(kinds)),
        reward_target_assignments=int(np.count_nonzero(kinds)), win_target_assignments=int(np.count_nonzero(kinds)),
        bootstrap_greedy_targets=int(np.count_nonzero(kinds == 1)), analytic_selected_win_targets=int(np.count_nonzero(kinds == 2)),
        postspawn_lost_targets=int(np.count_nonzero(kinds == 3)), target_kind_reads=steps)
    equal_tree(fit['target_counts'], target_counts, 'actual FIRST-bootstrap terminal and target generation work')
    for sample in (fit['first_sample'], fit['last_sample']):
        index = sample['step']
        require(close(sample['reward_target'], actual[0][index]) and close(sample['risk_target'], actual[1][index])
            and close(sample['reward_error'], sample['reward_target']-sample['reward_prediction'])
            and close(sample['risk_error'], sample['risk_target']-sample['risk_probability'])
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(sample['risk_probability']-.5)),
            'new current-head residual examples consume the actual intervention arrays')
    return sum(value.nbytes for value in actual), steps


def check_probe(chosen, board, updated, base, keys, p, localized):
    expected = literal_localized_choose(board, updated, base, keys, p)
    equal_tree({key:chosen[key] for key in expected if key != 'support_counts'},
        {key:value for key, value in expected.items() if key != 'support_counts'},
        'each declared probe uses literal seeded-fact H2 values and exact joint R/WIN leaf gating')
    planning_counts(chosen['counts'], 1, depth=2)
    predictions = chosen['counts'].get('value_predictions', 0)
    check_representation(chosen['representation_counts'], 'LOCAL_RISK', predictions)
    if localized:
        equal_tree(chosen['support_counts'], expected['support_counts'],
            'every literal probe support hit fallback and binary-search comparison count')
        check_support_queries(chosen['support_counts'], predictions)
    else:
        require(not chosen.get('support_counts', {}), 'full-head diagnostic probes do not perform gate work')


def check_lifecycle(row, old, worlds, source, source_checkpoint):
    life, parent = row['lifecycle'], row['parent']; initial = old['initial']['A']
    originals = {str(r):old['rounds'][str(r)]['A']['arms']['GREEDY_LOCAL'] for r in (1, 2)}
    versions = dict(FIRST=initial['head_versions']['FIRST_LOCAL'],
        R1=originals['1']['head_version'], R2=originals['2']['head_version'])
    require(parent == life % 4 and row['planning_belief'] == initial['planning_belief'],
        'all sixteen diagnostic A banks retain their original observed FIRST belief')
    equal_tree(row['source_versions'], versions, 'every source model version is the audited actual V317 FIRST GREEDY v1 and v2')
    identity = dict(lifecycle=life, parent=parent, context_id=initial['context_id'], arm='GREEDY_LOCAL')
    first = HeadVersions(source, source_checkpoint, identity, 'LOCAL_RISK'); first.apply(versions['FIRST'])
    own1 = HeadVersions(source, source_checkpoint, identity, 'LOCAL_RISK'); own1.apply(versions['FIRST']); own1.apply(versions['R1'])
    own2 = HeadVersions(source, source_checkpoint, identity, 'LOCAL_RISK'); own2.apply(versions['FIRST']); own2.apply(versions['R1']); own2.apply(versions['R2'])
    counter = HeadVersions(source, source_checkpoint, identity, 'LOCAL_RISK'); counter.apply(versions['FIRST']); counter.apply(versions['R1'])
    keys = {}; factual = {}
    for r in ('1', '2'):
        world = worlds[life, int(r)]; batch = old['rounds'][r]['A']['collectors']['FIXED_FIRST']; dataset = batch['dataset']
        require(batch['actor_version'] == versions['FIRST'] and world.expected_identity['actor_version'] == versions['FIRST'],
            'both diagnostic factual batches were physically collected by unchanged FIRST v0')
        boards, postspawn = np.concatenate(world.afterstate_chunks), np.concatenate(world.postspawn_chunks)
        source_batch = dict(actor_version=versions['FIRST'], stream_seed=world.seed,
            fit_step_end=dataset['fit_step_end'], fit_game_count=dataset['fit_game_count'])
        keys[r] = check_support(row['supports'][r], boards, dataset,
            dict(lifecycle=life, parent=parent, round=int(r)), source_batch)
        factual[r] = (boards, postspawn, world.games, dataset)
    require(set(row['supports']) == {'1', '2'}, 'each diagnostic life retains both exact current-round support sets')
    reproduction_bytes, reproduction_rows = check_reproduction(row['reproduction'], originals['2']['fit'], versions['R1'])
    boards, postspawn, games, dataset = factual['2']
    target_bytes, target_rows = check_first_targets(row['counterfactual']['fit'], boards, postspawn, games,
        dataset['fit_game_count'], first, versions['FIRST'], versions['R1'], originals['2']['fit'])
    new_version = row['counterfactual']['head_version']
    require(new_version['updates'] == versions['R1']['updates']+row['counterfactual']['fit']['trained_afterstates'],
        'actual intervention current head advances once per shared nonWIN FIT state')
    apply_counterfactual_version(counter, new_version)
    view_heads = dict(FIRST=(first, first, np.asarray([], dtype=np.uint64)),
        R1_OWN_FULL=(own1, own1, np.asarray([], dtype=np.uint64)), R1_OWN_LOCAL=(own1, first, keys['1']),
        R2_OWN_FULL=(own2, own2, np.asarray([], dtype=np.uint64)), R2_OWN_LOCAL=(own2, own1, keys['2']),
        R2_FIRST_FULL=(counter, counter, np.asarray([], dtype=np.uint64)), R2_FIRST_LOCAL=(counter, own1, keys['2']))
    references = dict(FIRST=initial['evaluations']['FIRST_LOCAL']['H2'],
        R1_OWN_FULL=originals['1']['evaluations']['H2'], R2_OWN_FULL=originals['2']['evaluations']['H2'])
    p = initial['planning_belief']['estimated_p_four']; values = {}
    require(set(row['evaluations']) == set(VIEWS), 'all seven fixed diagnostic view endpoints are retained')
    for view in VIEWS:
        evaluated = row['evaluations'][view]; localized = view.endswith('_LOCAL')
        if view in references:
            equal_tree(evaluated, references[view], 'reused full-head evaluation is the exact already-audited V317 reference')
        else:
            head_version = versions['R1'] if view == 'R1_OWN_LOCAL' else versions['R2'] if view == 'R2_OWN_LOCAL' else new_version
            base_version = versions['FIRST'] if view == 'R1_OWN_LOCAL' else versions['R1'] if localized else None
            support_file = row['supports']['1' if view.startswith('R1') else '2']['file'] if localized else None
            equal_tree({key:evaluated[key] for key in ('view', 'head_version', 'base_head_version', 'support_file')},
                dict(view=view, head_version=head_version, base_head_version=base_version, support_file=support_file),
                'each new view binds actual updated/base versions and its own current-round exact support')
        values[view] = check_evaluation(evaluated, life, p, localized)
    expected_probes = []
    for r in ('1', '2'):
        boards, postspawn, games, dataset = factual[r]
        for split in ('FIT', 'HELDOUT'):
            for index in sample_positions(boards, dataset['fit_step_end'], sum(game['steps'] for game in games), split):
                expected_probes.append((int(r), split, index, postspawn[index].tolist()))
    require(len(row['probe_rows']) == len(expected_probes) == 8,
        'all declared first/last evenly spaced FIT and HELDOUT probes remain present in both rounds')
    probes = 0
    for probe, (r, split, index, board) in zip(row['probe_rows'], expected_probes):
        require(probe['round'] == r and probe['split'] == split and probe['index'] == index
            and probe['postspawn_board'] == board, 'probe positions are the prescribed actual same-pass postspawn facts')
        expected_views = {'R1_OWN_FULL', 'R1_OWN_LOCAL'} if r == 1 else {'R2_OWN_FULL', 'R2_OWN_LOCAL', 'R2_FIRST_FULL', 'R2_FIRST_LOCAL'}
        require(set(probe['views']) == expected_views, 'each factual probe retains all declared round-specific interventions')
        for view, chosen in probe['views'].items():
            updated, base, support = view_heads[view]
            check_probe(chosen, board, updated, base, support, p, view.endswith('_LOCAL')); probes += 1
    extraction = row['extraction']
    require(extraction['parent'] == parent and extraction['lifecycle'] == life and extraction['new_raw_tiles'] == 0
        and extraction['reconstructed_raw_tiles'] == 2*POST_RAW and extraction['selected_training_records'] == 2*POST_RAW//256,
        'each diagnostic extracts two paid old A batches without acquiring new training facts')
    return dict(lifecycle=life, parent=parent, values=values), dict(probe_rows=len(expected_probes),
        literal_view_probes=probes, first_target_rows=target_rows, reproduced_target_rows=reproduction_rows,
        new_target_array_bytes=target_bytes+reproduction_bytes)


def expected_configuration(source_summary):
    return dict(schema='acfqp.retention_mechanism_freeze.v318', source_summary=str(source_summary),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/RETENTION_MECHANISM_V318.md'),
        lifecycles=list(range(16)), parents=4, workers=4, task='A', rounds=[1, 2], alpha=.0025,
        actual_reproduction='EXACT_ALL_PARAMETERS_TARGET_ARRAYS_AND_NATIVE_COUNTS_BEFORE_INTERVENTION',
        counterfactual='FROZEN_FIRST_V0_WITH_ACTUAL_V1_CURRENT_HEAD',
        propagation='COUPLED_HEAD_SWITCH_AT_NONWIN_H2_LEAF_BY_EXACT_CURRENT_ROUND_NONWIN_FIT_BOARD',
        support_encoding=ENCODING, max_steps=8192, evaluation_games_per_view=32,
        new_views=list(NEW_VIEWS), expected_new_evaluation_games=2048, new_training_raw_tiles=0,
        evaluation_seed=317900000000, bootstrap_seed=31800001, bootstrap_draws=20000,
        mechanism_family_size=4, mechanism_ci_coverage=.9875, sample_nonwin_per_split=64,
        probe_positions='FIRST_AND_LAST_PER_SPLIT', stop_rule='NO_LIFE_SEED_ALPHA_SUPPORT_TARGET_OR_INTERVAL_SELECTION_RETAIN_CUTOFF')


def check_analysis(summary, records, lives):
    require(summary['bootstrap_seed'] == 31800001 and summary['bootstrap_draws'] == 20000,
        'all four frozen mechanism effects use the exact prespecified bootstrap contract')
    equal_tree(summary['mechanism_family'], dict(size=4, family_alpha=.05, interval_coverage=.9875, method='BONFERRONI'),
        'four two-sided prespecified mechanism effects retain Bonferroni 98.75 percent family coverage')
    require(set(summary['effects']) == set(MECHANISMS)
        and set(summary['secondary_own_first']) == set(VIEWS)-{'FIRST'},
        'all four mechanism effects and every own-FIRST secondary comparison remain present')
    cutoffs = [dict(lifecycle=row['lifecycle'], view=view, seed=game['seed']) for row in lives for view in VIEWS
        for game in row['evaluations'][view]['game_summaries'] if game['status'] == 'CUTOFF']
    complete = not cutoffs
    require(summary['complete_game_endpoints'] == complete and summary['cutoffs'] == cutoffs
        and summary['new_physical_evaluation_games'] == 2048, 'all natural endpoints retain cutoffs and count four physical new views only')
    for name, terms in MECHANISMS.items():
        deltas = [sum(coefficient*row['values'][view]['mean_game_utility'] for view, coefficient in terms) for row in records]
        check_effect(summary['effects'][name], deltas, complete, True)
    for view in set(VIEWS)-{'FIRST'}:
        deltas = [row['values'][view]['mean_game_utility']-row['values']['FIRST']['mean_game_utility'] for row in records]
        check_effect(summary['secondary_own_first'][view], deltas, complete, False)
    scope = summary['evidence_scope']
    require('all sixteen V317 A lives' in scope and 'No new training facts or independent confirmation' in scope
        and 'symmetry transfer' in scope, 'diagnostic scope retains fixed old coverage and blocks all exact-support-external generalization')


def check_accounting(document, previous, worlds, replay):
    lives, parents, account = document['by_lifecycle'], document['parent_receipts'], document['accounting']
    evaluations = [row['evaluations'][view] for row in lives for view in NEW_VIEWS]
    fits = [row[kind]['fit'] for row in lives for kind in ('reproduction', 'counterfactual')]
    supports = [support for row in lives for support in row['supports'].values()]
    worker = sum(parent['cpu_seconds'] for parent in parents)
    compiler = sum(parent['compiler_cpu_seconds'] for parent in parents)
    coordinator = account['coordinator_cpu_seconds']; new_cpu = worker+compiler+coordinator
    inherited = previous['accounting']['economic_source_and_target_cpu_seconds']
    expected = dict(new_training_raw_tiles=0, retained_raw_tiles_reconstructed=32*POST_RAW,
        retained_trace_records_parsed=sum(row['extraction']['parsed_records'] for row in lives),
        retained_compressed_trace_bytes_read=sum(row['extraction']['compressed_bytes_read'] for row in lives),
        retained_selected_training_records=sum(row['extraction']['selected_training_records'] for row in lives),
        retained_fact_read_cpu_seconds=sum(row['extraction']['cpu_seconds'] for row in lives),
        new_evaluation_games=2048, new_evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        localized_support_counts=sum_counts(value.get('support_counts', {}) for value in evaluations),
        fitted_states=sum(fit['trained_afterstates'] for fit in fits), fit_cpu_seconds=sum(fit['cpu_seconds'] for fit in fits),
        fit_counts=sum_counts(fit['learning_counts'] for fit in fits), support_files=32,
        support_saved_bytes=sum(support['saved_bytes'] for support in supports),
        support_array_bytes=sum(support['bytes'] for support in supports), target_files=32,
        target_saved_bytes=sum(fit['target_artifact']['saved_bytes'] for fit in fits), new_head_files=16,
        new_head_saved_bytes=sum(row['counterfactual']['head_version']['saved_bytes'] for row in lives),
        worker_cpu_seconds=worker, compiler_cpu_seconds=compiler, coordinator_cpu_seconds=coordinator,
        new_diagnostic_cpu_seconds=new_cpu, inherited_successful_source_and_v317_cpu_seconds=inherited,
        economic_source_v317_and_diagnostic_cpu_seconds=inherited+new_cpu)
    equal_tree({key:account[key] for key in expected}, expected, 'complete diagnostic physical games fit support target and actual CPU costs')
    require(account['retained_trace_records_parsed'] == replay['decoded_canonical_rows']
        and account['retained_selected_training_records'] == 32*POST_RAW//256
        and account['retained_compressed_trace_bytes_read'] == sum(parent['trace_bytes'] for parent in previous['parent_receipts']),
        'producer reads all four retained traces once and reconstructs only the prescribed A training rows')
    require(worker >= 0. and compiler >= 0. and coordinator >= 0. and account['wall_seconds'] > 0.,
        'actual diagnostic compute closure uses worker compiler and coordinator CPU once')
    size = 4*11**6
    for row in lives:
        life = row['lifecycle']; extraction = row['extraction']
        expected_bytes = sum(136*worlds[life, r].ends[-1]+12*len(worlds[life, r].games) for r in (1, 2))
        require(extraction['dataset_array_bytes'] == expected_bytes
            and 0. <= extraction['reconstruction_cpu_seconds'] <= extraction['cpu_seconds'],
            'two complete-prefix factual arrays and reconstruction CPU are contained in the single retained-fact reader')
        require(len(row['head_setups']) == 5, 'FIRST actual v1 actual v2 reproduction and intervention retain five real allocations')
        for index, setup in enumerate(row['head_setups']):
            counts = setup['setup_counts']
            require(counts['source_parameters_copied'] == size and counts['source_weight_bytes_copied'] == 8*size
                and counts['allocated_weight_parameters'] == 2*size and counts['allocated_weight_bytes'] == 16*size
                and counts['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                'all native diagnostic heads charge actual two-table allocation and SOURCE initialization')
            if index:
                require(counts['first_parameters_copied'] == 2*size and counts['first_weight_bytes_copied'] == 16*size,
                    'each private restored reproduction or intervention head retains its actual predecessor copy')
    require('not added twice' in account['scope'] and 'unknown' in account['scope'],
        'cost closure excludes double-added contained work and preserves unknown archived-failure and old-dynamics CPU')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.retention_mechanism.v318'
        and document['status'] in ('DIAGNOSTIC_COMPLETE', 'HOLD_CUTOFF'), 'normal V318 diagnostic terminal receipt')
    source_summary = Path(document['source_summary']).resolve(); previous = json_file(source_summary)
    prior_audit = json_file(source_summary.parent/'audit.json')
    prior_execution = json_file(source_summary.parent/'audit_execution.json')
    require(previous['schema'] == 'acfqp.greedy_targets.v317' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior_audit['status'] == 'PASS' and prior_audit['independent_valid'] and prior_execution['exit_code'] == 0
        and prior_audit['every_native_greedy_action_and_target_checked'] and prior_audit['fixed_first_collector_valid'],
        'diagnostic references require the successful independently audited complete V317 cohort without repeating its audit')
    config = expected_configuration(source_summary)
    equal_tree(json_file(directory/'configuration.json'), config, 'frozen V318 design and unchanged paired reference seeds')
    equal_tree(document['settings'], config, 'terminal V318 settings match the prespecified diagnostic configuration')
    require(document['scientific_gate'] == 'MECHANISM_DIAGNOSTIC_NOT_FORMAL_GATE',
        'V318 records model interventions as a diagnostic rather than new training confirmation')
    lives = document['by_lifecycle']; old_lives = {row['lifecycle']:row for row in previous['by_lifecycle']}
    require([row['lifecycle'] for row in lives] == list(range(16))
        and [row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all sixteen existing A lives and all four frozen parent groups remain unconditional')
    sources = {source['parent']:source for source in previous['source_provenance']['parents']}
    worlds, replay = read_a_facts(previous); records = []; counts = Counter()
    weights = {}
    for row in lives:
        parent = row['parent']; source = sources[parent]
        equal_tree(row['source'], source, 'diagnostic SOURCE provenance is the exact already audited fresh V312 parent')
        if parent not in weights:
            weights[parent] = read_source_weights(source['checkpoint'])
        record, inventory = check_lifecycle(row, old_lives[row['lifecycle']], worlds, weights[parent], source['checkpoint'])
        records.append(record); counts.update(inventory)
    check_analysis(document['summary'], records, lives); check_accounting(document, previous, worlds, replay)
    require(document['status'] == ('DIAGNOSTIC_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'),
        'any cutoff preserves diagnostic HOLD without deleting physical endpoints')
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4,
        prior_v317_audit_status=prior_audit['status'], prior_full_audit_repeated=False,
        retained_A_facts_reconstructed_once=True, **replay, **dict(counts), exact_support_files=32,
        counterfactual_head_versions=16, actual_version_lineage_valid=True,
        every_new_frozen_FIRST_target_and_action_checked=True, reproduced_target_arrays_exact=True,
        parameter_reproduction_evidence='PRODUCER_EXACT_ARRAY_COMPARISON_NO_INDEPENDENT_REFIT',
        literal_joint_leaf_gate_valid=True, immutable_bank_beliefs_valid=True,
        new_evaluation_games=2048, reused_reference_evaluation_games=1536, new_training_raw_tiles=0,
        complete_game_endpoints=document['summary']['complete_game_endpoints'],
        mechanism_status={name:value['status98_75'] for name, value in document['summary']['effects'].items()},
        new_diagnostic_cpu_seconds=document['accounting']['new_diagnostic_cpu_seconds'],
        economic_source_v317_and_diagnostic_cpu_seconds=document['accounting']['economic_source_v317_and_diagnostic_cpu_seconds'],
        limitations='Frozen interventions on all sixteen existing A lives, conditional on four V312 SOURCE parents and V317 coverage. '
            'One necessary A-only raw reconstruction establishes exact FIT support and sampled factual probes; no full prior audit is repeated. '
            'All new FIRST-bootstrap targets and selected actions are independently checked; reproduced targets are exactly compared to audited arrays. '
            'Parameter reproduction is the producer exact full-array comparison, not an independent refit. '
            'H2 values are independently recomputed at predeclared first/last FIT/HELDOUT probes; evaluation actions and bootstrap draws are not rerun. '
            'Exact-state localization blocks all external generalization including symmetry transfer. '
            'Historical dynamics and archived failed-attempt CPU remain unknown.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    try:
        result = audit(args.output)
    except (ValueError, KeyError, FileNotFoundError, IndexError) as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (args.output/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())




