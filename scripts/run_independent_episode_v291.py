#!/usr/bin/env python3
"""Confirm frozen whole-game learning on new training and evaluation histories."""
import argparse
from acfqp.science.independent_episode_v291 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
