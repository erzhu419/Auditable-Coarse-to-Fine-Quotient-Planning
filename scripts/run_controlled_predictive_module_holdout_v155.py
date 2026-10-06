"""Episode-grouped holdout of fixed-reference module advantage repairs."""
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
from scripts import run_controlled_predictive_module_repair_v154 as prior
from acfqp.science.controlled_predictive_policy_modules_v151 import utility

SOURCE=ROOT/'reports/controlled_predictive_module_repair_v154'
LIVES,QUERIES=prior.LIVES,prior.QUERIES
REPAIRS=('REPAIR_H2','REPAIR_GATE')
REPLICAS=(0,4,8,12)
EPOCHS,ALPHA=32,.1
read,save,RootConsequences=prior.read,prior.save,prior.RootConsequences


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,repairs=list(REPAIRS),replicas=list(REPLICAS),
        source='audited V154 compact means of all64 V153 roots and unchanged OLD cp4 models',
        grouping='same history/query/replica: hold out both H2 and LEARN8 source roots together',
        folds=32,training_roots_per_fold=6,heldout_roots_per_fold=2,epochs=EPOCHS,alpha=ALPHA,
        initialization='each fold/arm independently loads the same OLD checkpoint; no old V151 label replay',
        training_order='V153 frozen root order with the two heldout roots removed',
        new_fits=64,new_updates=12288,updates_per_fit=192,frozen_models=72,
        targets={'REPAIR_H2':'mean components(M_H2-H_H2)','REPAIR_GATE':'mean components(M_GATE-H_GATE)'},
        gate='strict positive predicted utility; fixed OLD continuation for local decision evaluation',
        predictions=dict(old=64,repair=512,total=576),
        primary='heldout own-target MSE change and (new_accept-old_accept)*GATE target utility',
        secondary='common GATE target MSE; H2 target local gain; train diagnostics; all roots and both source strata',
        weighting='equal roots within each history, then equal four histories; include zero-disagreement roots',
        uncertainty='descriptive only; overlapping fold training sets are not independent repetitions',
        freeze='protocol and all32 folds before fitting; all64 repairs frozen before any evaluation predictions',
        new_environment_samples=0,native_planner_calls=0,
        accounting='reuse audited compact means; both arms charge the full retained2017530-transition pool, physical acquisition once')


def build_folds(roots):
    folds=[]
    for life in LIVES:
        for query in QUERIES:
            selected=[r for r in roots if r['life']==life and r['query']==query]
            if len(selected)!=8:raise ValueError('eight roots required per history/query')
            for replica in REPLICAS:
                held=[r for r in selected if r['replica']==replica]
                train=[r for r in selected if r['replica']!=replica]
                if len(held)!=2 or {r['source_method'] for r in held}!={'H2','LEARN8'} or len({r['source_seed'] for r in held})!=1:
                    raise ValueError('hold out the two same-seed source episodes together')
                folds.append(dict(fold_id=f'{life}:{query}:{replica}',life=life,query=query,replica=replica,
                    source_seed=held[0]['source_seed'],train_ids=[r['root_id'] for r in train],
                    heldout_ids=[r['root_id'] for r in held]))
    return folds


def extract_source(directory):
    source=read(SOURCE/'source_capsule.json');run=read(SOURCE/'run.json');analysis=read(SOURCE/'analysis.json')
    examples=read(SOURCE/run['training']['examples_ref'])
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V154 audited completion is required')
    models=[]
    for item in source['models']:
        path=SOURCE/item['model_ref'];payload=read(path)
        if prior.prior.prior.model_state(payload)!=item['frozen_state'] or not payload['frozen']:
            raise ValueError('OLD differs from its frozen reference')
        target=directory/f'frozen_models/life_{item["life"]}/{item["query"]}/OLD.json'
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        models.append(dict(life=item['life'],query=item['query'],arm='OLD',source_model_ref=str(path),
            model_ref=str(target.relative_to(directory)),frozen_state=deepcopy(item['frozen_state']),model_bytes=target.stat().st_size))
    if len(models)!=8 or [e['root_id'] for e in examples]!=[r['root_id'] for r in source['roots']]:
        raise ValueError('all eight originals and all64 compact labels are required')
    return dict(schema='acfqp.module_holdout.v155.source',source_run_ref=str(SOURCE/'run.json'),
        source_analysis_ref=str(SOURCE/'analysis.json'),source_capsule_ref=str(SOURCE/'source_capsule.json'),
        source_examples_ref=str(SOURCE/run['training']['examples_ref']),roots=deepcopy(source['roots']),
        examples=examples,models=models,retained_training_cost=deepcopy(run['training']['read_work']),
        cost_refs=deepcopy(run['inherited_cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v154_runtime_tmp/{name}_checks.json'),fields=['attempts']) for name in ('runner','metrics','analyzer')])


