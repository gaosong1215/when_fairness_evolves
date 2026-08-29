#!/usr/bin/env python3
"""Run a fairness simulation using the locally generated agent cohort."""

from fairness_sim.core.runner import SimulationRunner


def main():
    config = {
        "rounds": 30,
        "agents_file": "agents.json",
        "initial_resource": None,
        "resource_multiplier": 2.0,
        "distribution_methods": ["discussion"],
        "save_results": True,
        "results_dir": "results",
        "enable_history_awareness": True,
        "experiment_name": "generated_agents_discussion",
    }

    simulator = SimulationRunner(config)
    simulator.setup()
    simulator.run_simulation()


if __name__ == "__main__":
    main()
