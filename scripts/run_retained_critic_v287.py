#!/usr/bin/env python3
"""Fit retained factual actor critics and evaluate fresh static H2 games."""
import argparse
from acfqp.science.retained_critic_v287 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
