"""Recover V236-scope evidence at the end of the original paid lifecycle.

The V233 environment-side replay verifies every retained batch against its
original seed, interval, and increments. This module selects final same-type
pools from that replay; it neither draws an unpaid suffix nor exposes laws.
"""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

from scripts import retained_query_tapes_v233 as paid

ROOT, INPUT, SELECTION = paid.ROOT, paid.INPUT, paid.SELECTION
OPERATORS, ALPHABETS = paid.OPERATORS, paid.ALPHABETS
ENDPOINT_INDEX, B_SCOPE_END_INDEX = 77, 53


def key(row):
    return row['life'], row['index'], row['arm']


def pool_key(row):
    return row['life'], row['arm'], row['case']['context'], row['identity']


def reconstruct_data(source_records, evidence, rows, worlds, selection):
    """Extend only the evidence endpoint; retain original queries and policies.

    A pools already resume A at A_RETURN. B pools retain the frozen A_at_switch
    inheritance from V233, so they cannot include later A_RETURN outcomes.
    Capturing each pool's final target and the original selected members uses
    one replay of all paid batches, without storing every intermediate pool.
    """
    latest, final_indices, target_paid = {}, {}, Counter()
    for row in rows:
        latest[pool_key(row)] = row
        life_arm = row['life'], row['arm']
        final_indices[life_arm] = row['index']
        target_paid[life_arm] += row['spent']
    if any(index != ENDPOINT_INDEX for index in final_indices.values()):
        raise ValueError('life-end evidence requires each retained arm to end at index 77')
    descriptors = {key(row): row for row in selection}
    for row in latest.values():
        descriptors.setdefault(key(row), dict(life=row['life'], index=row['index'], arm=row['arm'],
            kind='endpoint_pool', phase='life_end'))
    replay = paid.reconstruct_data(source_records, evidence, rows, worlds, list(descriptors.values()))
    recovered = {key(row): row for row in replay['snapshots']}
    source_paid = Counter()
    for record in source_records:
        source_paid[record['life']] += record['draw_end']-record['draw_start']
    snapshots = []
    for descriptor in selection:
        original = recovered[key(descriptor)]
        endpoint = recovered[key(latest[pool_key(original)])]
        life_arm = original['life'], original['arm']
        snapshot = deepcopy(original)
        snapshot['early_fees'] = deepcopy(original['fees'])
        snapshot['operators'] = deepcopy(endpoint['operators'])
        snapshot['provenance'] = deepcopy(endpoint['provenance'])
        snapshot.update(endpoint_index=ENDPOINT_INDEX, certificate_index=ENDPOINT_INDEX,
            evidence_end_index=max(segment['index'] for segments in endpoint['provenance'].values()
                                   for segment in segments),
            evidence_scope_end_index=B_SCOPE_END_INDEX if original['case']['context'] == 'B' else ENDPOINT_INDEX,
            latest_pool_index=endpoint['index'])
        # Every target has already been paid by the endpoint. These references
        # repeat across selected queries and must not be added across tapes.
        snapshot['fees'] = dict(source_paid_samples=source_paid[original['life']],
            history_paid_samples=target_paid[life_arm], current_paid_samples=0,
            target_paid_samples=target_paid[life_arm],
            total_reference_paid_samples=source_paid[original['life']]+target_paid[life_arm],
            evidence_samples=sum(map(len, snapshot['operators'].values())))
        snapshots.append(snapshot)
    summary = dict(replay['summary'])
    summary.pop('queue_product_validity')
    summary.update(selected_snapshots=len(snapshots), endpoint_pool_snapshots=len(latest),
        reconstruction_snapshots=len(recovered), endpoint_index=ENDPOINT_INDEX,
        B_evidence_scope_end_index=B_SCOPE_END_INDEX,
        evidence_scope='V236_rows_at_original_life_end_with_B_A_at_switch_inheritance',
        row_fee_scope='full life/arm acquisition fee references are not additive',
        life_arm_paid_totals=[dict(life=life, arm=arm, source_paid_samples=source_paid[life],
            target_paid_samples=amount, total_paid_samples=source_paid[life]+amount)
            for (life, arm), amount in sorted(target_paid.items())])
    return dict(snapshots=snapshots, summary=summary)


def reconstruct(input_dir=INPUT, selection_path=SELECTION):
    input_dir, selection_path = Path(input_dir), Path(selection_path)
    worlds, source_paths = paid.frozen_worlds(input_dir)
    cases = json.loads((input_dir/'cases.json').read_text())
    if any(row['cases'] != worlds[row['life']][0] for row in cases):
        raise ValueError('frozen task cases differ from retained public roster')
    with gzip.open(selection_path, 'rt') as stream:
        selection = [json.loads(line) for line in stream]
    recovered = reconstruct_data(json.loads((input_dir/'source_records.json').read_text()),
        json.loads((input_dir/'source_evidence.json').read_text()),
        paid.read_rows(input_dir), worlds, selection)
    recovered['source_code_paths'] = source_paths+[
        'scripts/retained_query_tapes_v233.py', 'scripts/retained_life_end_tapes_v238.py']
    recovered['input_paths'] = [str(path.relative_to(ROOT)) for path in
        (input_dir/'source_records.json', input_dir/'source_evidence.json', input_dir/'cases.json',
         selection_path, *sorted(input_dir.glob('records_life_*.jsonl.gz')))]
    return recovered
