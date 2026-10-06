"""Fresh-board confirmation of frozen SOURCE-trained exact H3 policies."""
from collections import Counter
import random
from time import perf_counter

from . import controlled_predictive_exact_h3_v177 as exact
from . import controlled_predictive_shared_consequences_v179 as shared
from . import controlled_predictive_rank_layout_consequences_v182 as layout
from .controlled_predictive_compositional_contract_v69 import build_model, model_payload, load_model
from .controlled_predictive_quotient_v1 import Query, plan

SCHEMA = 'acfqp.fresh_h3_confirmation.v184'
REPLICAS = 4
ROOTS_PER_REPLICA = 24
SEED_BASE = 1840200
MAX_STATES = 200000
MODEL_NAMES = ('RIDGE', 'LAYOUT', 'SHARED', 'ONE')
HORIZON = 3


def fresh_cases():
    """Use the original V69 H3 board geometry with new frozen seeds."""
    edges = [(4*r+c, 4*r+c+1) for r in range(4) for c in range(3)]
    edges += [(4*r+c, 4*(r+1)+c) for r in range(3) for c in range(4)]
    cases = []
    for replica in range(REPLICAS):
        for index in range(ROOTS_PER_REPLICA):
            seed = SEED_BASE+ROOTS_PER_REPLICA*replica+index
            rng = random.Random(seed)
            board = [rng.randint(1, 10) for _ in range(16)]
            left, right = edges[index % len(edges)]
            board[left] = board[right] = 1+index % 10
            for cell in rng.sample([i for i in range(16) if i not in (left, right)], index % 3):
                board[cell] = 0
            cases.append(dict(name=f'v184_h3_r{replica:02d}_{index:02d}', horizon=HORIZON,
                seed=seed, replica=replica, stratum=index, board=board, vacancies=index % 3))
    return cases


def observe_roots(cases):
    """Observe only current boards, legal actions and exact first rewards."""
    roots, counts = [], Counter()
    for ordinal, case in enumerate(cases):
        root = exact.root_from_case(case, ordinal, 'FRESH', counts)
        root.update(source_id=f"FRESH_REPLICA:{case['replica']:02d}",
                    replica=case['replica'], stratum=case['stratum'], seed=case['seed'])
        roots.append(root)
    return roots, dict(counts)


def freeze_choices(roots, models):
    """Annotate fresh roots with one shared cache before opening new labels."""
    choices = {mode: [] for mode in (*MODEL_NAMES, 'FALLBACK')}
    counts = Counter()
    for root in roots:
        root['layout_features'] = layout.action_features_from_root(root, counts)
        root['action_features'] = {action: list(record['aggregate'])
                                   for action, record in root['layout_features'].items()}
        counts.update(shared_feature_maps_derived=1,
                      shared_aggregate_cache_values_copied=6*len(root['action_features']))
        observable = {key: root[key] for key in ('root_id', 'source_id', 'life', 'canonical_board',
            'legal_actions', 'immediate_rewards', 'fallback_action', 'action_map', 'layout_features', 'action_features')}
        for mode in MODEL_NAMES:
            chooser = layout.choose_action if mode in ('RIDGE', 'LAYOUT') else shared.choose_action if mode == 'SHARED' else exact.choose_action
            decision = chooser(models[mode], observable)
            counts.update(decision['work']); counts.update(decision.get('feature_work', {}))
            counts['fresh_model_choices'] += 1
            choices[mode].append(dict(root_id=root['root_id'], mode=mode,
                canonical_action=decision['canonical_action'], actual_action=decision['actual_action'],
                fallback=decision['fallback'], decision=decision))
        action = root['fallback_action']
        counts['fresh_fallback_choices'] += 1
        choices['FALLBACK'].append(dict(root_id=root['root_id'], mode='FALLBACK',
            canonical_action=action, actual_action=root['action_map'][action], fallback=False,
            decision=dict(reason='observable_immediate_reward', work=dict(fresh_fallback_choices=1))))
    return choices, dict(counts)


def exact_labels(case, rule):
    """Build FULL once, freeze the native float-DP teacher, then evaluate exactly."""
    started = perf_counter()
    try:
        built = build_model(tuple(case['board']), HORIZON, rule, 'FULL', max_states=MAX_STATES)
    except Exception as error:
        error.operation = 'construction'
        if not hasattr(error, 'counts'):
            error.counts = {}
        if not hasattr(error, 'elapsed_seconds'):
            error.elapsed_seconds = perf_counter()-started
        raise
    tick = perf_counter()
    payload = model_payload(built)
    compiled, _ = load_model(payload)
    compilation_seconds = perf_counter()-tick
    tick = perf_counter()
    solution = plan(compiled, Query(reward_weight=1., failure_penalty=1., goal_bonus=1.))
    planning_seconds = perf_counter()-tick
    tick = perf_counter()
    evaluated = exact.evaluate_payload(payload, dict(policy=solution.policy), [0])
    label_seconds = perf_counter()-tick
    tick = perf_counter()
    teacher, export = [], Counter()
    for (horizon, board), state in sorted(built.encoding.items()):
        export['teacher_encoding_records_read'] += 1
        if built.model.terminal[state] != 'ACTIVE':
            continue
        teacher.append(dict(board=list(board), horizon=horizon, action=solution.policy[state]))
        export.update(teacher_policy_records=1, teacher_policy_action_reads=1, teacher_policy_tile_reads=16)
    export_seconds = perf_counter()-tick
    return dict(native=evaluated['labels'][0], teacher_policy=teacher,
        costs=dict(construction=dict(built.counts), planning=dict(solution.counts),
            label_evaluation=evaluated['counts'], teacher_export=dict(export),
            compilation=dict(model_payload_calls=1, model_reload_calls=1,
                payload_cells=len(payload['cells']), payload_rows=len(payload['rows']),
                payload_outcomes=sum(len(row[2]) for row in payload['rows'])),
            times=dict(construction=built.elapsed_seconds, compilation=compilation_seconds,
                planning=planning_seconds, label_evaluation=label_seconds,
                teacher_export=export_seconds, total=perf_counter()-started)))
