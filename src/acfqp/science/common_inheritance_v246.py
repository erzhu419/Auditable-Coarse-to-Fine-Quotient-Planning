"""Replay the paid ONE_WAY A+B prefix without carrying decisions or truth.

The common state stops before V245's first A_RETURN observation. Each new arm
gets its own replayed state, native banks and cost ledger. Only recorded batch
increments and the public equality interface enter the replay.
"""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

from . import bidirectional_pool_v243 as core

PREFIX_TARGETS = tuple(range(3, 27))+tuple(range(30, 54))


def load_prefix(directory, life):
    """Read a compact observation-only prefix from the retained V245 files."""
    directory = Path(directory)
    sources = [dict(context=row['context'], slot=row['slot'], operator=row['operator'],
                    increments=deepcopy(row['increments']), source_position=position)
               for position, row in enumerate(json.loads((directory/'source_records.json').read_text()))
               if row['life'] == life]
    interface = next(row for row in json.loads((directory/'interfaces.json').read_text())
                     if row['life'] == life)['metadata']
    targets = []
    record_file = f'records_life_{life:02d}.jsonl.gz'
    with gzip.open(directory/record_file, 'rt') as stream:
        for position, line in enumerate(stream):
            row = json.loads(line)
            if row['arm'] != 'ONE_WAY':
                continue
            if row['index'] >= 54:
                break
            targets.append(dict(index=row['index'], identity=row['identity'],
                case=deepcopy(row['case']), record_position=position,
                batches=[dict(operator=batch['operator'], increments=deepcopy(batch['increments']))
                         for batch in row['batches']]))
            if len(targets) == len(PREFIX_TARGETS):
                break
    if tuple(row['index'] for row in targets) != PREFIX_TARGETS:
        raise ValueError('the complete frozen ONE_WAY A+B prefix is required')
    return dict(life=life, sources=sources, targets=targets,
        changed_operator=interface['changed_operator'], b_to_a=tuple(interface['b_to_a']),
        reference=dict(directory=str(directory), source_records='source_records.json',
            target_records=record_file, arm='ONE_WAY', stages=['A', 'B'],
            first_target=3, last_target=53, targets=len(targets)))


def replay_prefix(prefix, work=None):
    """Return one independent ONE_WAY state and its fully charged cost ledger."""
    if work is None:
        work = Counter()
    anchors = {context: [core.empty() for _ in range(3)] for context in ('A', 'B')}
    source_paid = dict.fromkeys(('A', 'B'), 0)
    for row in prefix['sources']:
        context, operator = row['context'], row['operator']
        anchor = anchors[context][row['slot']-(3 if context == 'B' else 0)][operator]
        for category, count in row['increments'].items():
            anchor[category] += count
            source_paid[context] += count
    state = core.prepare(anchors['A'], prefix['life'], 'ONE_WAY', work)
    target_paid, batch_counts = dict.fromkeys(('A', 'B'), 0), dict.fromkeys(('A', 'B'), 0)
    for row in prefix['targets']:
        if row['index'] == 30:
            core.begin_b(state, anchors['B'], prefix['changed_operator'], prefix['b_to_a'], work)
        context = row['case']['context']
        for batch in row['batches']:
            core.observe(state, row['case'], row['identity'], batch['operator'], batch['increments'])
            target_paid[context] += sum(batch['increments'].values())
            batch_counts[context] += 1
    ledger = dict(life=prefix['life'], reference=deepcopy(prefix['reference']),
        source_samples_by_context=source_paid, target_samples_by_context=target_paid,
        target_batches_by_context=batch_counts, source_paid_samples=sum(source_paid.values()),
        history_paid_samples=sum(target_paid.values()), new_observations=0,
        retained_decisions_imported=0, return_observations_imported=0,
        another_arm_observations_imported=0)
    ledger['total_prefix_paid_samples'] = ledger['source_paid_samples']+ledger['history_paid_samples']
    return state, ledger
