"""CLI for assays and resumable JSON turn streams."""
import argparse
import json
from pathlib import Path
import sys
from .benchmark import run_benchmark
from .core.persistence import load, save
from .core.zygote import MorphZygote


def main():
    parser = argparse.ArgumentParser(prog="morph")
    commands = parser.add_subparsers(dest="command", required=True)
    assay = commands.add_parser("benchmark")
    assay.add_argument("--sessions", type=int, default=30)
    assay.add_argument("--output", type=Path)
    run = commands.add_parser("run")
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--seed", default="MORPH-Unit")
    args = parser.parse_args()
    if args.command == "benchmark":
        result = run_benchmark(args.sessions)
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
            print(json.dumps({"output": str(args.output), "same_boot": result["same_boot"],
                              "pairwise_different": result["pairwise_different"]}))
        else:
            print(encoded, end="")
    else:
        agent = load(args.state) if args.state.exists() else MorphZygote(args.seed)
        for line in sys.stdin:
            if line.strip():
                result = agent.step(json.loads(line))
                save(agent, args.state)
                print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
