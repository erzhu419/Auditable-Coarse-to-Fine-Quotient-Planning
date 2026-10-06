"""Compare local and policy-semantic residual features on grouped heldout roots."""
import argparse
from collections import Counter
from copy import deepcopy
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_module_holdout_v155 as prior
from scripts import run_controlled_predictive_policy_modules_v151 as modules
from acfqp.science.controlled_predictive_module_semantics_v156 import (
    ResidualLMS,build_local_features,build_semantic_features)
from acfqp.science.controlled_predictive_policy_modules_v151 import utility

SOURCE=ROOT/'reports/controlled_predictive_module_holdout_v155'
LIVES,QUERIES,REPAIRS=prior.LIVES,prior.QUERIES,prior.REPAIRS
REPRESENTATIONS=('LOCAL','SEMANTIC')
EPOCHS,ALPHA=32,.1
read,save,build_folds=prior.read,prior.save,prior.build_folds
RootConsequences,load_teacher,leaf_state=modules.RootConsequences,modules.load_teacher,modules.leaf_state


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,repairs=list(REPAIRS),representations=list(REPRESENTATIONS),
        replicas=[0,4,8,12],folds=32,training_roots_per_fold=6,heldout_roots_per_fold=2,
        source='all64 audited V155 roots and V153 component means; unchanged OLD cp4 and frozen H2 teachers',
        feature_definition='specs/MODULE_SEMANTICS_V156.md; LOCAL V151 sparse41 occurrences; SEMANTIC fixed12 features',
        critic='both selected actions scored by the target-query teacher; other-query scalar values are not subtracted',
        local_target='three-component target minus cached frozen OLD components; zero residual initialization',
        epochs=32,alpha=.1,optimizer='normalized LMS with sum of squared feature values; frozen V153 root order',
        new_fits=128,new_updates=24576,updates_per_fit=192,old_predictions=64,residual_evaluation_predictions=1024,
        planned_root_queries=128,new_environment_samples=0,
        freeze='folds before feature preparation; feature package before fitting; all128 residual models before evaluation',
        primary='heldout SEMANTIC minus LOCAL own-target MSE and fixed-OLD-continuation local GATE gain',
        secondary='both representations against OLD; common GATE/H2 MSE, both source strata, histories, train diagnostics',
        weighting='equal roots within history then equal four histories; unchanged decisions retained',
        uncertainty='descriptive only; overlapping folds and previously inspected retained labels',
        accounting='all four views charge full retained2017530-transition pool; native planning and all residual work separate')


def extract_source(directory):
    source=read(SOURCE/'source_capsule.json');run=read(SOURCE/'run.json');analysis=read(SOURCE/'analysis.json')
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V155 audited completion is required')
    teacher_capsule=read(source['source_capsule_ref']);models=[]
    for item in source['models']:
        path=SOURCE/item['model_ref'];payload=read(path)
        if not payload['frozen'] or any(payload[k]!=v for k,v in item['frozen_state'].items()):
            raise ValueError('OLD differs from frozen source')
        target=directory/f'frozen_models/life_{item["life"]}/{item["query"]}/OLD.json'
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        models.append(dict(life=item['life'],query=item['query'],arm='OLD',source_model_ref=str(path),
            model_ref=str(target.relative_to(directory)),frozen_state=deepcopy(item['frozen_state']),model_bytes=target.stat().st_size))
    return dict(schema='acfqp.module_semantics.v156.source',source_run_ref=str(SOURCE/'run.json'),
        source_analysis_ref=str(SOURCE/'analysis.json'),source_capsule_ref=str(SOURCE/'source_capsule.json'),
        teacher_capsule_ref=source['source_capsule_ref'],snapshots=deepcopy(teacher_capsule['snapshots']),
        roots=deepcopy(source['roots']),examples=deepcopy(source['examples']),models=models,
        retained_training_cost=deepcopy(source['retained_training_cost']),
        cost_refs=deepcopy(source['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v155_runtime_tmp/{name}_checks.json'),fields=['attempts']) for name in ('runner','metrics','analyzer')])


