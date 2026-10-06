"""Cross the frozen V105 ranking models on common retained candidate inputs."""
import argparse
import importlib
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_crossed_data_v106 import load_cohort
from acfqp.science.controlled_predictive_crossed_scoring_v106 import score_models

SOURCE = ROOT / 'reports/controlled_predictive_fresh_ranking_v105'


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_crossed_ranking_v106')
    paths = {Path(__file__).resolve(), ROOT / 'specs/CROSSED_RANKING_V106.md'}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / 'src') or path.is_relative_to(ROOT / 'scripts'):
                paths.add(path)
    for source in paths:
        target = directory / 'source' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def run(directory):
    started = perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot(directory)
    source = json.loads((SOURCE / 'run.json').read_text())
    analysis = json.loads((SOURCE / 'analysis.json').read_text())
    if source['status'] != 'complete' or not analysis['primary_complete']:
        raise ValueError('crossed evaluation requires the completed full V105 reference cohort')
    settings = dict(source['settings'], training_lifecycles=source['settings']['lifecycles'],
        crossed_model_count=16, new_environment_transitions=0, new_model_prefix_transitions=0,
        new_neural_model_fits=0)
    report = dict(schema='acfqp.crossed_ranking.v106', status='running', source=str(SOURCE),
        platform=platform.platform(), executable=sys.executable, python=sys.version, settings=settings,
        inherited_v105_work=analysis['actual_executed_work'], cohort=None, models=[], decisions=[], scoring_log=None)
    save(directory / 'run.json', report)
    roots, log = load_cohort(SOURCE, directory, source)
    report['cohort'] = dict(roots=roots, log=log)
    report['actual_wall_seconds'] = perf_counter() - started
    save(directory / 'run.json', report)
    if not all(log['checks'].values()):
        raise ValueError('retained candidate input recovery failed: ' + str(log['checks']))
    print(json.dumps(dict(phase='cohort_recovered', roots=len(roots), counts=log['counts'])), flush=True)
    models, decisions, scoring = score_models(SOURCE, source, roots)
    report.update(models=models, decisions=decisions, scoring_log=scoring,
        actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    if not all(scoring['checks'].values()):
        raise ValueError('frozen model or original decision reproduction failed: ' + str(scoring['checks']))
    report.update(status='complete', actual_wall_seconds=perf_counter() - started)
    save(directory / 'run.json', report)
    print(json.dumps(dict(phase='complete', models=len(models), decisions=len(decisions),
        counts=scoring['counts'], checks=scoring['checks'], seconds=report['actual_wall_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