def fit_models(capsule,folds,directory):
    examples={e['root_id']:e for e in capsule['examples']}
    originals={(m['life'],m['query']):m for m in capsule['models']}
    result=[]
    for fold in folds:
        source=originals[fold['life'],fold['query']];payload=read(directory/source['model_ref'])
        selected=[examples[key] for key in fold['train_ids']]
        if len(selected)!=6 or set(fold['train_ids'])&set(fold['heldout_ids']):
            raise ValueError('a fit must use exactly six roots outside its heldout group')
        for arm in REPAIRS:
            started=perf_counter();model=RootConsequences.from_payload(payload);before=model.state();model.frozen=False
            for _ in range(EPOCHS):
                for example in selected:model.update(example['board'],example['targets'][arm],ALPHA)
            model.freeze();state=model.state();fit_counts=dict(model.counts)
            target=directory/f'frozen_models/life_{fold["life"]}/{fold["query"]}/fold_{fold["replica"]}/{arm}.json'
            target.parent.mkdir(parents=True,exist_ok=True);save(target,model.to_payload())
            result.append(dict(**{k:fold[k] for k in ('fold_id','life','query','replica')},arm=arm,
                source_model_ref=source['model_ref'],model_ref=str(target.relative_to(directory)),before=before,
                frozen_state=state,fit_counts=fit_counts,total_counts=dict(model.counts),
                setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds,
                root_ids=list(fold['train_ids']),new_updates=model.updates-before['updates'],
                model_bytes=target.stat().st_size,seconds=perf_counter()-started))
    return result


def prediction(model,board,query):
    components=list(model.predict(board));advantage=utility(components,query)
    return dict(components=components,advantage=advantage,accept=advantage>0.)


def evaluate(capsule,folds,models,directory):
    started=perf_counter();olds={};records=[];rows=[]
    for meta in capsule['models']:
        model=RootConsequences.from_payload(read(directory/meta['model_ref']));before=model.state()
        for root in capsule['roots']:
            if (root['life'],root['query'])==(meta['life'],meta['query']):
                olds[root['root_id']]=prediction(model,root['board'],root['query'])
        records.append(dict(model_ref=meta['model_ref'],before=before,after=model.state(),counts=dict(model.counts),
            setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
    examples={e['root_id']:e for e in capsule['examples']};by_fold={f['fold_id']:f for f in folds}
    for meta in models:
        fold=by_fold[meta['fold_id']];model=RootConsequences.from_payload(read(directory/meta['model_ref']));before=model.state()
        for root in capsule['roots']:
            if (root['life'],root['query'])!=(fold['life'],fold['query']):continue
            key=root['root_id']
            rows.append(dict(**{k:fold[k] for k in ('fold_id','life','query','replica')},arm=meta['arm'],
                root_id=key,source_method=root['source_method'],split='heldout' if key in fold['heldout_ids'] else 'train',
                old_prediction=olds[key],prediction=prediction(model,root['board'],root['query']),
                targets=deepcopy(examples[key]['targets'])))
        records.append(dict(model_ref=meta['model_ref'],before=before,after=model.state(),counts=dict(model.counts),
            setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
    return rows,dict(rows_ref='evaluation_rows.json',models=records,
        root_predictions=sum(m['counts'].get('root_predictions',0) for m in records),
        new_environment_samples=0,native_planner_calls=0,seconds=perf_counter()-started)


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_holdout_v155')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_HOLDOUT_V155.md',ROOT/'reports/v155_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    files.update((ROOT/'tests').glob('*module_holdout_v155.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source(directory);folds=build_folds(capsule['roots'])
    save(directory/'source_capsule.json',capsule);snapshot_code(directory)
    data=dict(schema='acfqp.module_holdout.v155.run',status='frozen',settings=settings(),folds=folds,
        inherited_cost_refs=capsule['cost_refs'],training=[],evaluation=None)
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    data['training']=fit_models(capsule,folds,directory)
    save(directory/'frozen_training.json',deepcopy(data['training']));save(directory/'run.json',data)
    rows,data['evaluation']=evaluate(capsule,folds,data['training'],directory)
    save(directory/'evaluation_rows.json',rows)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(dict(status='complete',fits=len(data['training']),rows=len(rows),seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_holdout_v155')
    run(parser.parse_args().output)

