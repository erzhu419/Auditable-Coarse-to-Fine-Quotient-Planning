#!/usr/bin/env python3
"""Run the frozen continuous natural episode-learning campaign."""
import argparse
from acfqp.science.natural_episode_v292 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output, dict(native=13, online=7, analysis=18, driver=4))
