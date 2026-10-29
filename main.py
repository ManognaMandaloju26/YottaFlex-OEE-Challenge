
import argparse
from pathlib import Path
import yaml

from src.oee_generator import generate_dataset
from src.validation import validate_dataset
from src.exporter import export_dataset


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    required = [
        "seed", "plants", "lines", "machines", "products",
        "days", "target_events", "target_counts"
    ]
    missing = [key for key in required if key not in config]

    if missing:
        raise ValueError(f"Missing config settings: {missing}")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="YottaFlex OEE Data Generator"
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--machines", type=int, default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--target-events", type=int, default=None)
    parser.add_argument("--target-counts", type=int, default=None)

    args = parser.parse_args()
    config = load_config(args.config)

    seed = args.seed if args.seed is not None else config["seed"]
    machines = args.machines if args.machines is not None else config["machines"]
    days = args.days if args.days is not None else config["days"]
    target_events = (
        args.target_events
        if args.target_events is not None
        else config["target_events"]
    )
    target_counts = (
        args.target_counts
        if args.target_counts is not None
        else config["target_counts"]
    )

    if machines < 1 or days < 1:
        parser.error("--machines and --days must be positive")
    if target_events < 0 or target_counts < 1:
        parser.error("--target-events must be nonnegative and --target-counts must be positive")

    output = Path(args.output or "output")

    print(f"Seed: {seed}")
    print(f"Machines: {machines}; Days: {days}")
    print(f"Target events: {target_events:,}")
    print(f"Target counts: {target_counts:,}")

    data = generate_dataset(
        seed=seed,
        machine_count=machines,
        days=days,
        target_events=target_events,
        target_counts=target_counts,
        line_count=config["lines"],
        product_count=config["products"],
    )

    report = validate_dataset(data)

    export_config = {
        **config,
        "seed": seed,
        "machines": machines,
        "days": days,
        "target_events": target_events,
        "target_counts": target_counts,
    }

    export_dataset(data, output, seed, export_config, report)

    print(f"Output folder: {output.resolve()}")
    print(f"Validation passed: {report['passed']}")
    print(f"Total issues: {report['issue_count']}")
    print(f"Unexpected issues: {report.get('unexpected_issue_count', 0)}")

    for name, frame in data.items():
        print(f"{name}: {len(frame):,} rows")


if __name__ == "__main__":
    main()
