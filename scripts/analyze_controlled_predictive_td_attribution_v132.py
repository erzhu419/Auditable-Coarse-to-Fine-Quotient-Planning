"""Read retained update attribution without resampling or replaying model weights."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_online_query_td_v131 as previous
from acfqp.science.controlled_predictive_ntuple_td_v120 import PATTERNS
from acfqp.domains import standard_2048 as ground

LIVES, GROUPS = tuple(range(4)), ('FIRST', 'FEATURE')
CATEGORIES = ('LOSS', 'WIN_BOUNDARY', 'BOOTSTRAP')
MID, FINAL, REPLICAS = 131072, 524288, 16


def mean(values):
    values = list(values)
    return None if not values or any(value is None for value in values) else math.fsum(values)/len(values)


def strict_sign(value):
    return int(value > 0)-int(value < 0)


def gap_classification(mid, final, rounded_mid, rounded_final, feature_difference, base_gap):
    """Separate an actual parameter-dependent reversal from rounded action ties."""
    parameter_invariant = not any(coefficient for _, coefficient in feature_difference)
    return dict(parameter_invariant=parameter_invariant,
        parameter_invariant_tie=parameter_invariant and base_gap == 0.,
        canonical_mid_sign=strict_sign(mid), canonical_final_sign=strict_sign(final),
        canonical_strict_flip=mid < 0. and final > 0.,
        canonical_sign_reversal=strict_sign(mid)*strict_sign(final) == -1,
        canonical_endpoint_tie=mid == 0. or final == 0.,
        rounded_strict_flip=rounded_mid < 0. and rounded_final > 0.,
        rounded_endpoint_tie=rounded_mid == 0. or rounded_final == 0.,
        mid_sign_disagrees_with_rounding=strict_sign(mid) != strict_sign(rounded_mid),
        final_sign_disagrees_with_rounding=strict_sign(final) != strict_sign(rounded_final))


def category_totals(items):
    """Keep signed cancellation and exact/shared partitions; no responsibility ratios."""
    items = list(items)
    return {category: dict(net=math.fsum(r[category]['net'] for r in items),
        exact_board=math.fsum(r[category]['exact_board'] for r in items),
        shared_rest=math.fsum(r[category]['shared_rest'] for r in items))
        for category in CATEGORIES}


def retained_category_totals(rows, mid=MID, final=FINAL):
    """Count category membership from retained targets, without model evaluation."""
    categories = Counter({category: 0 for category in CATEGORIES})
    transitions, updates, segments = 0, 0, 0
    checks = dict(retained_segment_boundaries=True, retained_update_counts=True,
        retained_update_partition=True, retained_pending_continuity=True)
    previous, first, last, summaries = None, None, None, []
    for row in rows:
        end = row['cumulative_transitions']; start = end-len(row['actions'])
        if end <= mid:
            previous = row
            continue
        if start >= final: break
        checks['retained_segment_boundaries'] &= start >= mid and end <= final
        if first is None:
            first = row
            checks['retained_segment_boundaries'] &= start == mid
        elif last is not None:
            checks['retained_segment_boundaries'] &= start == last['cumulative_transitions']
        if previous is not None:
            checks['retained_update_counts'] &= row['updates_before'] == previous['updates_after']
            if previous['status'] == 'ACTIVE':
                checks['retained_pending_continuity'] &= (row['pending_before'] == previous['pending_after']
                    and row['start_board'] == previous['end_board'] and row['episode'] == previous['episode'])
            else:
                checks['retained_pending_continuity'] &= row['pending_before'] is None
        targets = row['td_targets']
        loss = int(row['terminal_update'] is not None)
        win_boundary = int(row['status'] == 'WON' and targets[-1] is not None)
        bootstrap = sum(target is not None for target in targets)-win_boundary
        count = loss+win_boundary+bootstrap
        checks['retained_update_partition'] &= loss == int(row['status'] == 'LOST') and bootstrap >= 0
        checks['retained_update_counts'] &= row['updates_after']-row['updates_before'] == count
        categories.update(dict(LOSS=loss, WIN_BOUNDARY=win_boundary, BOOTSTRAP=bootstrap))
        summaries.append(dict(episode=row['episode'], start_step=row.get('start_step'),
            end_step=row.get('end_step'), status=row['status'], cumulative_transitions=end,
            updates_before=row['updates_before'], updates_after=row['updates_after'],
            transitions=len(row['actions']), updates=count,
            category_counts=dict(LOSS=loss, WIN_BOUNDARY=win_boundary, BOOTSTRAP=bootstrap)))
        transitions += len(row['actions']); updates += count; segments += 1
        previous, last = row, row
    checks['retained_segment_boundaries'] &= (transitions == final-mid and last is not None
        and last['cumulative_transitions'] == final)
    return dict(transitions=transitions, updates=updates, segments=segments,
        updates_before=None if first is None else first['updates_before'],
        updates_after=None if last is None else last['updates_after'],
        categories=dict(categories), segment_summaries=summaries,
        checks={k: bool(v) for k, v in checks.items()})


def independent_features(board):
    if max(board) >= 11: return Counter()
    counts = Counter()
    for table, pattern in enumerate(PATTERNS):
        for reflected in (False, True):
            for rotations in range(4):
                address = 0
                for cell in pattern:
                    row, column = divmod(cell, 4)
                    if reflected: column = 3-column
                    for _ in range(rotations): row, column = column, 3-row
                    address = 11*address+board[4*row+column]
                counts[table*11**6+address] += 1
    return counts


def d4_equivalent(left, right):
    for reflected in (False, True):
        for rotations in range(4):
            transformed = [0]*16
            for cell, value in enumerate(left):
                row, column = divmod(cell, 4)
                if reflected: column = 3-column
                for _ in range(rotations): row, column = column, 3-row
                transformed[4*row+column] = value
            if transformed == right: return True
    return False


def probe_checks(probe, attribution, offset, work):
    features = probe['feature_difference']; old_action, new_action = probe['old_action'], probe['new_action']
    old, new = probe['old_afterstate'], probe['new_afterstate']
    before, after = independent_features(old), independent_features(new)
    expected = {i: after[i]-before[i] for i in sorted(set(before)|set(after)) if after[i] != before[i]}
    actual = {f['address']: f['coefficient'] for f in features}
    checks = dict(probe_features=actual == expected and len(actual) == len(features),
        probe_actions=True, canonical_gaps=True, attribution_arithmetic=True,
        overlap_counts=True)
    work['probe_feature_occurrences'] += sum(before.values())+sum(after.values())
    for stage in ('mid', 'final'):
        row = probe[stage]; values = row['action_values']
        chosen = min(values, key=lambda action: (-values[action]['value'], action))
        checks['probe_actions'] &= row['action'] == chosen == (old_action if stage == 'mid' else new_action)
        for action, value in values.items():
            board, score, changed = ground.swipe_board_v1(tuple(probe['board']), ground.Swipe2048Action(action))
            work['deterministic_probe_swipes'] += 1
            checks['probe_actions'] &= changed and list(board) == value['afterstate'] and score == value['score']
        checks['probe_actions'] &= values[old_action]['afterstate'] == old and values[new_action]['afterstate'] == new
        gap = math.fsum([probe['base_gap']]+[f['coefficient']*f[stage+'_weight'] for f in features])
        checks['canonical_gaps'] &= (row['canonical_gap'] == gap
            and row['rounded_gap'] == values[new_action]['value']-values[old_action]['value'])
    vals = probe['mid']['action_values']
    base_gap = math.fsum([(vals[new_action]['score']-vals[old_action]['score'])/2048.,
        (8. if max(new) >= 11 else offset)-(8. if max(old) >= 11 else offset)])
    classification = gap_classification(probe['mid']['canonical_gap'], probe['final']['canonical_gap'],
        probe['mid']['rounded_gap'], probe['final']['rounded_gap'], list(expected.items()), base_gap)
    classification['d4_equivalent'] = d4_equivalent(old, new)
    checks['canonical_gaps'] &= (probe['base_gap'] == base_gap
        and probe['exact_feature_tie'] == classification['parameter_invariant_tie']
        and probe['d4_equivalent'] == classification['d4_equivalent']
        and probe['strict_canonical_flip'] == classification['canonical_strict_flip'])
    net = attribution['categories']; exact = attribution['exact_board_categories']
    shared = attribution['shared_feature_categories']
    linear = math.fsum(f['coefficient']*(f['final_weight']-f['mid_weight']) for f in features)
    summed = math.fsum(net.values())
    tails0, tails1 = attribution['initial_tails'], attribution['final_tails']
    observed = (tails1[1]-tails1[0])-(tails0[1]-tails0[0])
    checks['attribution_arithmetic'] &= (set(net) == set(exact) == set(shared) == set(CATEGORIES)
        and all(shared[c] == net[c]-exact[c] for c in CATEGORIES)
        and attribution['nonzero_signed_addresses'] == len(expected)
        and attribution['linear_gap_change'] == linear and attribution['attributed_gap_change'] == summed
        and attribution['observed_gap_change'] == observed
        and attribution['rounding_residual'] == observed-summed
        and attribution['linear_rounding_residual'] == linear-summed
        and (bool(expected) or all(net[c] == exact[c] == shared[c] == 0. for c in CATEGORIES)))
    result = dict(probe, classification=classification,
        attribution={c: dict(net=net[c], exact_board=exact[c], shared_rest=shared[c]) for c in CATEGORIES},
        signed_overlap_update_counts=attribution['signed_overlap_update_counts'],
        linear_gap_change=linear, attributed_gap_change=summed,
        linear_rounding_residual=linear-summed, observed_rounding_residual=observed-summed,
        closure_residual=math.fsum([probe['final']['canonical_gap'], -probe['mid']['canonical_gap'], -summed]))
    return {k: bool(v) for k, v in checks.items()}, result


def group_summary(slots, probes, group):
    """Keep fixed episode slots even when boards alias or no diagnostic exists."""
    selected = [slot for slot in slots if slot['group'] == group]
    lifecycles = []
    for life in LIVES:
        life_slots = [slot for slot in selected if slot['life'] == life]
        available = [probes[slot['probe_id']] for slot in life_slots if slot['probe_id'] is not None]
        unique = {slot['probe_id'] for slot in life_slots if slot['probe_id'] is not None}
        events = Counter()
        for probe in available:
            for name, value in probe['classification'].items():
                if isinstance(value, bool): events[name] += value
        contributions = {category: {field: mean(probe['attribution'][category][field]
            for probe in available) for field in ('net', 'exact_board', 'shared_rest')}
            for category in CATEGORIES}
        lifecycles.append(dict(life=life, expected_slots=REPLICAS, slots=len(life_slots),
            available_slots=len(available), unique_probes=len(unique),
            unavailable_slots=len(life_slots)-len(available), alias_slots=len(available)-len(unique),
            unavailable_reasons=dict(Counter(slot.get('reason', 'no_actual_divergence' if group == 'FIRST'
                else 'no_feature_divergence') for slot in life_slots
                if slot['probe_id'] is None)), events=dict(events),
            event_fractions_of_fixed_slots={key: value/REPLICAS for key, value in events.items()},
            available_slot_means=dict(mid_gap=mean(p['mid']['canonical_gap'] for p in available),
                final_gap=mean(p['final']['canonical_gap'] for p in available),
                closure_residual=mean(p['closure_residual'] for p in available),
                contributions=contributions)))
    equal_life = dict(mid_gap=mean(r['available_slot_means']['mid_gap'] for r in lifecycles),
        final_gap=mean(r['available_slot_means']['final_gap'] for r in lifecycles),
        closure_residual=mean(r['available_slot_means']['closure_residual'] for r in lifecycles),
        contributions={category: {field: mean(r['available_slot_means']['contributions'][category][field]
            for r in lifecycles) for field in ('net', 'exact_board', 'shared_rest')}
            for category in CATEGORIES})
    complete = all(r['slots'] == REPLICAS for r in lifecycles)
    events = Counter()
    for row in lifecycles: events.update(row['events'])
    physical = [probes[key] for key in {s['probe_id'] for s in selected if s['probe_id'] is not None}]
    return dict(group=group, complete_roster=complete, expected_slots=len(LIVES)*REPLICAS,
        slots=len(selected), available_slots=sum(r['available_slots'] for r in lifecycles),
        unavailable_slots=sum(r['unavailable_slots'] for r in lifecycles),
        unique_probes=len({s['probe_id'] for s in selected if s['probe_id'] is not None}),
        events=dict(events), event_fractions_of_fixed_slots={key: value/(len(LIVES)*REPLICAS)
            for key, value in events.items()},
        maximum_absolute_residuals={name: max((abs(p.get(name, 0.)) for p in physical), default=None)
            for name in ('closure_residual', 'linear_rounding_residual', 'observed_rounding_residual')},
        lifecycles=lifecycles, equal_life_available_slot_means=equal_life,
        all_slots_available=complete and all(r['available_slots'] == REPLICAS for r in lifecycles),
        interpretation='Event frequencies retain all 16 episode slots per life. Numeric means condition on available slots within each life, then weight all four lives equally; an empty life leaves the pooled mean unavailable. Aliased slots retain their original episode weight.')


def source_board_at(row, index, work):
    board = tuple(row['initial_board'])
    for step in range(index):
        after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(row['actions'][step]))
        work['deterministic_prefix_swipes'] += 1
        cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        if not changed or score != row['scores'][step] or after[cell] != 0:
            raise ValueError('retained control prefix no longer agrees with deterministic swipe')
        after = list(after); after[cell] = rank; board = tuple(after)
    return list(board)


def slot_checks(case, probe, left, right, work):
    checks = dict(fixed_slot_source=case['seed'] == left['seed'] == right['seed']
        and case['mid_utility'] == left['result']['utility']
        and case['final_utility'] == right['result']['utility'],
        first_divergence=True, feature_selection=True, selected_board=True)
    if case['group'] == 'FIRST':
        first = next((i for i, (a, b) in enumerate(zip(left['actions'], right['actions'])) if a != b), None)
        shared = min(len(left['actions']), len(right['actions'])) if first is None else first
        checks['first_divergence'] &= (case['index'] == first and case['available'] == (first is not None)
            and left['initial_board'] == right['initial_board']
            and all(left[key][:shared] == right[key][:shared] for key in ('scores', 'spawned_cells', 'spawned_ranks'))
            and (first is not None or len(left['actions']) == len(right['actions'])))
        if probe is not None:
            checks['first_divergence'] &= (probe['old_action'] == left['actions'][first]
                and probe['new_action'] == right['actions'][first])
    else:
        trace = case['selection_trace']; candidates = trace['differing_candidates']
        indices = [item['index'] for item in candidates]
        eligible = [item for item in candidates if item['nonzero_features']]
        expected_index = eligible[0]['index'] if eligible else None
        checks['feature_selection'] &= (indices == sorted(set(indices))
            and all(0 <= item['index'] < trace['scanned_steps']
                and item['mid_action'] == left['actions'][item['index']]
                and item['mid_action'] != item['final_action'] for item in candidates)
            and case['index'] == expected_index and case['available'] == bool(eligible)
            and len(eligible) <= 1
            and trace['scanned_steps'] == (expected_index+1 if eligible else len(left['actions'])))
        if eligible:
            checks['feature_selection'] &= (candidates[-1] == eligible[0]
                and probe['old_action'] == eligible[0]['mid_action']
                and probe['new_action'] == eligible[0]['final_action'] and bool(probe['feature_difference']))
    if probe is not None:
        checks['selected_board'] &= (probe['life'] == case['life']
            and probe['board'] == source_board_at(left, case['index'], work))
    return {k: bool(v) for k, v in checks.items()}


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve(); io = Counter()
    def read(path):
        path = Path(path); io['files_read'] += 1; io['compressed_or_plain_bytes_read'] += path.stat().st_size
        return json.loads(path.read_text())
    def rows(path):
        path = Path(path); io['files_read'] += 1; io['compressed_or_plain_bytes_read'] += path.stat().st_size
        return previous.read_rows(path)
    run, capsule, roster = (read(directory/name) for name in ('run.json', 'source_capsule.json', 'roster.json'))
    sources = {source['life']: source for source in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES), ages=[MID, FINAL], groups=list(GROUPS), query='risk8',
        kind='PRIOR', replicas=REPLICAS, workers=4, alpha=.0025, slots=128,
        replay_transitions_per_life=FINAL-MID, new_environment_samples=0)
    probes = {probe['probe_id']: probe for probe in roster['probes']}; cases = roster['cases']
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[key]) == 4 and {r['life'] for r in run[key]} == set(LIVES)
            for key in ('panel_lifecycles', 'replay_lifecycles')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        fixed_slot_roster=len(cases) == 128 and {c['case_id'] for c in cases} == set(range(128))
            and all(c['case_id'] == GROUPS.index(c['group'])*64+c['life']*16+c['replica']
                and c['available'] == (c['probe_id'] is not None) for c in cases),
        probe_roster=len(probes) == len(roster['probes'])
            and len({(p['life'], tuple(p['board'])) for p in probes.values()}) == len(probes)
            and {c['probe_id'] for c in cases if c['available']} == set(probes),
        model_loads=True, exact_replay=True, independent_category_counts=True,
        retained_segment_summaries=True, replay_counters=True, source_checkpoint_roster=True,
        zero_new_samples=True, panel_roster=True)
    work = Counter(); normalized, replay_summaries = {}, []
    source_root = Path(sources[0]['training_trace']).parent.parent
    prior_run = read(source_root/'run.json'); prior_analysis = read(source_root/'analysis.json')
    checks['source_complete'] = prior_run['status'] == 'complete' and prior_analysis['complete'] is True
    training = {r['life']: r for r in prior_run['lifecycles']}
    controls = {r['life']: r for r in prior_run['eval_lifecycles']}
    panels = {r['life']: r for r in run['panel_lifecycles']}
    replay_counts, category_counts = Counter(), Counter()
    for replay in run['replay_lifecycles']:
        life = replay['life']; source = sources[life]
        learner = training[life]['queries']['risk8']['learners']['PRIOR']
        checkpoints = {str(c['age']): c for c in learner['checkpoints'] if c['age'] in (MID, FINAL)}
        checks['source_checkpoint_roster'] &= (source['training_trace'] == str(source_root/learner['training_trace'])
            and source['control_trace'] == str(source_root/controls[life]['control_trace'])
            and set(source['checkpoints']) == {str(MID), str(FINAL)}
            and all(source['checkpoints'][age] == dict(path=str(source_root/c['model_ref']),
                updates=c['updates'], stream_state=c['stream_state']) for age, c in checkpoints.items()))
        inspection = retained_category_totals(rows(source['training_trace']))
        for key, value in inspection['checks'].items(): checks[key] = checks.get(key, True) and value
        summaries = list(rows(directory/replay['trace']))
        expected = [dict(life=life, **r) for r in inspection.pop('segment_summaries')]
        checks['retained_segment_summaries'] &= summaries == expected
        checks['independent_category_counts'] &= (replay['category_counts'] == inspection['categories']
            and replay['initial_updates'] == inspection['updates_before'] == checkpoints[str(MID)]['updates']
            and replay['final_updates'] == inspection['updates_after'] == checkpoints[str(FINAL)]['updates'])
        counts = replay['counts']; n, updates = inspection['transitions'], inspection['updates']
        checks['exact_replay'] &= replay['checks'] == dict(exact_final_weights=True, exact_final_updates=True,
            exact_recorded_predictions=True, exact_recorded_targets_errors=True, exact_retained_transitions_pending=True)
        checks['replay_counters'] &= (replay['prefix_transitions_read'] == MID
            and replay['replayed_transitions'] == counts['replayed_transitions'] == n == FINAL-MID
            and replay['segments'] == inspection['segments'] == counts['retained_segments']
            and counts['greedy_action_checks'] == n and counts['chosen_value_checks'] == 2*n
            and counts['recorded_spawns'] == n and counts['replayed_updates'] == updates
            and counts['raw_target_checks'] == counts['td_error_checks'] == updates
            and counts['update_feature_occurrences'] == 32*updates
            and updates <= counts['unique_address_updates'] <= 32*updates
            and counts['final_compared_parameters'] == 4*11**6
            and replay['setup_counts']['private_parameters_copied'] == 4*11**6
            and replay['setup_counts']['private_weight_bytes_copied'] == 8*4*11**6)
        checks['zero_new_samples'] &= replay['newly_sampled_environment_transitions'] == replay['newly_sampled_model_transitions'] == 0
        for stage in (panels[life], replay):
            loads = stage['loads']['checkpoints']
            checks['model_loads'] &= (len(loads) == 2 and {r['age'] for r in loads} == {MID, FINAL}
                and all(r['counts']['checkpoint_loads'] == 1 for r in loads))
        attrs = {r['probe_id']: r for r in replay['probes']}
        checks['probe_roster'] &= set(attrs) == {k for k, p in probes.items() if p['life'] == life}
        for probe_id, attribution in attrs.items():
            checked, item = probe_checks(probes[probe_id], attribution,
                previous.expected_offset(source, 'risk8', 'PRIOR'), work)
            for key, value in checked.items(): checks[key] = checks.get(key, True) and value
            checks['overlap_counts'] &= (set(item['signed_overlap_update_counts']) == set(CATEGORIES)
                and all(0 <= item['signed_overlap_update_counts'][c] <= replay['category_counts'][c] for c in CATEGORIES))
            normalized[probe_id] = item
        retained_control = list(rows(source['control_trace']))
        indexed = {(r['checkpoint'], r['replica']): r for r in retained_control
            if r['query'] == 'risk8' and r['method'] == 'PRIOR' and r['checkpoint'] in (MID, FINAL)}
        checks['fixed_slot_source'] = checks.get('fixed_slot_source', True) and set(indexed) == {
            (age, replica) for age in (MID, FINAL) for replica in range(REPLICAS)}
        for case in (c for c in cases if c['life'] == life):
            checked = slot_checks(case, probes.get(case['probe_id']), indexed[MID, case['replica']],
                indexed[FINAL, case['replica']], work)
            for key, value in checked.items(): checks[key] = checks.get(key, True) and value
        panel = panels[life]
        checks['panel_roster'] &= len(panel['cases']) == 32 and len(panel['probes']) == len(attrs)
        replay_counts.update(counts); category_counts.update(replay['category_counts'])
        replay_summaries.append(dict(life=life, retained=inspection, category_stats=replay['category_stats'],
            category_counts=replay['category_counts'], counts=counts, seconds=replay['seconds']))
    checks['total_replay_budget'] = replay_counts['replayed_transitions'] == 1572864
    groups = {group: group_summary(cases, normalized, group) for group in GROUPS}
    checks['independent_fixed_groups'] = all(group['complete_roster'] for group in groups.values())
    return dict(schema='acfqp.td_attribution.v132.analysis', complete=run['status'] == 'complete' and all(checks.values()),
        checks={key: bool(value) for key, value in checks.items()}, groups=groups,
        probes=list(normalized.values()), replay_lifecycles=replay_summaries,
        costs=dict(replay_counts=dict(replay_counts), category_counts=dict(category_counts),
            new_environment_samples=0, new_model_samples=0, independent_read_counts=dict(io),
            independent_deterministic_work=dict(work)), inherited_costs=run['inherited_costs'],
        seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Offline attribution on retained updates. Exact replay checks come from the native replay; independent analysis rereads retained targets and control histories, verifies features, fixed selection and arithmetic, and does not replay weights or generate samples. Category contributions are signed net effects on the recorded trajectory; bootstrap updates also carry propagated terminal information.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'reports/controlled_predictive_td_attribution_v132')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'], checks=result['checks'])))
