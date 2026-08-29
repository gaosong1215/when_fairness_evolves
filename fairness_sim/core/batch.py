"""Run batch experiments for the generated agent cohort."""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Import SimulationRunner
from fairness_sim.core.runner import SimulationRunner

AGENTS_PATH = Path(__file__).resolve().parents[1] / "config" / "agents.json"


def load_cohort():
    """Load the generated cohort and fail with an actionable message."""
    if not AGENTS_PATH.exists():
        raise FileNotFoundError(
            f"No agent file found at {AGENTS_PATH}. "
            "Generate it first with: python3 -m fairness_sim.agents.generate_agents"
        )
    with AGENTS_PATH.open(encoding="utf-8") as handle:
        agents = json.load(handle).get("agents", [])
    if not agents:
        raise ValueError(
            f"The agent file {AGENTS_PATH} is empty. "
            "Generate agents first with: python3 -m fairness_sim.agents.generate_agents"
        )
    return agents


def calculate_base_needs(agents):
    return sum(
        2 * agent["labor_force"] + (agent["members"] - agent["labor_force"])
        for agent in agents
    )

# Experimental Configuration
DISTRIBUTION_METHODS = [
    "equal",                  # Equal distribution
    "llm_needs_based",        # Allocate as needed
    "contribution_based",     # Distribution by Contribution
    "discussion"              # Negotiated Allocation
]

ROUNDS = 30
RESOURCE_MULTIPLIERS = (1.8, 2.0, 2.2)

# Experimental Profile Templates
def create_config(distribution_method, initial_resource, rounds, experiment_name):
    """Create Experimental Configuration"""
    config = {
        "rounds": rounds,
        "agents_file": "agents.json",
        "initial_resource": initial_resource,
        "save_results": True,
        "results_dir": "results",
        "distribution_methods": [distribution_method],
        "enable_history_awareness": True,
        "experiment_name": experiment_name  # Add Lab Name Identification
    }
    return config

def run_experiment(distribution_method, initial_resource, rounds, experiment_id,
                   base_needs):
    """Run a single experiment"""
    # Calculate Resource Abundance Coefficient
    alpha = initial_resource / base_needs if base_needs else 0.0
    
    # Create Experiment Name
    method_names = {
        "equal": "Equal",
        "llm_needs_based": "NeedsBased",
        "contribution_based": "Contribution",
        "discussion": "Discussion"
    }
    method_short = method_names.get(distribution_method, distribution_method)
    experiment_name = f"{method_short}_R{initial_resource}_α{alpha:.2f}"
    
    print("\n" + "="*80)
    print(f"Experiment {experiment_id}: {experiment_name}")
    print("="*80)
    print(f"  Distribution method: {distribution_method}")
    print(f"  Initial Resources: {initial_resource} Unit (α={alpha:.2f})")
    print(f"  Round: {rounds}")
    print(f"  Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Create Experimental Configuration(Pass directly to SimulationRunner)
        config = create_config(distribution_method, initial_resource, rounds, experiment_name)
        
        # Run Simulation
        start_time = time.time()
        
        # Direct Calls SimulationRunner
        simulator = SimulationRunner(config)
        simulator.setup()
        results = simulator.run_simulation()
        
        duration = time.time() - start_time
        
        if results:
            print(f"  ✓ Experiment Complete,Elapsed time: {duration:.1f}Seconds")
            print(f"  End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        else:
            print(f"  ✗ Experiment failed:No results returned")
            return False
            
    except Exception as e:
        print(f"  ✗ Experimental abnormality: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main Function:Run all experiments"""
    print("="*80)
    print("Batch experiment initiation")
    print("="*80)
    agents = load_cohort()
    base_needs = calculate_base_needs(agents)
    resource_levels = [base_needs * multiplier for multiplier in RESOURCE_MULTIPLIERS]

    print(f"Generated cohort: {len(agents)} families")
    print(f"Base survival needs: {base_needs:.2f} units")
    print(f"Total Experiments: {len(DISTRIBUTION_METHODS)} × {len(resource_levels)} = {len(DISTRIBUTION_METHODS) * len(resource_levels)}")
    print(f"Each experimental round: {ROUNDS}")
    print(f"Expected total rounds: {len(DISTRIBUTION_METHODS) * len(resource_levels) * ROUNDS}")
    print("\nExperiment List:")
    
    experiment_id = 0
    experiments = []
    
    # Generate Experiment List
    for resource in resource_levels:
        for method in DISTRIBUTION_METHODS:
            experiment_id += 1
            alpha = resource / base_needs if base_needs else 0.0
            experiments.append({
                'id': experiment_id,
                'method': method,
                'resource': resource,
                'alpha': alpha,
                'rounds': ROUNDS
            })
            print(f"  {experiment_id}. {method:20s} | R={resource:.1f} (α={alpha:.2f}) | {ROUNDS} rounds")
    
    # Ask for confirmation
    print("\n" + "="*80)
    response = input("Whether to start running all experiments?(y/n): ")
    if response.lower() != 'y':
        print("Experiment canceled")
        return
    
    # Record the results of the experiment
    results = []
    successful = 0
    failed = 0
    
    # Start running the experiment
    overall_start_time = time.time()
    
    for exp in experiments:
        success = run_experiment(
            distribution_method=exp['method'],
            initial_resource=exp['resource'],
            rounds=exp['rounds'],
            experiment_id=exp['id'],
            base_needs=base_needs,
        )
        
        results.append({
            'experiment_id': exp['id'],
            'method': exp['method'],
            'resource': exp['resource'],
            'alpha': exp['alpha'],
            'rounds': exp['rounds'],
            'success': success
        })
        
        if success:
            successful += 1
        else:
            failed += 1
        
        # Take a break,AvoidAPIOverload
        if exp['id'] < len(experiments):
            print("\n  Break5Seconds until next experiment...")
            time.sleep(5)
    
    # Summary
    overall_duration = time.time() - overall_start_time
    
    print("\n" + "="*80)
    print("Batch experiment completed")
    print("="*80)
    print(f"Total time spent: {overall_duration/60:.1f} Minutes ({overall_duration:.0f}Seconds)")
    print(f"Success: {successful}/{len(experiments)}")
    print(f"Failed: {failed}/{len(experiments)}")
    
    # Save Experimental Record
    summary_file = f"batch_experiments_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_experiments': len(experiments),
            'successful': successful,
            'failed': failed,
            'total_duration_seconds': overall_duration,
            'experiments': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nExperimental record saved to: {summary_file}")
    
    # Print failed experiments
    if failed > 0:
        print("\nFailed experiments:")
        for result in results:
            if not result['success']:
                print(f"  - Experiment{result['experiment_id']}: {result['method']}, R={result['resource']}")

if __name__ == "__main__":
    main()
