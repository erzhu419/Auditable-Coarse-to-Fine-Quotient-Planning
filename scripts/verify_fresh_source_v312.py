#!/usr/bin/env python3
"""Independent compact-trace physics, SOURCE TD timing and measured-cost audit."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import random

import numpy as np

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_policy_data_v306 import board_status, swipe

GAMES = 4096
MAX_STEPS = 2000
PARAMETERS = 4*11**6
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
BASE_PATTERNS = ((0,1,2,4,5,6), (4,5,6,8,9,10), (0,1,2,3,4,5), (4,5,6,7,8,9))
ACTIONS = ('DOWN','LEFT','RIGHT','UP')


def source_seed(parent, episode):
    return 31200000000+1000000+parent*100000+10000+episode


def feature_patterns():
    patterns = []
    for pattern in BASE_PATTERNS:
        for reflected in (False,True):
            for rotations in range(4):
                cells = []
                for cell in pattern:
                    row,col = divmod(cell,4)
                    if reflected:
                        col = 3-col
                    for _ in range(rotations):
                        row,col = col,3-row
                    cells.append(4*row+col)
                patterns.append(cells)
    return np.asarray(patterns, dtype=np.int64)


PATTERNS = feature_patterns()


def unique_update_writes(afterstates):
    if not afterstates:
        return 0
    boards = np.asarray(afterstates, dtype=np.int64)
    require(boards.shape[1:] == (16,) and np.all((0<=boards)&(boards<11)),
        'only actual nonwinning afterstates enter the SOURCE value tables')
    addresses = np.zeros((len(boards),32), dtype=np.int64)
    for digit in range(6):
        addresses = 11*addresses+boards[:,PATTERNS[:,digit]]
    addresses += (np.arange(32)//8)*(11**6)
    addresses.sort(axis=1)
    return int(len(boards)+np.count_nonzero(addresses[:,1:] != addresses[:,:-1]))


def spawn(board, rng, cell, rank):
    empty = [index for index,value in enumerate(board) if value == 0]
    expected_cell = empty[int(rng.random()*len(empty))]
    expected_rank = 1 if rng.random()<.9 else 2
    require((cell,rank) == (expected_cell,expected_rank),
        'fresh seeded SOURCE initial and post-action cell/rank draws follow the actual p_four 0.1 world')
    board[cell] = rank


def check_terminal_update(row, status, steps, updates_before):
    require(row['terminal_update'] == (status == 'LOST') and row['analytic_terminal'] == (status == 'WON')
        and row['censored_last_update'] == (status == 'CUTOFF')
        and row['terminal_update_target'] == (-4. if status == 'LOST' else None),
        'LOST fits its final afterstate once; analytic WIN and CUTOFF final afterstates remain untrained')
    updates = steps-int(status != 'LOST')
    require(row['result']['updates_after'] == updates_before+updates,
        'SOURCE actual update count preserves winning and cutoff last-state exclusions')
    return updates


class SourceTrace:
    def __init__(self, parent):
        self.parent = parent
        self.games = self.updates = self.raw = 0
        self.environment = Counter(); self.learning = Counter(); self.outcomes = Counter()
        self.seconds = 0.

    def game(self, row):
        result,replay = row['result'],row
        require(row['life'] == self.parent and row['query'] == 'risk_goal' and row['method'] == 'TRAIN'
            and row['checkpoint'] is row['replica'] is None and row['episode_index'] == self.games
            and row['seed'] == source_seed(self.parent,self.games),
            'one fresh ordered risk_goal SOURCE training history with no old weights or evaluation rows')
        require(result['updates_before'] == self.updates and not result['planning_counts']
            and not result['setup_counts'] and result['setup_seconds'] == 0.,
            'SOURCE DIRECT training continues actual TD history without repeated model setup')
        actions,scores = replay['actions'],replay['scores']; steps = len(actions)
        require(1<=steps<=MAX_STEPS and steps == result['steps'] == len(scores)
            == len(replay['spawned_cells']) == len(replay['spawned_ranks'])
            == len(row['decision_updates_before']) == len(row['decision_values']) == len(row['previous_update_targets']),
            'every physical SOURCE action and its decision-before-update event is retained')
        board = [0]*16; rng = random.Random(row['seed'])
        require(len(replay['initial_spawns']) == 2, 'every fresh SOURCE game pays exactly two initial tile draws')
        for value in replay['initial_spawns']:
            spawn(board,rng,value['cell'],value['rank'])
        require(board == replay['initial_board'] and board_status(board) == 'ACTIVE',
            'SOURCE game starts at its actual fresh two-tile board')
        afterstates = []; legal = goals = 0
        for step,action in enumerate(actions):
            require(board_status(board) == 'ACTIVE', 'SOURCE never acts after a natural terminal board')
            require(row['decision_updates_before'][step] == self.updates+max(0,step-1),
                'SOURCE chooses the next action before updating the previous afterstate')
            choices = {candidate:swipe(board,candidate) for candidate in ACTIONS}
            legal += sum(after != board for after,score in choices.values())
            goals += sum(after != board and max(after)>=11 for after,score in choices.values())
            require(action in choices, 'SOURCE action is one of the four supported swipes')
            after,score = choices[action]
            require(after != board and score == scores[step], 'SOURCE recorded action is legal and its merge score is physically exact')
            target = row['previous_update_targets'][step]
            require(target is None if step == 0 else target == row['decision_values'][step],
                'only a preceding afterstate receives the current pre-update chosen action value as TD target')
            if max(after)>=11:
                require(row['decision_values'][step] == score/2048.+4.,
                    'a winning SOURCE choice uses the analytic goal continuation before updating its predecessor')
            afterstates.append(after)
            board = list(after); spawn(board,rng,replay['spawned_cells'][step],replay['spawned_ranks'][step])
        status = board_status(board)
        if status == 'ACTIVE':
            require(steps == MAX_STEPS, 'SOURCE cutoff occurs only at its registered training horizon')
            status = 'CUTOFF'
        require(status == result['status'] and board == replay['final_board'] and sum(scores) == result['score'],
            'SOURCE complete physical outcome score and final board remain actual')
        require(result['utility'] == sum(scores)/2048.+(4. if status == 'WON' else -4. if status == 'LOST' else 0.),
            'SOURCE game utility preserves its actual terminal bonus or censored endpoint')
        updates = check_terminal_update(row,status,steps,self.updates)
        trained = afterstates if status == 'LOST' else afterstates[:-1]
        environment = dict(initial_spawns=2, sampled_transitions=steps, environment_random_draws=2*(steps+2),
            ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+1,
            ground_status_internal_swipe_calls=4*(steps+1-int(status=='WON')),
            ground_swipe_calls=steps+4*(steps+1-int(status=='WON')))
        require(Counter(result['environment_counts']) == Counter(environment), 'every initial terminal and censored SOURCE transition is physically paid')
        predictions = legal-goals+updates
        learning = dict(choose_calls=steps, learned_swipe_calls=4*steps, line_table_lookups=16*steps,
            legal_swipes=legal, learned_terminal_checks=steps+legal, terminal_goal_bypasses=goals,
            value_predictions=predictions, table_lookups=32*predictions, td_updates=updates,
            table_updates=unique_update_writes(trained), table_update_occurrences=32*updates)
        require(Counter(result['learning_counts']) == Counter(learning),
            'SOURCE native DIRECT candidate reads and multiplicity-preserving TD parameter writes match the actual boards')
        self.environment.update(environment); self.learning.update(learning); self.outcomes[status] += 1
        self.raw += steps+2; self.updates += updates; self.games += 1; self.seconds += result['seconds']


def check_checkpoint(path, state, receipt, setup):
    with np.load(path, allow_pickle=False) as checkpoint:
        metadata = json.loads(str(checkpoint['metadata']))
        indices,values = checkpoint['indices'],checkpoint['values']
        require(metadata['schema'] == 'controlled_predictive_ntuple_td_v120' and metadata['radix'] == 11
            and metadata['patterns'] == [list(value) for value in BASE_PATTERNS],
            'fresh SOURCE final sparse checkpoint has the actual fixed V120 model')
        require(metadata['updates'] == receipt['updates'] == state.updates,
            'saved SOURCE model retains exactly the independently counted new TD updates')
        require(metadata['setup_counts'] == setup,
            'saved SOURCE model retains its actual new zero initialization and setup receipt')
        require(indices.ndim == values.ndim == 1 and len(indices) == len(values) == receipt['nonzero_weights']
            and np.all((0<=indices)&(indices<PARAMETERS)) and np.all(indices[1:]>indices[:-1])
            and np.all(values != 0.), 'fresh SOURCE sparse checkpoint stores its actual distinct nonzero parameters')
        saves = dict(checkpoint_saves=1, checkpoint_scanned_parameters=PARAMETERS,
            checkpoint_saved_parameters=len(indices))
        require(Counter(metadata['counts']) == state.learning+Counter(saves),
            'final sparse checkpoint includes all actual SOURCE training and one paid dense save scan')
        require(receipt['parameter_count'] == PARAMETERS and receipt['bytes'] == Path(path).stat().st_size,
            'SOURCE final checkpoint allocation and physical storage inventory')
        return saves


def check_source_compute(compute):
    require(compute['includes_source_setup_training_checkpoint_save'] is True,
        'fresh SOURCE compute includes setup training and final checkpoint save')
    expected = sum(compute[key] for key in ('worker_cpu_seconds','compiler_cpu_seconds','coordinator_cpu_seconds'))
    require(close(compute['full_source_cpu_seconds'],expected),
        'SOURCE worker compiler and coordinator CPU enter its full measured total exactly once')


def audit(directory):
    directory = Path(directory); document = json_file(directory/'source_summary.json')
    require(document['schema'] == 'acfqp.fresh_source.v312' and document['status'] == 'SOURCE_COMPLETE',
        'all four fresh SOURCE parents reach their registered terminal training boundary')
    run = json_file(directory/'run.json'); capsule = json_file(directory/'source_capsule.json')
    settings = document['settings']; equal_tree(settings,json_file(directory/'configuration.json'),'unchanged SOURCE training freeze')
    expected = dict(parents=list(range(4)), games_per_parent=GAMES, max_steps=MAX_STEPS, alpha=.0025,
        query=QUERY, p_four=.1, seed_base=31200000000,
        initialization='ZERO_NTUPLE_WEIGHTS', dynamics='FIXED_ORIGINAL_V120_CAPSULE_ONLY',
        workers=4, block_size=256, training_order='CHOOSE_NEXT_ACTION_BEFORE_PREVIOUS_AFTERSTATE_UPDATE',
        terminal_targets=dict(LOST=-4.,WON='ANALYTIC_LAST_UNTRAINED',CUTOFF='LAST_PENDING_UNTRAINED'),
        checkpoints=[GAMES], evaluations=0)
    for key,value in expected.items():
        require(settings[key] == value,'registered fresh SOURCE '+key)
    original = json_file(settings['dynamics_capsule'])
    require(capsule['snapshots'] == original['snapshots'] and capsule['inherited_costs'] == original['inherited_costs'],
        'the deterministic dynamics teacher alone is inherited unchanged')
    require(run['status'] == 'SOURCE_COMPLETE' and run['settings'] == settings
        and [row['life'] for row in run['lifecycles']] == list(range(4)),
        'SOURCE loader compatibility receipts close exactly the four fresh training histories')
    provenance = document['source_provenance']; require([p['parent'] for p in provenance['parents']] == list(range(4)),
        'four actual newly trained SOURCE parents')
    require(provenance['inherited_dynamics_costs'] == capsule['inherited_costs'],
        'fresh SOURCE provenance keeps the declared original deterministic dynamics costs')
    states = []; saves = []
    for parent in range(4):
        row = run['lifecycles'][parent]; source = provenance['parents'][parent]
        require(row['life'] == parent, 'SOURCE runner parent order')
        training = row['queries']['risk_goal']; setup = training['setup_counts']
        require(training['initial_updates'] == training['initial_nonzero_parameters'] == 0
            and setup['allocated_weight_parameters'] == PARAMETERS and setup['allocated_weight_bytes'] == 8*PARAMETERS
            and setup['zero_initialized_weight_parameters'] == PARAMETERS
            and not setup.get('checkpoint_loads',0), 'each fresh SOURCE allocates zero value tables without loading old weights')
        state = SourceTrace(parent); trace = directory/f'life_{parent}'/'risk_goal'/'training.jsonl.gz'
        require(training['training_trace_bytes'] == trace.stat().st_size, 'actual compact SOURCE trace physical byte inventory')
        with gzip.open(trace,'rt') as stream:
            for line in stream:
                state.game(json.loads(line))
        require(state.games == GAMES, 'exactly 4096 independently seeded SOURCE training games per parent')
        require(len(training['checkpoints']) == 1 and training['checkpoints'][0]['episodes'] == GAMES,
            'only the final SOURCE model checkpoint is retained')
        checkpoint = training['checkpoints'][0]
        path = (directory/checkpoint['model_file']).resolve()
        require(source['checkpoint'] == str(path) and source['updates'] == state.updates and source['source_query'] == QUERY
            and source['rule'] == capsule['snapshots'][parent]['rule'],
            'confirmation provenance names the actual new frozen SOURCE checkpoint and query')
        save = check_checkpoint(path,state,checkpoint,setup)
        require(Counter(checkpoint['save_counts']) == Counter(save)
            and Counter(training['source_operation_counts']) == state.learning+Counter(save)
            and training['final_updates'] == state.updates,
            'SOURCE compatibility runner closes training and final save operations exactly once')
        costs = source['inherited_training_costs']
        require(Counter(costs['environment_counts']) == state.environment
            and Counter(costs['learning_counts']) == state.learning and costs['training_games'] == GAMES
            and close(costs['training_seconds'],state.seconds) and costs['setup_counts'] == setup
            and Counter(costs['checkpoint_save_counts']) == Counter(save), 'every new SOURCE parent carries its actual complete training and save costs')
        states.append(state); saves.append(save)
    costs = document['accounting']['inherited_costs_per_arm']['SOURCE']
    environment = sum((state.environment for state in states),Counter())
    require(costs['source_training_raw_tiles'] == sum(state.raw for state in states)
        and costs['source_training_games'] == 4*GAMES and Counter(costs['source_training_environment_counts']) == environment
        and close(costs['source_training_seconds'],sum(state.seconds for state in states)),
        'fresh SOURCE economic receipts include all four actual full training histories')
    dynamics = original['inherited_costs']; counts = dynamics['source_environment']
    require(costs['dynamics_costs'] == dynamics
        and costs['dynamics_raw_tiles'] == counts.get('initial_spawns',0)+counts.get('sampled_transitions',0),
        'old dynamics raw inputs remain explicit separate inherited costs')
    compute = costs['fresh_source_compute']; check_source_compute(compute)
    worker = [row['fresh_source_compute'] for row in run['lifecycles']]
    require(close(compute['worker_cpu_seconds'],sum(row['worker_cpu_seconds'] for row in worker))
        and close(compute['compiler_cpu_seconds'],sum(row['compiler_cpu_seconds'] for row in worker)),
        'full SOURCE worker and compiler CPU reconcile all four actual parent receipts')
    return dict(status='PASS', independent_valid=True, source_parents=4, source_games=4*GAMES,
        source_training_raw_tiles=costs['source_training_raw_tiles'],
        source_updates={str(state.parent):state.updates for state in states},
        outcomes=dict(sum((state.outcomes for state in states),Counter())),
        fresh_source_compute=compute, zero_initialized_source_parameters=4*PARAMETERS,
        method='One independent compact-tape replay of all new SOURCE physics, seeded raw tile draws, '
            'decision-before-previous-update timing, actual TD targets and terminal/cutoff exclusions; '
            'candidate prediction work, exact repeated-address writes, final sparse checkpoints and measured full SOURCE costs.',
        limitations='Value parameters and action selection are not retrained or recomputed. The identified deterministic '
            'dynamics teacher is inherited, so this establishes new value-parent histories rather than a wholly new dynamics pipeline.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    directory = parser.parse_args().output
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False)); raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
