"""Decision-time candidate features and complete retained root utility labels."""
from collections import Counter
from itertools import groupby
import gzip
import json
from pathlib import Path
from time import perf_counter
import numpy as np

from acfqp.science.controlled_predictive_direct_value_v95 import _simulate_prefix
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility
from acfqp.science.controlled_predictive_joint_fragments_v84 import _array
from acfqp.science.controlled_predictive_paired_continuation_value_v92 import _pair_array
from acfqp.science.controlled_predictive_continuation_data_v91 import _key, _rows, _target

FEATURE_DIM = 121


def write_row(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')


def build_candidates(board, query, rule, seed, replicas=32):
    """Model prefixes depend only on the observed board, query and fresh streams."""
    start = perf_counter()
    raw, indexed = [], {}
    model, planning, feature, outcomes = (Counter() for _ in range(4))
    wiring = dict(spawn_uniforms_aligned=True, model_uniforms_aligned=True,
                  single_initiations=True, committed_lengths_match=True, terminal_absorbs=True)
    for replica in range(replicas):
        for option in OPTIONS:
            prefix = _simulate_prefix(board, query, option, replica, seed + replica, rule)
            raw.append(prefix)
            indexed[option, replica] = prefix
            model.update(prefix['model_work'])
            planning.update(prefix['planning_counts'])
            outcomes[prefix['status']] += 1
            n, control = prefix['steps_count'], prefix['controller']
            duration = 0 if option == 'H2' else int(option.split('_')[1])
            wiring['spawn_uniforms_aligned'] &= prefix['model_work']['spawn_uniform_draws'] == 2 * n
            wiring['model_uniforms_aligned'] &= prefix['planning_counts']['model_uniform_draws'] == 4 * n
            wiring['single_initiations'] &= len(control['events']) == 1 and control['initiation_step'] == 0
            wiring['committed_lengths_match'] &= (control['fragment_actions'] == min(duration, n)
                and prefix['action_paths'] == ['fragment'] * min(duration, n) + ['H2'] * (n - min(duration, n)))
            wiring['terminal_absorbs'] &= (all(s['status'] == 'ACTIVE' for s in prefix['steps'][:-1])
                and (prefix['status'] != 'ACTIVE' or n == 4))
    observed = _array([dict(board=board)], feature)[0]
    q = QUERIES[query]
    coefficients = [q['reward_weight'], -q['failure_penalty'], q['goal_bonus']]
    features, utilities = [], []
    for oi, option in enumerate(OPTIONS):
        pairs, deltas = [], []
        for replica in range(replicas):
            c, h = indexed[option, replica], indexed['H2', replica]
            pairs.append(dict(candidate_board=c['final_board'], reference_board=h['final_board'],
                candidate_active=c['status'] == 'ACTIVE', reference_active=h['status'] == 'ACTIVE'))
            deltas.append([a - b for a, b in zip(c['direct'], h['direct'])])
        pair = _pair_array(pairs, feature).mean(axis=0)
        direct = np.asarray(deltas).mean(axis=0)
        features.append(np.concatenate((observed, pair, direct, np.eye(5)[oi], coefficients)).tolist())
        utilities.append(float(np.dot(direct, coefficients)))
    feature['candidate_feature_vectors'] += 5
    return features, utilities, raw, dict(replicas=replicas, trajectories=len(raw),
        model_work=dict(model), planning_counts=dict(planning), feature_counts=dict(feature),
        outcomes=dict(outcomes), wiring=wiring, seconds=perf_counter() - start)


def load_batch(folder, output, rule, life):
    start = perf_counter()
    folder, output = Path(folder), Path(output)
    acq = json.loads((folder / 'construction.json').read_text())['acquisition']
    accepted = {_key(r): r for r in acq['completed_roots']}
    roster = {_key(r['root']): r for r in acq['root_records'] if r['branch_trajectories']}
    replicas = acq['replicas']
    expected = {(option, replica) for option in OPTIONS for replica in range(replicas)}
    counts, ground, planning, model_new, plan_new, feature_new, outcomes_new = (Counter() for _ in range(7))
    records, seen = [], set()
    with gzip.open(output / 'training_model_prefixes.jsonl.gz', 'wt') as retained:
        for key, stream in groupby(_rows(folder / 'branch_games.jsonl.gz'), key=lambda raw: _key(raw['root'])):
            if key in seen or key not in roster:
                raise ValueError('retained branch root is repeated or absent from its original roster')
            seen.add(key)
            raw = list(stream)
            index = {(r['option'], r['replica']): r for r in raw}
            for r in raw:
                ground.update(r['game']['work'])
                planning.update(r['planning_counts'])
                counts['trajectories_read'] += 1
                counts['steps_read'] += r['game']['work']['sampled_transitions']
            complete = (set(index) == expected and len(index) == len(raw)
                        and all(r['game']['status'] in ('WON', 'LOST') for r in raw))
            if complete != (key in accepted) or complete != roster[key]['complete_block']:
                raise ValueError('whole-root completeness differs from V98 acquisition')
            if not complete:
                counts['excluded_roots'] += 1
                continue
            root = accepted[key]
            seed = 210000000000 + life * 10000000 + root['episode'] * 1000 + tuple(QUERIES).index(root['query']) * 100
            features, direct, prefixes, log = build_candidates(root['board'], root['query'], rule, seed)
            for prefix in prefixes:
                write_row(retained, dict(root={k:root[k] for k in ('board','query','episode')}, **prefix))
            model_new.update(log['model_work'])
            plan_new.update(log['planning_counts'])
            feature_new.update(log['feature_counts'])
            outcomes_new.update(log['outcomes'])
            if not all(log['wiring'].values()):
                raise ValueError('candidate training prefixes violate execution semantics')
            targets = []
            for option in OPTIONS:
                deltas = []
                for replica in range(replicas):
                    c, h = index[option, replica]['game'], index['H2', replica]['game']
                    deltas.append([a - b for a, b in zip(_target(c['return_score'], c['status']), _target(h['return_score'], h['status']))])
                targets.append(np.mean(deltas, axis=0).tolist())
            records.append(dict(board=root['board'], query=root['query'], episode=root['episode'],
                features=features, utilities=[_utility(t, QUERIES[root['query']]) for t in targets],
                paired_rfs=targets, prefix_utilities=direct, prefix_seed=seed))
    if (seen != set(roster) or len(records) != len(accepted)
            or ground != Counter(acq['branches']['ground_work'])
            or planning != Counter(acq['branches']['planning_counts'])):
        raise ValueError('retained branch roster or costs differ from V98')
    with gzip.open(output / 'candidate_roots.jsonl.gz', 'wt') as handle:
        for record in records:
            write_row(handle, record)
    counts.update(complete_roots=len(records), training_roots=sum(r['episode'] % 5 != 4 for r in records),
        heldout_roots=sum(r['episode'] % 5 == 4 for r in records), new_environment_transitions=0, tree_fits=0)
    return records, dict(episode_cutoff=acq['episode_cutoff'], start_cursor=acq['start_cursor'],
        next_cursor=acq['next_cursor'], counts=dict(counts), inherited_acquisition=acq,
        new_model_work=dict(model_new), new_planning_counts=dict(plan_new), new_feature_counts=dict(feature_new),
        new_prefix_outcomes=dict(outcomes_new), model_prefix_trajectories=sum(outcomes_new.values()),
        model_prefix_roots=len(records), seconds=perf_counter() - start)


class CandidateSelector:
    def __init__(self, model, rule, seed, replicas=32):
        self.model, self.rule, self.seed, self.replicas = model, rule, seed, replicas
        self.checkpoint = model.checkpoint if model else None
        self.last_prefixes, self.last_log = [], None

    def select(self, board, query, allowed=None, work=None):
        start = perf_counter()
        x, direct, raw, log = build_candidates(board, query, self.rule, self.seed, self.replicas)
        counts = Counter()
        if self.model is None:
            scores, semantics = direct, 'prefix_utility'
            counts['prefix_only_decisions'] += 1
        else:
            scores = self.model.score_candidates(x, counts)
            semantics = 'rank_score' if self.model.family == 'PAIRWISE_RANK' else 'utility_estimate'
        allowed = OPTIONS if allowed is None else tuple(allowed)
        chosen, best = 'H2', 0.
        predictions = {}
        for option, value in zip(OPTIONS, scores):
            if option in allowed:
                predictions[option] = dict(value=float(value))
                if value > best:
                    chosen, best = option, value
        self.last_prefixes = raw
        self.last_log = dict(log, value_counts=dict(counts), seconds=perf_counter() - start)
        if work is not None:
            work['candidate_selector_decisions'] += 1
            work['candidate_trajectories'] += len(raw)
            for group in (log['model_work'], log['planning_counts'], log['feature_counts'], counts):
                for key, value in group.items():
                    work['candidate_' + key] += value
        return dict(option=chosen, predicted_advantage=None, value=float(best),
                    predictions=predictions, score_semantics=semantics)
