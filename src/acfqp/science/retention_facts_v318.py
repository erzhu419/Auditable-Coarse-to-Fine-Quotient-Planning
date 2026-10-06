"""Read the retained V317 A facts once, without replaying other phases.

Each parent iterator retains only one lifecycle's two round datasets.  Its
incremental receipts charge parsing skipped rows as well as reconstructing A;
the reconstruction CPU is included in, rather than added to, reader CPU.
"""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import process_time

import numpy as np

from .greedy_target_data_v317 import FixedPolicyData


ROUNDS = {'A_R1': '1', 'A_R2': '2'}


def _parent_inputs(document, parent):
    lives = [row for row in document['by_lifecycle'] if row['parent'] == parent]
    expected = list(range(parent, 16, 4))
    if parent not in range(4) or sorted(row['lifecycle'] for row in lives) != expected:
        raise ValueError('V318 requires all four retained lifecycles for each parent')
    receipts = [row for row in document['parent_receipts'] if row['parent'] == parent]
    if len(receipts) != 1:
        raise ValueError('V318 requires one retained trace per parent')
    return {row['lifecycle']: row for row in lives}, expected, Path(receipts[0]['trace_file'])


def _training(life_row, round_number):
    return life_row['rounds'][round_number]['A']['collectors']['FIXED_FIRST']['acquisition']['training']


def _finished_round(builder, life_row, round_number):
    dataset = builder.finish(_training(life_row, round_number))
    costs = dataset['costs']
    costs['full_batch_raw_tiles'] = costs.pop('full_A_raw_tiles')
    costs['full_batch_acquisition_counts'] = costs.pop('full_A_acquisition_counts')
    dataset['batch_id'] = f'A_R{round_number}'
    return dataset


def iter_a_lifecycles(document, parent):
    """Yield ``(original_life_row, {'1': data, '2': data}, costs)``.

    Only A_R1/A_R2 FIXED_FIRST TRAIN rows enter V317's original physics reader.
    All JSON lines enter the parsing ledger.  Receipts partition the single
    parent read, and the final lifecycle is yielded after EOF to include its
    skipped B/evaluation tail.  CPU timers stop across yields so caller fitting
    and evaluation are not charged again here.  No new raw tiles are acquired.
    """
    cpu_started = process_time()
    lives, expected, path = _parent_inputs(document, parent)
    current = None
    seen = []
    builders, datasets = {}, {}
    counts = Counter(trace_files_read=1, new_raw_tiles=0)

    with path.open('rb') as compressed:
        compressed_start = compressed.tell()
        with gzip.GzipFile(fileobj=compressed, mode='rb') as stream:
            for line in stream:
                row = json.loads(line)
                life = row.get('lifecycle')
                if life is not None and life != current:
                    if current is not None:
                        if set(datasets) != {'1', '2'}:
                            raise ValueError('Retained A lifecycle lacks a complete round')
                        receipt = dict(counts, parent=parent, lifecycle=current,
                            trace_file=str(path), compressed_bytes_read=compressed.tell()-compressed_start,
                            cpu_seconds=process_time()-cpu_started,
                            reconstruction_cpu_seconds=sum(data['costs']['processing_cpu_seconds']
                                for data in datasets.values()),
                            dataset_array_bytes=sum(value.nbytes for data in datasets.values()
                                for value in data.values() if isinstance(value, np.ndarray)))
                        yield lives[current], datasets, receipt
                        cpu_started = process_time()
                        compressed_start = compressed.tell()
                        counts = Counter(new_raw_tiles=0)
                        builders, datasets = {}, {}
                    if life not in lives or life != expected[len(seen)]:
                        raise ValueError('Retained parent trace changed lifecycle order or membership')
                    current = life
                    seen.append(life)

                counts['parsed_records'] += 1
                counts['parsed_bytes'] += len(line)
                counts['parsed_raw_tiles'] += len(row.get('raw_spawns', ()))
                if not (row['kind'] == 'TRAIN' and row.get('task') == 'A'
                        and row.get('arm') == 'FIXED_FIRST' and row.get('phase') in ROUNDS):
                    continue
                round_number = ROUNDS[row['phase']]
                if row['batch_id'] != row['phase'] or row['parent'] != parent:
                    raise ValueError('Retained A training tags changed')
                if round_number in datasets:
                    raise ValueError('Retained A training continued past its paid budget')
                training = _training(lives[current], round_number)
                if round_number not in builders:
                    if row['start'] != training['before_stream']:
                        raise ValueError('Retained A training is missing its initial chunk')
                    builders[round_number] = FixedPolicyData(current, parent)
                builder = builders[round_number]
                builder.consume(row)
                counts['selected_training_records'] += 1
                counts['selected_training_bytes'] += len(line)
                counts['reconstructed_raw_tiles'] += len(row['raw_spawns'])
                if builder.state['raw_tiles'] >= training['raw_tiles']:
                    datasets[round_number] = _finished_round(builder, lives[current], round_number)
                    del builders[round_number]
                    del builder

        if seen != expected or set(datasets) != {'1', '2'}:
            raise ValueError('Retained parent trace lacks the planned A lifecycle rounds')
        receipt = dict(counts, parent=parent, lifecycle=current,
            trace_file=str(path), compressed_bytes_read=compressed.tell()-compressed_start,
            cpu_seconds=process_time()-cpu_started,
            reconstruction_cpu_seconds=sum(data['costs']['processing_cpu_seconds']
                for data in datasets.values()),
            dataset_array_bytes=sum(value.nbytes for data in datasets.values()
                for value in data.values() if isinstance(value, np.ndarray)))
        yield lives[current], datasets, receipt


def extract_a_rounds(document):
    """Stream all sixteen A lifecycles, one parent file at a time."""
    for parent in range(4):
        yield from iter_a_lifecycles(document, parent)


def sample_indices(dataset, split, n=64):
    """Evenly space probes over chronological complete nonWIN positions."""
    if split not in ('FIT', 'HELDOUT') or n < 1:
        raise ValueError('Probe sampling requires FIT or HELDOUT and a positive count')
    complete = int(dataset['ends'][-1])
    fit = int(dataset['fit_step_end'])
    start, stop = (0, fit) if split == 'FIT' else (fit, complete)
    eligible = np.flatnonzero(np.max(dataset['afterstates'][start:stop], axis=1) < 11) + start
    if len(eligible) <= n:
        return eligible.tolist()
    positions = np.linspace(0, len(eligible)-1, n, dtype=np.int64)
    return eligible[positions].tolist()
