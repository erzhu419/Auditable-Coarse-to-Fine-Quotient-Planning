"""Supplemental observable equivalence after the retained V172 gauge failure."""
from copy import deepcopy
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from scripts import analyze_controlled_predictive_consequence_partition_v172 as audit


def first_difference(actual,expected,path='payload'):
    if audit._equal(actual,expected): return None
    if isinstance(expected,dict) and isinstance(actual,dict):
        for key,value in expected.items():
            difference = first_difference(actual.get(key),value,f'{path}.{key}')
            if difference is not None: return difference
    elif isinstance(expected,list) and isinstance(actual,list) and len(actual)==len(expected):
        for index,(left,right) in enumerate(zip(actual,expected)):
            difference = first_difference(left,right,f'{path}[{index}]')
            if difference is not None: return difference
    return dict(path=path,actual=actual,expected=expected)


def normalize_payload(payload):
    """Remove only the unidentifiable offset shared by a connected action group."""
    normalized,offsets = deepcopy(payload),{}
    for original,leaf in zip(payload['leaves'],normalized['leaves']):
        for component in original['connected_components']:
            offset = [math.fsum(original['coefficients'][action][k] for action in component)/len(component) for k in range(3)]
            for action in component:
                offsets[original['leaf_id'],action] = offset
                leaf['coefficients'][action] = [value-shift for value,shift in zip(original['coefficients'][action],offset)]
    return normalized,offsets


def normalize_choices(choices,offsets_by_model):
    normalized = deepcopy(choices)
    for row in normalized:
        if row['mode']=='H2': continue
        offsets = offsets_by_model[row['life'],row['mode']]; decision = row['decision']
        for action,vector in decision['predicted_components'].items():
            offset = offsets[decision['leaf'],action]
            decision['predicted_components'][action] = [value-shift for value,shift in zip(vector,offset)]
    return normalized


def reconcile(directory,audit_reference):
    started = perf_counter(); directory,audit_reference = Path(directory),Path(audit_reference)
    read = lambda name:json.loads((directory/name).read_text())
    reference = json.loads(audit_reference.read_text()); run,capsule,frozen = (read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    original_checks = reference['checks']; checks = []
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    replacement_names = {f'{life}:{mode}:independent_pair_fit_and_best_splits' for life in audit.LIVES for mode in audit.MODES}|{'frozen_validation_choices'}
    failed = {row['name'] for row in original_checks if not row['passed']}
    check('retained_audit_counts_and_narrow_failure_scope',reference['passed_checks']==sum(row['passed'] for row in original_checks) and
        reference['total_checks']==len(original_checks) and len({row['name'] for row in original_checks})==len(original_checks) and failed<=replacement_names)
    check('retained_complete_training_and_validation',run['status']=='complete' and reference['training_complete'] and reference['validation_complete'])
    inherited_inputs = json.loads(Path(capsule['inherited_frozen_inputs_ref']).read_text())
    inherited_outcomes = [row for ref in capsule['train_outcomes'] for row in json.loads(Path(ref['path']).read_text())]
    early = audit.assemble_examples(frozen['inherited_roots'],inherited_inputs['train_roster'],inherited_outcomes)
    training_roots,training_roster = read('training_roots.json'),read('training_roster.json')
    new_outcomes = [row for lifecycle in run['phases']['TRAIN']['lifecycles'] for row in read(lifecycle['outcomes_ref'])]
    late = audit.assemble_examples(training_roots,training_roster,new_outcomes)
    check('compact_labels_complete_without_raw_replay',early['complete'] and late['complete'])
    models,offsets,replacements,model_rows = {},{},{},[]
    first,maximum,original_gauge_failure = None,0.,False
    for manifest in read('frozen_models.json'):
        life,mode = manifest['life'],manifest['mode']; payload = read(manifest['model_ref'])['payload']
        expected = audit.independent_partition(early['examples'] if mode=='PART_EARLY' else early['examples']+late['examples'],life,mode)
        normalized,model_offsets = normalize_payload(payload); models[life,mode] = expected; offsets[life,mode] = model_offsets
        values = [abs(value) for vector in model_offsets.values() for value in vector]; gauge = max(values,default=0.)
        maximum = max(maximum,gauge); original_gauge_failure |= any(not audit._equal(value,0.) for value in values)
        difference = first_difference(payload,expected)
        if first is None and difference is not None: first = dict(model_ref=manifest['model_ref'],**difference)
        name = f'{life}:{mode}:independent_pair_fit_and_best_splits'; equivalent = audit._equal(normalized,expected)
        replacements[name] = equivalent; check(name,equivalent)
        model_rows.append(dict(life=life,mode=mode,model_ref=manifest['model_ref'],maximum_component_gauge_offset=gauge,
            original_coordinate_match=difference is None,observable_equivalence=equivalent,
            first_remaining_discrepancy=first_difference(normalized,expected)))
    roots = read('validation_roots.json')['roots']; expected_choices,_ = audit.choices_for(roots,models)
    actual_choices = read('frozen_choices.json'); normalized_choices = normalize_choices(actual_choices,offsets)
    replacements['frozen_validation_choices'] = audit._equal(normalized_choices,expected_choices)
    check('frozen_validation_choices',replacements['frozen_validation_choices'])
    combined = [dict(row,passed=replacements.get(row['name'],row['passed'])) for row in original_checks]
    equivalence = all(row['passed'] for row in checks) and all(row['passed'] for row in combined)
    result = dict(schema='acfqp.consequence_partition.v172.equivalence',observed_equivalence=equivalence,
        original_zero_sum_contract_failed=original_gauge_failure,original_analysis_overwritten=False,
        audit_reference=str(audit_reference.resolve()),retained_audit_passed_checks=reference['passed_checks'],retained_audit_total_checks=reference['total_checks'],
        combined_semantic_passed_checks=sum(row['passed'] for row in combined),combined_semantic_total_checks=len(combined),
        checks=checks,passed_checks=sum(row['passed'] for row in checks),total_checks=len(checks),models=model_rows,
        maximum_component_gauge_offset=maximum,first_discrepancy=first,
        frozen_choices=len(actual_choices),chosen_action_disagreements=sum(left['canonical_action']!=right['canonical_action'] for left,right in zip(actual_choices,expected_choices)),
        first_remaining_choice_discrepancy=first_difference(normalized_choices,expected_choices,'choices'),
        costs=dict(new_environment_samples=reference['costs']['new_environment_samples'],added_environment_samples=0,
            added_environment_random_draws=0,added_physical_trace_replays=0,rewritten_models=0,rewritten_choices=0,independent_models_rebuilt=len(models)),
        scope='retained physical checks plus original-tolerance observable contrasts; frozen zero-sum coordinate defect remains recorded',
        seconds=perf_counter()-started)
    (directory/'equivalence_analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_consequence_partition_v172')
    parser.add_argument('--audit-reference',type=Path,default=PROJECT/'reports/v172_runtime_tmp/audit.attempt_1.analysis.json')
    args = parser.parse_args(); result = reconcile(args.directory,args.audit_reference)
    print(json.dumps(dict(observed_equivalence=result['observed_equivalence'],original_zero_sum_contract_failed=result['original_zero_sum_contract_failed'],
        combined_passed=result['combined_semantic_passed_checks'],combined_checks=result['combined_semantic_total_checks'],added_environment_samples=0)))
    raise SystemExit(0 if result['observed_equivalence'] else 1)


if __name__=='__main__': main()
