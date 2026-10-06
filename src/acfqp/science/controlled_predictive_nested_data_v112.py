"""Two-history source pools and scoring confined to their excluded histories."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

from .controlled_predictive_capacity_ranking_v103 import CandidateModel
from .controlled_predictive_crossed_scoring_v106 import _event
from .controlled_predictive_pooled_data_v110 import _summary, _unique


def pool_pair(bank, source_lives):
    started = perf_counter()
    source_lives = sorted(source_lives)
    if (len(source_lives) != 2 or len(set(source_lives)) != 2
            or any(life not in bank for life in source_lives)):
        raise ValueError('V112 requires two distinct existing source histories')
    if any(record['source_life'] != life for life in source_lives for record in bank[life]):
        raise ValueError('V112 record source history differs from its bank entry')
    records = deepcopy([record for life in source_lives for record in bank[life]])
    _unique(records)
    if any(type(record['is_half']) is not bool for record in records):
        raise ValueError('V112 requires actual half-batch membership')
    half = [record for record in records if record['is_half']]
    return records, dict(pair_id='_'.join(map(str, source_lives)), source_lives=source_lives,
        validation_lives=[life for life in sorted(bank) if life not in source_lives],
        half=_summary(half), full=_summary(records),
        checks=dict(source_history_tags_bound=True, unique_source_root_identities=True,
            half_membership_preserved=True, validation_histories_excluded=True),
        seconds=perf_counter() - started)


def score_inner_models(models, roots):
    """Score the actual retained validation roots, preserving costs on binding failure."""
    started = perf_counter()
    decisions = []
    counts = Counter(model_payloads_loaded=0, model_root_scores=0,
        neural_candidate_predictions=0, neural_hidden_activations=0,
        new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, optimizer_steps=0, model_prefix_trajectories=0)
    lives = sorted({root['life'] for root in roots})
    model_keys = [(row['pair_id'], row['method']) for row in models]
    checks = dict(root_identity_unique=len(roots) == len({root['root_id'] for root in roots})
            == len({(root['life'], root['query'], root['episode']) for root in roots}),
        model_roster_unique=len(model_keys) == len(set(model_keys)), model_metadata_match=True,
        validation_roster_complete=True, only_validation_histories_scored=True,
        scoring_roster_complete=False)
    expected = {(row['pair_id'], row['method'], root['root_id']) for row in models for root in roots
        if root['life'] in row['metadata']['validation_lives']}

    def finish():
        return decisions, dict(counts=dict(counts), checks=checks,
            expected_model_root_scores=len(expected), seconds=perf_counter() - started)

    if not checks['root_identity_unique'] or not checks['model_roster_unique']:
        return finish()
    for row in models:
        metadata = row['metadata']
        sources, validation = metadata['source_lives'], metadata['validation_lives']
        checks['validation_roster_complete'] &= (len(sources) == len(set(sources)) == 2
            and sources == sorted(sources) and set(sources).issubset(lives)
            and validation == [life for life in lives if life not in sources]
            and len(validation) == 2)
        if not checks['validation_roster_complete']:
            return finish()
        payload = json.loads(Path(metadata['path']).read_text())
        counts['model_payloads_loaded'] += 1
        model = CandidateModel.from_payload(payload)
        update = payload['update']
        training, statistics = update['training_roster'], update['statistics_roster']
        expected_episodes = {query: sorted([[life, episode] for life, name, episode in training
            if name == query]) for query in ('reward', 'risk_goal')}
        stage, width = metadata['stage'], metadata['hidden']
        checks['model_metadata_match'] &= (stage in ('HALF', 'FULL') and width in (4, 16)
            and row['pair_id'] == '_'.join(map(str, sources)) == update['pair_id']
            and row['method'] == f'POOLED_H{width}_{stage}'
            and update['source_lives'] == sources and update['validation_lives'] == validation
            and update['stage'] == stage and model.hidden == payload['hidden'] == width
            and model.family == metadata['family'] == 'UNIFORM_SHRINK'
            and model.checkpoint == metadata['checkpoint'] == metadata['budget']
                == (256000 if stage == 'HALF' else 512000)
            and model.parameter_count == metadata['parameter_count'] == payload['parameter_count'] == 123 * width
            and update['optimizer_state'] == 'reset_zero_moments'
            and update['new_optimizer_steps'] == model.optimizer_steps == 1000
            and model.training_episodes == expected_episodes
            and len(training) == len({tuple(key) for key in training})
            and len(statistics) == len({tuple(key) for key in statistics})
            and {key[0] for key in training} == {key[0] for key in statistics} == set(sources)
            and all(query in ('reward', 'risk_goal') and episode % 5 != 4
                for _, query, episode in training + statistics)
            and set(map(tuple, statistics)).issubset(map(tuple, training))
            and (stage != 'HALF' or training == statistics))
        if not checks['model_metadata_match']:
            return finish()
        for root in roots:
            if root['life'] not in validation:
                continue
            checks['only_validation_histories_scored'] &= root['life'] not in sources
            event = _event(model.score_candidates(root['features'], counts))
            decisions.append(dict(pair_id=row['pair_id'], root_id=root['root_id'],
                validation_life=root['life'], method=row['method'], event=event))
            counts['model_root_scores'] += 1
    checks['scoring_roster_complete'] = (len(decisions) == len(expected)
        and {(row['pair_id'], row['method'], row['root_id']) for row in decisions} == expected)
    return finish()
