"""CLI for assays and resumable JSON turn streams."""
import argparse
import json
import gzip
from pathlib import Path
import sys
from .benchmark import run_benchmark
from .path_assay import run_path_assay, summarize
from .core.persistence import load, save
from .core.zygote import MorphZygote


def main():
    parser = argparse.ArgumentParser(prog="morph")
    commands = parser.add_subparsers(dest="command", required=True)
    assay = commands.add_parser("benchmark")
    assay.add_argument("--sessions", type=int, default=30)
    assay.add_argument("--output", type=Path)
    order = commands.add_parser("path-assay")
    order.add_argument("--output", type=Path)
    order.add_argument("--summary-output", type=Path)
    run = commands.add_parser("run")
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--seed", default="MORPH-Unit")
    args = parser.parse_args()
    if args.command in ("benchmark", "path-assay"):
        result = run_benchmark(args.sessions) if args.command == "benchmark" else run_path_assay()
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.suffix == ".gz":
                with args.output.open("wb") as stream:
                    with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as archive:
                        archive.write(encoded.encode("utf-8"))
            else:
                args.output.write_text(encoded, encoding="utf-8")
            print(json.dumps({"output": str(args.output), "experiment": result.get("experiment", "MORPH-001"),
                              "gates_passed": result.get("gates_passed", result.get("pairwise_different"))}))
        else:
            print(encoded, end="")
        if args.command == "path-assay" and args.summary_output:
            args.summary_output.parent.mkdir(parents=True, exist_ok=True)
            args.summary_output.write_text(json.dumps(summarize(result), indent=2) + "\n", encoding="utf-8")
    else:
        agent = load(args.state) if args.state.exists() else MorphZygote(args.seed)
        for line in sys.stdin:
            if line.strip():
                result = agent.step(json.loads(line))
                save(agent, args.state)
                print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
