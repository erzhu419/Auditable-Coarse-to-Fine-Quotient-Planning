"""Reuse the retained incremental V102 candidate records for a capacity comparison."""
import gzip
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_candidate_data_v100 import FEATURE_DIM, write_row
from acfqp.science.controlled_predictive_continuation_data_v91 import _key, _rows
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS


INHERITED_FIELDS = ('replicas', 'episode_cutoff', 'start_cursor', 'next_cursor',
    'inherited_acquisition', 'inherited_ground_work', 'inherited_planning_counts',
    'inherited_feature_prefixes')


def load_batch(v102_stage_folder, output):
    """Copy complete roots in their saved order without rereading branch trajectories."""
    start = perf_counter()
    folder, output = Path(v102_stage_folder), Path(output)
    stage = json.loads((folder / 'construction.json').read_text())
    source = stage['data']
    acquisition = source['inherited_acquisition']
    if (stage['episode_cutoff'] != source['episode_cutoff']
            or any(source[field] != acquisition[field]
                   for field in ('replicas', 'episode_cutoff', 'start_cursor', 'next_cursor'))):
        raise ValueError('V102 candidate stage differs from its inherited acquisition interval')
    records = list(_rows(folder / 'candidate_roots.jsonl.gz'))
    if ([_key(record) for record in records] != [_key(root) for root in acquisition['completed_roots']]
            or len(records) != source['counts']['complete_roots']):
        raise ValueError('V102 candidate records differ from the complete ordered stage roster')
    largest_difference = 0.0
    for record in records:
        labels, utilities = np.asarray(record['replica_utilities']), np.asarray(record['utilities'])
        if (np.asarray(record['features']).shape != (len(OPTIONS), FEATURE_DIM)
                or labels.shape != (source['replicas'], len(OPTIONS))
                or utilities.shape != (len(OPTIONS),)):
            raise ValueError('retained V102 candidate feature or replica label dimensions differ')
        difference = float(np.max(np.abs(labels.mean(axis=0) - utilities)))
        if (not np.all(labels[:, 0] == 0)
                or not np.allclose(labels.mean(axis=0), utilities, rtol=0, atol=1e-12)):
            raise ValueError('retained V102 replica labels disagree with paired terminal means')
        largest_difference = max(largest_difference, difference)
    with gzip.open(output / 'candidate_roots.jsonl.gz', 'wt') as handle:
        for record in records:
            write_row(handle, record)
    counts = dict(roots_read=len(records),
        training_roots=sum(record['episode'] % 5 != 4 for record in records),
        heldout_roots=sum(record['episode'] % 5 == 4 for record in records),
        mean_roots_verified=len(records), new_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0, neural_candidate_predictions=0,
        model_prefix_trajectories=0)
    return records, dict({field: source[field] for field in INHERITED_FIELDS},
        counts=counts, inherited_v102_data_counts=source['counts'],
        max_mean_utility_difference=largest_difference, seconds=perf_counter() - start)
