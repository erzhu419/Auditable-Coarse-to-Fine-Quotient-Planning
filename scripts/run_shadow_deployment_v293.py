#!/usr/bin/env python3
"""Run frozen shared-shadow learning and paid validated deployment."""
import argparse
from acfqp.science.shadow_deployment_v293 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output, dict(core=6, analysis=14, driver=3))
