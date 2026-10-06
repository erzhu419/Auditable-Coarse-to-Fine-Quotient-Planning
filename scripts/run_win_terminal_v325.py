import argparse

from acfqp.science.win_terminal_run_v325 import run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-summary', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.source_summary, args.output)