def prepare_features(capsule,directory):
    started=perf_counter();rows=[];teachers=[];originals=[];feature_counts={r:Counter() for r in REPRESENTATIONS}
    backend=directory/'teacher_backend';backend.mkdir()
    for source in capsule['snapshots']:
        life=source['life'];bank={};parents={};leaves={};records={};old_models={}
        for query in QUERIES:
            parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,backend)
            parents[query],leaves[query],bank[query]=parent,leaf,teacher
            records[query]=dict(life=life,query=query,loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
            meta=next(m for m in capsule['models'] if (m['life'],m['query'])==(life,query))
            model=RootConsequences.from_payload(read(directory/meta['model_ref']));old_models[query]=model
            originals.append(dict(life=life,query=query,model_ref=meta['model_ref'],before=model.state(),
                setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
        for root in capsule['roots']:
            if root['life']!=life:continue
            choices={q:bank[q].choose(root['board'],QUERIES[q]) for q in QUERIES}
            local,local_work=build_local_features(root['board'])
            semantic,semantic_work=build_semantic_features(root['board'],choices,root['query'])
            model=old_models[root['query']];components=list(model.predict(root['board']));advantage=utility(components,root['query'])
            row=dict(root_id=root['root_id'],life=life,query=root['query'],choices=choices,
                old_prediction=dict(components=components,advantage=advantage,accept=advantage>0),
                features={'LOCAL':[[k,v] for k,v in sorted(local.items())],'SEMANTIC':[[k,v] for k,v in sorted(semantic.items())]},
                feature_counts={'LOCAL':local_work,'SEMANTIC':semantic_work})
            rows.append(row)
            for representation in REPRESENTATIONS:feature_counts[representation].update(row['feature_counts'][representation])
        for query in QUERIES:
            records[query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),
                total_counts=dict(bank[query].counts));teachers.append(records[query])
            record=next(m for m in originals if (m['life'],m['query'])==(life,query))
            record.update(after=old_models[query].state(),counts=dict(old_models[query].counts))
    return dict(rows=rows,teachers=teachers,old_models=originals,feature_counts={k:dict(v) for k,v in feature_counts.items()},
        old_predictions=sum(m['counts'].get('root_predictions',0) for m in originals),
        planned_root_queries=sum(t['total_counts'].get('choose_calls',0) for t in teachers),
        new_environment_samples=0,seconds=perf_counter()-started)


def fit_models(capsule,folds,feature_package,directory):
    examples={e['root_id']:e for e in capsule['examples']};features={r['root_id']:r for r in feature_package['rows']};models=[]
    for fold in folds:
        for representation in REPRESENTATIONS:
            for arm in REPAIRS:
                started=perf_counter();model=ResidualLMS(representation);before=model.state()
                for _ in range(EPOCHS):
                    for key in fold['train_ids']:
                        row=features[key];target=[a-b for a,b in zip(examples[key]['targets'][arm],row['old_prediction']['components'])]
                        model.update(dict(row['features'][representation]),target,ALPHA)
                model.freeze();state=model.state();fit_counts=dict(model.counts)
                target=directory/f'frozen_models/life_{fold["life"]}/{fold["query"]}/fold_{fold["replica"]}/{representation}_{arm}.json'
                target.parent.mkdir(parents=True,exist_ok=True);save(target,model.to_payload())
                models.append(dict(**{k:fold[k] for k in ('fold_id','life','query','replica')},representation=representation,arm=arm,
                    model_ref=str(target.relative_to(directory)),before=before,frozen_state=state,root_ids=list(fold['train_ids']),
                    new_updates=model.updates,fit_counts=fit_counts,total_counts=dict(model.counts),
                    model_bytes=target.stat().st_size,seconds=perf_counter()-started))
    return models


def evaluate(capsule,folds,feature_package,models,directory):
    started=perf_counter();rows=[];records=[];features={r['root_id']:r for r in feature_package['rows']}
    examples={e['root_id']:e for e in capsule['examples']};by_fold={f['fold_id']:f for f in folds}
    for meta in models:
        fold=by_fold[meta['fold_id']];model=ResidualLMS.from_payload(read(directory/meta['model_ref']));before=model.state()
        for root in capsule['roots']:
            if (root['life'],root['query'])!=(fold['life'],fold['query']):continue
            key=root['root_id'];feature=features[key];residual=list(model.predict(dict(feature['features'][meta['representation']])))
            components=[a+b for a,b in zip(feature['old_prediction']['components'],residual)];advantage=utility(components,root['query'])
            rows.append(dict(**{k:fold[k] for k in ('fold_id','life','query','replica')},arm=meta['arm'],representation=meta['representation'],
                root_id=key,source_method=root['source_method'],split='heldout' if key in fold['heldout_ids'] else 'train',
                old_prediction=deepcopy(feature['old_prediction']),residual_components=residual,
                prediction=dict(components=components,advantage=advantage,accept=advantage>0),targets=deepcopy(examples[key]['targets'])))
        records.append(dict(model_ref=meta['model_ref'],before=before,after=model.state(),counts=dict(model.counts)))
    return rows,dict(rows_ref='evaluation_rows.json',models=records,rows=len(rows),
        new_environment_samples=0,seconds=perf_counter()-started)


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_semantics_v156')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_SEMANTICS_V156.md',ROOT/'reports/v156_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_semantics_v156.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source(directory);folds=build_folds(capsule['roots']);save(directory/'source_capsule.json',capsule);snapshot_code(directory)
    data=dict(schema='acfqp.module_semantics.v156.run',status='frozen',settings=settings(),folds=folds,
        inherited_cost_refs=capsule['cost_refs'],features_ref='frozen_features.json',training=[],evaluation=None)
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    features=prepare_features(capsule,directory);save(directory/'frozen_features.json',features)
    data['training']=fit_models(capsule,folds,features,directory);save(directory/'frozen_training.json',deepcopy(data['training']))
    save(directory/'run.json',data)
    rows,data['evaluation']=evaluate(capsule,folds,features,data['training'],directory);save(directory/'evaluation_rows.json',rows)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(dict(status='complete',fits=len(data['training']),rows=len(rows),seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_semantics_v156')
    run(parser.parse_args().output)

