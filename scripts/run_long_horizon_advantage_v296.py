#!/usr/bin/env python3
"""Validate actions frozen from V294 with independent long SOURCE-H2 continuations."""
import argparse

from acfqp.science.long_horizon_advantage_v296 import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-summary', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.source_summary, args.output, dict(driver_native=4, independent_analysis=12,
        compact_verifier=8))


if __name__ == '__main__':
    main()
