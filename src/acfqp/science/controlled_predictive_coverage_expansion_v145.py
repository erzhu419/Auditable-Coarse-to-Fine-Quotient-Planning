"""Fixed disagreement roots and paired H2-continuation training targets."""
from collections import Counter
from copy import deepcopy
import gzip
import json


LIVES, QUERIES, REPLICAS = range(4), ('risk1', 'risk8'), range(8)
ROOTS_PER_GAME, SUFFIXES, BASE = 4, 8, 145*100000000


def suffix_seed(life, query, replica, slot, suffix):
    return BASE+life*1000000+QUERIES.index(query)*100000+replica*10000+slot*100+suffix


def read_rows(path):
    with gzip.open(path, 'rt') as source:
        for line in source:
            yield json.loads(line)


def build_cohort(snapshots):
    """Choose four ordinal midpoint quantiles from each retained LEARNED game.

    Eligibility uses only candidate action disagreement and nonterminal
    afterstates. Predictions, chosen action, and eventual outcomes never rank
    or filter these roots. Boards are reconstructed from retained spawn arrays.
    """
    roots, games, reads = [], set(), Counter()
    for source in snapshots:
        for game in read_rows(source['advantage_control_trace']):
            reads['physical_game_records'] += 1
            if game['method'] != 'LEARNED':
                continue
            identity = (game['life'], game['query'], game['replica'])
            if game['life'] != source['life'] or identity in games:
                raise ValueError('source game identity differs')
            games.add(identity)
            reads['learned_games'] += 1
            reads['learned_decisions'] += len(game['choices'])
            eligible, board = [], list(game['initial_board'])
            for step, choice in enumerate(game['choices']):
                selection = choice['selection']
                candidate, baseline = selection['candidate_choice'], selection['baseline_choice']
                differing = selection['candidate_action'] != selection['baseline_action']
                nonterminal = max(candidate['afterstate']+baseline['afterstate']) < 11
                if differing and not selection['terminal_pair_bypass'] and nonterminal:
                    eligible.append(dict(life=game['life'], query=game['query'], replica=game['replica'],
                        seed=game['seed'], step=step, board=board.copy(),
                        previous_action=choice['previous_action'], simulation_seed=choice['simulation_seed'],
                        choices=dict(H2=selection['baseline_action'], H1_CONT=selection['candidate_action']),
                        candidate_after=deepcopy(candidate['afterstate']), baseline_after=deepcopy(baseline['afterstate']),
                        candidate_score=candidate['score'], baseline_score=baseline['score'],
                        immediate_difference=(candidate['score']-baseline['score'])/2048.))
                board = list(choice['afterstate'])
                board[game['spawned_cells'][step]] = game['spawned_ranks'][step]
            reads['eligible_decisions'] += len(eligible)
            if len(eligible) < ROOTS_PER_GAME:
                raise ValueError('source game lacks four eligible disagreement roots')
            for slot in range(ROOTS_PER_GAME):
                ordinal = ((2*slot+1)*len(eligible))//(2*ROOTS_PER_GAME)
                root = eligible[ordinal]
                root.update(root_id='v145:'+':'.join(map(str, (*identity, root['step']))),
                    slot=slot, source_ordinal=ordinal, source_game_roots=len(eligible),
                    actions=sorted(root['choices'].values()),
                    suffix_seeds=[suffix_seed(*identity, slot, suffix) for suffix in range(SUFFIXES)])
                roots.append(root)
    expected = {(life, query, replica) for life in LIVES for query in QUERIES for replica in REPLICAS}
    if games != expected or len(roots) != 256:
        raise ValueError('source LEARNED game roster is incomplete')
    roots.sort(key=lambda root: (root['life'], QUERIES.index(root['query']), root['replica'], root['slot']))
    return dict(schema='acfqp.coverage_expansion.v145.cohort', roots=roots, source_rows_read=dict(reads),
        physical_branches=len(roots)*SUFFIXES*2, paired_records=len(roots)*SUFFIXES)


def build_examples(cohort, traces):
    """Pair all eight retained suffixes; reject incomplete terminal supervision."""
    roots = {root['root_id']: root for root in cohort['roots']}
    grouped, reads = {key: [] for key in roots}, Counter()
    for row in traces:
        root = roots[row['root_id']]
        suffix = row['suffix']
        if (suffix not in range(SUFFIXES) or row['seed'] != root['suffix_seeds'][suffix]
                or row['continuation'] != 'H2' or sorted(row['branches']) != root['actions']):
            raise ValueError('paired source identity differs')
        for method, prefix in (('H1_CONT', 'candidate'), ('H2', 'baseline')):
            action = root['choices'][method]
            branch = row['branches'][action]
            if (branch['seed'] != row['seed'] or branch['root_board'] != root['board']
                    or branch['first_action'] != action or branch['first_afterstate'] != root[prefix+'_after']
                    or branch['scores'][0] != root[prefix+'_score']):
                raise ValueError('paired first-action branch differs')
            result = branch['result']
            if result['status'] not in ('WON', 'LOST'):
                raise ValueError('paired terminal supervision is incomplete')
            expected = [sum(branch['scores'])/2048., float(result['status'] == 'LOST'),
                        float(result['status'] == 'WON')]
            if result['components'] != expected:
                raise ValueError('paired terminal components differ')
        candidate = row['branches'][root['choices']['H1_CONT']]['result']['components']
        baseline = row['branches'][root['choices']['H2']]['result']['components']
        grouped[root['root_id']].append((suffix, [a-b for a, b in zip(candidate, baseline)]))
        reads.update(paired_records=1, physical_branches=2)
    examples = []
    for key, root in roots.items():
        rows = sorted(grouped[key])
        if [row[0] for row in rows] != list(range(SUFFIXES)):
            raise ValueError('paired suffix roster differs')
        total = [sum(row[1][i] for row in rows)/SUFFIXES for i in range(3)]
        examples.append(dict(root_id=key, life=root['life'], query=root['query'], replica=root['replica'],
            slot=root['slot'], step=root['step'], split='TRAIN' if root['replica'] < 4 else 'VALIDATION',
            origin='V145', candidate_action=root['choices']['H1_CONT'], baseline_action=root['choices']['H2'],
            **{key: deepcopy(root[key]) for key in ('candidate_after', 'baseline_after', 'immediate_difference')},
            target_total=total, target_tail=[total[0]-root['immediate_difference'], *total[1:]], suffixes=SUFFIXES))
    if len(examples) != 256 or reads != Counter(paired_records=2048, physical_branches=4096):
        raise ValueError('incomplete V145 supervision roster')
    examples.sort(key=lambda row: (row['life'], QUERIES.index(row['query']), row['replica'], row['slot']))
    return dict(schema='acfqp.coverage_expansion.v145.examples', examples=examples, source_rows_read=dict(reads))
