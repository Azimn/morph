"""CLI for assays and resumable JSON turn streams."""
import argparse
import json
import gzip
from pathlib import Path
import sys
from .benchmark import run_benchmark
from .path_assay import run_path_assay, summarize
from .consequence_assay import run_consequence_assay
from .qualification import assess_all
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
    consequence = commands.add_parser("consequence-assay")
    consequence.add_argument("--output", type=Path)
    qualification = commands.add_parser("qualify")
    qualification.add_argument("--output", type=Path)
    qualification.add_argument("--evidence-index", type=Path)
    qualification.add_argument("--artifact-root", type=Path, default=Path("."))
    run = commands.add_parser("run")
    run.add_argument("--state", type=Path, required=True)
    run.add_argument("--seed", default="MORPH-Unit")
    args = parser.parse_args()
    if args.command in ("benchmark", "path-assay", "consequence-assay", "qualify"):
        if args.command == "benchmark":
            result = run_benchmark(args.sessions)
        elif args.command == "path-assay":
            result = run_path_assay()
        elif args.command == "consequence-assay":
            result = run_consequence_assay()
        else:
            packets = {}
            if args.evidence_index:
                raw = json.loads(args.evidence_index.read_text(encoding="utf-8"))
                if type(raw) is not dict or any(str(int(k)) != k for k in raw):
                    raise ValueError("Evidence index must map canonical Article numbers to packets")
                packets = {int(k): v for k, v in raw.items()}
            result = assess_all(packets, artifact_root=args.artifact_root)
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.suffix == ".gz":
                with args.output.open("wb") as stream:
                    with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=0) as archive:
                        archive.write(encoded.encode("utf-8"))
            else:
                args.output.write_text(encoded, encoding="utf-8")
            print(json.dumps({"output": str(args.output), "experiment": result.get("experiment", "ARTICLES-V3" if args.command == "qualify" else "MORPH-001"),
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
