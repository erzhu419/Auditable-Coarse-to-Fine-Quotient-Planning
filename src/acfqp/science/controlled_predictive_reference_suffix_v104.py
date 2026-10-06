"""Execution audit for independent suffix references in the retained V103 stream."""
from collections import Counter
from .controlled_predictive_fragments_v83 import OPTIONS, QUERIES


def audit_reference(root, raw, log, replicas=32, life_base=103000):
    """Check sampler wiring and all recorded cost; CUTOFF is a valid recorded outcome."""
    roster = {(row['option'], row['replica']) for row in raw}
    checks = dict(trajectory_roster_complete=len(raw) == len(roster) == replicas * len(OPTIONS)
        and roster == {(option, replica) for option in OPTIONS for replica in range(replicas)},
        root_boards_match=True, paired_fresh_streams=True, committed_fragments_match=True,
        executed_costs_match=True, censored_status_matches=True)
    ground, planning, outcomes = Counter(), Counter(), Counter()
    for row in raw:
        game, controller = row['game'], row['controller']
        steps, option = game['steps_count'], row['option']
        seed = (8310000000 + (life_base + root['life']) * 10000000
            + tuple(QUERIES).index(root['query']) * 100000 + root['episode'] * 100 + row['replica'])
        checks['root_boards_match'] &= game['initial_board'] == root['board']
        checks['paired_fresh_streams'] &= (row['env_seed'] == game['seed'] == seed
            and row['model_seed'] == seed + 1000000000000
            and game['work'].get('environment_random_draws', 0) == 2 * steps
            and row['planning_counts'].get('model_uniform_draws', 0) == 4 * steps)
        duration = 0 if option == 'H2' else int(option.split('_')[1])
        checks['committed_fragments_match'] &= (controller['initiation_step'] == 0
            and controller['selected_option'] == option and len(controller['events']) == 1
            and controller['fragment_actions'] == min(duration, steps))
        ground.update(game['work']); planning.update(row['planning_counts']); outcomes[game['status']] += 1
    checks['executed_costs_match'] &= (ground == Counter(log['ground_work'])
        and planning == Counter(log['planning_counts']) and outcomes == Counter(log['outcomes'])
        and log['trajectories'] == len(raw))
    checks['censored_status_matches'] = bool(outcomes['CUTOFF']) == log['censored_root']
    return checks
