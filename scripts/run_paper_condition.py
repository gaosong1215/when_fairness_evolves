#!/usr/bin/env python3
"""Run one generated-agent condition from the package.

Generate agents first with ``python3 -m fairness_sim.agents.generate_agents``.
API credentials, endpoint, and model are read from environment variables by
the runtime client; no secret is stored in this package.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fairness_sim.core.runner import SimulationRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--method",
        choices=["equal", "llm_needs_based", "contribution_based", "discussion"],
        default="discussion",
    )
    parser.add_argument(
        "--initial-resource", type=float, default=None,
        help="Absolute initial resource pool; defaults to a derived multiple of base needs",
    )
    parser.add_argument(
        "--resource-multiplier", type=float, default=2.0,
        help="Initial resources as a multiple of generated agents' base needs",
    )
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--results-dir", default="results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = {
        "rounds": args.rounds,
        "agents_file": "agents.json",
        "initial_resource": args.initial_resource,
        "resource_multiplier": args.resource_multiplier,
        "save_results": True,
        "results_dir": str(Path(args.results_dir)),
        "distribution_methods": [args.method],
        "enable_history_awareness": True,
        "experiment_name": f"generated_agents_{args.method}",
    }
    simulator = SimulationRunner(config)
    simulator.setup()
    simulator.run_simulation()


if __name__ == "__main__":
    main()
