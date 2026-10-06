"""Fixed complete-game replay selection under an exact supervised-state budget."""
from collections import deque
from time import process_time
import numpy as np

OLD = 'OLD_A1'
CURRENT = 'CURRENT_DATA'


def game_priority(count):
    queue = deque([(0, count)])
    while queue:
        first, end = queue.popleft()
        if first == end:
            continue
        middle = (first + end)//2
        yield middle
        queue.extend(((first, middle), (middle+1, end)))


def inventory(dataset, source):
    rows = []
    for game in range(dataset['fit_game_count']):
        first = int(dataset['ends'][game-1]) if game else 0
        end = int(dataset['ends'][game])
        eligible = np.flatnonzero(np.max(dataset['afterstates'][first:end], axis=1)<11)
        rows.append(dict(source=source, source_game=game, source_episode=dataset['games'][game]['episode'],
            source_start=first, source_end=end, terminal_code=int(dataset['terminal_codes'][game]),
            eligible_steps=len(eligible), eligible_local_steps=eligible))
    return rows


def choose_games(rows, quota):
    remaining = quota
    selected = []
    for index in game_priority(len(rows)):
        row = rows[index]
        count = min(remaining, row['eligible_steps'])
        if count:
            local = row['eligible_local_steps']
            partial = None
            if count < len(local):
                positions = ((2*np.arange(count, dtype=np.int64)+1)*len(local))//(2*count)
                partial = local[positions].tolist()
            selected.append(dict({key:value for key,value in row.items() if key!='eligible_local_steps'},
                selected_count=count, selected_local_steps=partial))
            remaining -= count
        if not remaining:
            break
    if remaining:
        raise ValueError('Retained FIT facts do not supply the frozen replay quota')
    return sorted(selected, key=lambda row:row['source_game'])


def _mask(records, datasets, total):
    mask = np.zeros(total, dtype=np.int32)
    for record in records:
        local = record['selected_local_steps']
        if local is None:
            data = datasets[record['source']]
            local = np.flatnonzero(np.max(data['afterstates'][record['source_start']:record['source_end']], axis=1)<11)
        mask[record['fit_start']+np.asarray(local, dtype=np.int64)] = 1
    return mask


def build_replay(old, current):
    started = process_time()
    datasets = {OLD:old, CURRENT:current}
    pools = {source:inventory(data, source) for source,data in datasets.items()}
    available = {source:sum(row['eligible_steps'] for row in rows) for source,rows in pools.items()}
    budget = available[CURRENT]
    quotas = {OLD:budget//2, CURRENT:budget-budget//2}
    if budget < 2 or available[OLD] < quotas[OLD]:
        raise ValueError('The supported retained histories must supply both replay quotas')

    new_records = []
    for row in pools[CURRENT]:
        new_records.append(dict({key:value for key,value in row.items() if key!='eligible_local_steps'},
            selected_count=row['eligible_steps'], selected_local_steps=None,
            fit_start=row['source_start'], fit_end=row['source_end']))
    new_mask = _mask(new_records, datasets, current['fit_step_end'])

    selected = {source:choose_games(pools[source], quota) for source,quota in quotas.items()}
    records = []
    for index in range(max(map(len, selected.values()))):
        for source in (OLD, CURRENT):
            if index < len(selected[source]):
                records.append(selected[source][index])
    boards, rewards, ends, codes = [], [], [], []
    offset = 0
    for record in records:
        data = datasets[record['source']]
        first, end = record['source_start'], record['source_end']
        boards.append(data['afterstates'][first:end]); rewards.append(data['rewards'][first:end])
        record.update(fit_start=offset, fit_end=offset+end-first)
        offset += end-first
        ends.append(offset); codes.append(record['terminal_code'])
    mixed = dict(afterstates=np.ascontiguousarray(np.concatenate(boards), dtype=np.int32),
        rewards=np.ascontiguousarray(np.concatenate(rewards), dtype=np.float64),
        ends=np.asarray(ends, dtype=np.int64), terminal_codes=np.asarray(codes, dtype=np.int32),
        fit_game_count=len(records), fit_step_end=offset)
    mixed_mask = _mask(records, datasets, offset)
    plans = {
        'NEW_ONLY':dict(budget_nonwinning_afterstates=budget, quotas={OLD:0, CURRENT:budget},
            candidate_game_count=current['fit_game_count'], fitted_full_steps=current['fit_step_end'], games=new_records),
        'MIXED_REPLAY':dict(budget_nonwinning_afterstates=budget, quotas=quotas,
            candidate_game_count=len(records), fitted_full_steps=offset, games=records)}
    if int(new_mask.sum())!=budget or int(mixed_mask.sum())!=budget:
        raise ValueError('Both replay interventions must process the same exact eligible-state budget')
    return dict(budget=budget, available=available, plans=plans,
        datasets={'NEW_ONLY':current, 'MIXED_REPLAY':mixed},
        masks={'NEW_ONLY':new_mask, 'MIXED_REPLAY':mixed_mask},
        counts=dict(candidate_fit_games=sum(data['fit_game_count'] for data in datasets.values()),
            candidate_fit_afterstates=sum(data['fit_step_end'] for data in datasets.values()),
            selected_training_afterstates_per_arm=budget, copied_replay_afterstate_cells=16*offset,
            copied_replay_reward_values=offset, copied_replay_game_boundaries=len(records),
            selection_mask_bytes=new_mask.nbytes+mixed_mask.nbytes), cpu_seconds=process_time()-started)
