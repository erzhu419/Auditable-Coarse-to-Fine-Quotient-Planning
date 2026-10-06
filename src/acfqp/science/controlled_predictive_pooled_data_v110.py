"""Read the V105 experience bank once and construct complete-history holdouts."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

from acfqp.science.controlled_predictive_incremental_data_v107 import load_training


def _identity(record):
    return (record['source_life'], record['query'], record['episode'])


def _unique(records):
    identities = [_identity(record) for record in records]
    if len(identities) != len(set(identities)):
        raise ValueError('V110 source-life/query/episode identities must be unique')


def _summary(records):
    training = [record for record in records if record['episode'] % 5 != 4]
    heldout = [record for record in records if record['episode'] % 5 == 4]
    return dict(records=len(records), training_roots=len(training), heldout_roots=len(heldout),
        training_roster=[list(_identity(record)) for record in training],
        heldout_roster=[list(_identity(record)) for record in heldout])


def load_bank(source, allocations):
    """Tag actual first-batch membership without changing the original records."""
    started = perf_counter()
    bank, histories, counts = {}, [], Counter()
    for allocation in sorted(allocations, key=lambda item: item['life']):
        life = allocation['life']
        if life in bank:
            raise ValueError('V110 requires one allocation per source history')
        records, _, log = load_training(source, life, allocation)
        if not all(log['checks'].values()):
            raise ValueError('V110 source history checks failed')
        half_count = log['stage_rosters'][0]['records']
        tagged = deepcopy(records)
        for index, record in enumerate(tagged):
            record.update(source_life=life, is_half=index < half_count)
        _unique(tagged)
        bank[life] = tagged
        histories.append(log)
        counts.update(log['counts'])
    counts.update(histories_loaded=len(bank),
        half_records=sum(record['is_half'] for records in bank.values() for record in records))
    rosters = {str(life): dict(half=_summary([record for record in records if record['is_half']]),
        full=_summary(records)) for life, records in bank.items()}
    return bank, dict(histories=histories, rosters=rosters, counts=dict(counts),
        checks=dict(source_history_checks=True, unique_source_root_identities=True,
                    half_membership_from_original_batch=True), seconds=perf_counter() - started)


def pool_fold(bank, heldout_life):
    """Pool equal-weight source roots; retain source heldouts for diagnostics only."""
    started = perf_counter()
    if heldout_life not in bank:
        raise ValueError('V110 target history must belong to the experience bank')
    source_lives = [life for life in sorted(bank) if life != heldout_life]
    records = deepcopy([record for life in source_lives for record in bank[life]])
    if any(record['source_life'] != life for life in source_lives for record in bank[life]):
        raise ValueError('V110 record source history differs from its bank entry')
    _unique(records)
    half = [record for record in records if record['is_half']]
    return records, dict(source_lives=source_lives, heldout_life=heldout_life,
        half=_summary(half), full=_summary(records),
        checks=dict(target_history_excluded=True, unique_source_root_identities=True,
                    source_history_tags_bound=True, half_membership_preserved=True),
        seconds=perf_counter() - started)
