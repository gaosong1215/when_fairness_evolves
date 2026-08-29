"""
Run experiments with real-time LLM interaction logging

This script records all LLM inputs and outputs to CSV file during experiment runtime
"""

from fairness_sim.core.runner import SimulationRunner

DEFAULT_CONFIG = {
    "rounds": 3,
    "agents_file": "agents.json",
    "initial_resource": None,
    "resource_multiplier": 2.0,
    "save_results": True,
    "results_dir": "results",
    "distribution_methods": ["contribution_based"],
}


def main(config=None):
    config = config or DEFAULT_CONFIG

    print("=" * 70)
    print("Community Farm Fairness Experiment - With LLM Interaction Logging")
    print("=" * 70)
    print("\nExperiment Configuration:")
    print(f"  Rounds: {config['rounds']}")
    print(f"  Distribution Methods: {', '.join(config['distribution_methods'])}")
    resource_text = config.get("initial_resource")
    if resource_text is None:
        resource_text = f"derived at {config.get('resource_multiplier', 2.0):g}× base needs"
    print(f"  Initial Resources: {resource_text}")
    print()

    simulator = SimulationRunner(config)
    results = simulator.run_simulation()

    print("\n" + "=" * 70)
    print("Experiment Completed!")
    print("=" * 70)
    print("\nGenerated Files:")
    print("  - Experiment Results JSON: results/simulation_results_*.json")
    print("  - LLM Interaction Log CSV: llm_logs/llm_interactions_*.csv")
    print("\nTips:")
    print("  Open the CSV file with Excel to view each LLM call.")
    print("  CSV file contains: round number, agent info, input prompt, output, score, etc.")
    return results


if __name__ == "__main__":
    main()
