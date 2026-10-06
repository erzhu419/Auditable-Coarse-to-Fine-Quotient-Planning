"""Stream retained FIRST facts and select chronological planner anchors."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

from .greedy_target_data_v317 import FixedPolicyData


BATCHES = {f'{task}_R{number}': (str(number), task)
    for number in (1, 2) for task in ('A', 'B')}


def _parent_inputs(document, parent):
    lives = [row for row in document['by_lifecycle'] if row['parent'] == parent]
    expected = list(range(parent, 16, 4))
    if parent not in range(4) or sorted(row['lifecycle'] for row in lives) != expected:
        raise ValueError('V319 requires all four retained lifecycles for each parent')
    receipts = [row for row in document['parent_receipts'] if row['parent'] == parent]
    if len(receipts) != 1:
        raise ValueError('V319 requires one retained trace per parent')
    return {row['lifecycle']: row for row in lives}, expected, Path(receipts[0]['trace_file'])


def _training(life_row, number, task):
    return life_row['rounds'][number][task]['collectors']['FIXED_FIRST']['acquisition']['training']


def _complete(datasets):
    return all(set(datasets[number]) == {'A', 'B'} for number in ('1', '2'))


def _receipt(counts, parent, life, path, compressed_bytes, cpu_seconds, datasets):
    data = [value for tasks in datasets.values() for value in tasks.values()]
    return dict(counts, parent=parent, lifecycle=life, trace_file=str(path),
        compressed_bytes_read=compressed_bytes, cpu_seconds=cpu_seconds,
        reconstruction_cpu_seconds=sum(value['costs']['processing_cpu_seconds'] for value in data),
        dataset_array_bytes=sum(array.nbytes for value in data for array in value.values()
            if isinstance(array, np.ndarray)))


def iter_query_lifecycles(document, parent):
    """Yield the original life row, four task-round datasets, and read costs.

    Only FIXED_FIRST A_R1/B_R1/A_R2/B_R2 TRAIN rows enter V317's factual
    reconstruction. All lines, including skipped initial and evaluation rows,
    enter the read ledger. One lifecycle is retained at a time; the last yield
    occurs after EOF. Reader CPU includes reconstruction and excludes caller
    work between yields. These are retained observations, not new raw samples.
    """
    cpu_started = process_time()
    lives, expected, path = _parent_inputs(document, parent)
    current, seen = None, []
    builders, datasets = {}, {'1': {}, '2': {}}
    counts = Counter(trace_files_read=1, new_raw_tiles=0)
    with path.open('rb') as compressed:
        compressed_start = compressed.tell()
        with gzip.GzipFile(fileobj=compressed, mode='rb') as stream:
            for line in stream:
                row = json.loads(line)
                life = row.get('lifecycle')
                if life is not None and life != current:
                    if current is not None:
                        if not _complete(datasets):
                            raise ValueError('Retained lifecycle lacks a complete task-round batch')
                        yield lives[current], datasets, _receipt(counts, parent, current, path,
                            compressed.tell()-compressed_start, process_time()-cpu_started, datasets)
                        cpu_started = process_time()
                        compressed_start = compressed.tell()
                        counts = Counter(new_raw_tiles=0)
                        builders, datasets = {}, {'1': {}, '2': {}}
                    if life not in lives or life != expected[len(seen)]:
                        raise ValueError('Retained parent trace changed lifecycle order or membership')
                    current = life; seen.append(life)
                counts['parsed_records'] += 1
                counts['parsed_bytes'] += len(line)
                counts['parsed_raw_tiles'] += len(row.get('raw_spawns', ()))
                if not (row['kind'] == 'TRAIN' and row.get('arm') == 'FIXED_FIRST'
                        and row.get('phase') in BATCHES):
                    continue
                number, task = BATCHES[row['phase']]
                if row['task'] != task or row['batch_id'] != row['phase'] or row['parent'] != parent:
                    raise ValueError('Retained task-round training tags changed')
                if task in datasets[number]:
                    raise ValueError('Retained task-round training continued past its paid budget')
                training = _training(lives[current], number, task)
                batch = row['phase']
                if batch not in builders:
                    if row['start'] != training['before_stream']:
                        raise ValueError('Retained task-round training is missing its initial chunk')
                    builders[batch] = FixedPolicyData(current, parent)
                builder = builders[batch]
                builder.consume(row)
                counts['selected_training_records'] += 1
                counts['selected_training_bytes'] += len(line)
                counts['reconstructed_raw_tiles'] += len(row['raw_spawns'])
                if builder.state['raw_tiles'] >= training['raw_tiles']:
                    dataset = builder.finish(training)
                    costs = dataset['costs']
                    costs['full_batch_raw_tiles'] = costs.pop('full_A_raw_tiles')
                    costs['full_batch_acquisition_counts'] = costs.pop('full_A_acquisition_counts')
                    dataset['batch_id'] = batch
                    datasets[number][task] = dataset
                    del builders[batch]
                    del builder, dataset
        if seen != expected or not _complete(datasets):
            raise ValueError('Retained parent trace lacks the planned task-round batches')
        yield lives[current], datasets, _receipt(counts, parent, current, path,
            compressed.tell()-compressed_start, process_time()-cpu_started, datasets)


def prepare_anchors(dataset, groups=16384):
    """Select 2*groups nonWIN FIT actions with a same-game predecessor board.

    The predecessor post-spawn board is the actual FIRST action's preboard.
    Every game's first action is excluded before any model query; HELDOUT and
    the paid unfinished tail cannot enter this position-only census.
    """
    started, cpu_started = perf_counter(), process_time()
    fit_end, fit_games = int(dataset['fit_step_end']), int(dataset['fit_game_count'])
    nonwinning = np.max(dataset['afterstates'][:fit_end], axis=1) < 11
    first = np.concatenate((np.array([0], dtype=np.int64), dataset['ends'][:fit_games-1]))
    excluded_first = int(np.count_nonzero(nonwinning[first]))
    eligible_mask = nonwinning.copy(); eligible_mask[first] = False
    eligible = np.flatnonzero(eligible_mask)
    requested = 2*groups
    if groups < 1 or len(eligible) < requested:
        raise ValueError('V319 insufficient eligible complete FIT anchors for the frozen census')
    positions = np.linspace(0, len(eligible)-1, requested, dtype=np.int64)
    indices = np.ascontiguousarray(eligible[positions], dtype=np.int64)
    preboards = np.ascontiguousarray(dataset['postspawn_boards'][indices-1], dtype=np.int32)
    roots = np.ascontiguousarray(dataset['afterstates'][indices], dtype=np.int32)
    counts = dict(fit_states=fit_end, fit_games=fit_games, eligible_anchors=len(eligible),
        selected_anchors=requested, requested_groups=groups,
        excluded_winning_fit_states=int(np.count_nonzero(~nonwinning)),
        excluded_game_first_nonwinning_states=excluded_first,
        index_array_bytes=int(indices.nbytes), preboard_array_bytes=int(preboards.nbytes),
        natural_root_array_bytes=int(roots.nbytes))
    return dict(indices=indices, preboards=preboards, natural_roots=roots, counts=counts,
        cpu_seconds=process_time()-cpu_started, seconds=perf_counter()-started)
