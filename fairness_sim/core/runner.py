"""
Simulation Runner - Integrate all components and execute multi-round simulation of community farm fairness experiment
"""
import os
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Import components
from fairness_sim.agents.generate_agents import load_agents
from fairness_sim.allocation.mechanisms import (
    equal_distribution,
    needs_based_distribution,
    contribution_based_distribution,
    negotiation_based_distribution
)
from fairness_sim.resources.generation import (
    ResourceGenerator,
    calculate_production,
    initialize_resources
)
from fairness_sim.evaluation.system import (
    evaluate_distribution,
    print_distribution_summary
)
from fairness_sim.resources import survival as survival_needs
from fairness_sim.logging.llm_interaction import initialize_logger, close_logger
from fairness_sim.negotiation.progressive_voting import discussion_based_distribution

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = PACKAGE_ROOT / "config"

class SimulationRunner:
    """Simulation runner class, integrates components and runs multi-round simulation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize simulation runner
        
        Args:
            config: Configuration dictionary containing simulation parameters
        """
        # Default configuration
        self.default_config = {
            "rounds": 5,                   # Number of simulation rounds
            "agents_file": "agents.json",  # Agents file
            "initial_resource": None,      # Derived from generated agents when omitted
            "resource_multiplier": 2.0,    # Initial resources as a multiple of base needs
            "save_results": True,          # Whether to save results
            "results_dir": "results",      # Results save directory
            "distribution_methods": [      # Distribution method list
                "equal", "needs_based", "contribution_based", "negotiation"
            ]
        }
        
        # Apply user configuration
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)
        # Normalize agents_file path. The refactored package keeps runtime JSON
        # under fairness_sim/config, rather than beside this core module.
        agents_path = self.config.get("agents_file", "agents.json")
        if not os.path.isabs(agents_path):
            agents_path = str(DEFAULT_CONFIG_DIR / agents_path)
        self.config["agents_file"] = agents_path
        
        # Create results directory
        if self.config["save_results"] and not os.path.exists(self.config["results_dir"]):
            os.makedirs(self.config["results_dir"])
        
        # 🆕 Create unified experiment_id for this run (for negotiation logs and LLM logs)
        self.experiment_id = time.strftime("%Y%m%d_%H%M%S")
        # Initialize historical memory module (always enabled for all mechanisms).
        from fairness_sim.evaluation.memory import HistoricalMemoryModule
        self.enable_history = self.config.get("enable_history_awareness", True)  # Default: True (always on)
        if self.enable_history:
            self.memory_module = HistoricalMemoryModule(enable=True)
        else:
            self.memory_module = HistoricalMemoryModule(enable=False)
        
        # Initialize state
        self.current_round = 0
        self.agents = []
        self.resource_generator = None
        self.family_resources = {}  # Current resources owned by each family
        self.family_needs = {}      # Survival needs of each family
        self.family_productions = {}  # Resource production of each family
        self.distribution_results = []  # Distribution results for each round
        self.evaluation_results = []    # Evaluation results for each round
        self.fixed_M = None  # 🆕 Fixed labor processing capacity M = S/L (calculated in setup())
        self.base_needs_total = None  # 🆕 Base total survival needs (for consumption upgrade mechanism)
    
    def setup(self):
        """Load the generated cohort and initialize the simulation environment."""
        print("="*50)
        print("Setting up Community Farm Fairness Experiment Simulation Environment")
        print("="*50)
        
        # Load the locally generated cohort.
        print(f"Loading agents file: {os.path.abspath(self.config['agents_file'])}")
        if os.path.exists(self.config["agents_file"]):
            print(f"Loading agents from {self.config['agents_file']}...")
            self.agents = load_agents(self.config["agents_file"])
        else:
            raise FileNotFoundError(
                f"No agent file found at {self.config['agents_file']}. "
                "Generate it first with: python3 -m fairness_sim.agents.generate_agents"
            )

        if not self.agents:
            raise ValueError(
                f"The agent file {self.config['agents_file']} is empty. "
                "Generate agents first with: python3 -m fairness_sim.agents.generate_agents"
            )
        
        print(f"Loaded {len(self.agents)} agent families in total")
        
        # Calculate survival needs for each family
        print("\nCalculating family survival needs...")
        self.family_needs = {}
        for agent in self.agents:
            agent_id = agent["id"]
            # Calculate this family's survival needs (initial base calculation)
            needs = survival_needs.calculate_survival_needs(
                agent["members"],
                agent["labor_force"],
                system_resource_ratio=2.0  # Initial Usage Benchmarkα=2.0
            )
            self.family_needs[agent_id] = needs
            
            print(f"{agent['family_name']} Family (ID:{agent_id}) survival needs: ", end="")
            for resource, amount in needs.items():
                print(f"{resource}:{amount:.2f} ", end="")
            print()
        
        # Initialize family resources (no resources in initial round)
        self.family_resources = {agent["id"]: {} for agent in self.agents}
        
        # 🆕 Calculate and store fixed M value (labor processing capacity)
        # M is a skill constant: M = 2×S/L, independent of initial resource endowment
        # This ensures theoretical consistency across different resource abundance scenarios
        total_needs = sum([n.get('grain', 0) for n in self.family_needs.values()])
        total_labor = sum([agent.get("labor_force", 0) for agent in self.agents])
        
        # Store base needs for consumption upgrade mechanism
        self.base_needs_total = total_needs

        # Derive the initial resource pool from the generated cohort unless the
        # caller explicitly supplied an absolute amount.
        if self.config.get("initial_resource") is None:
            multiplier = float(self.config.get("resource_multiplier", 2.0))
            if multiplier <= 0:
                raise ValueError("resource_multiplier must be greater than zero")
            self.config["initial_resource"] = total_needs * multiplier
        initial_resources = float(self.config["initial_resource"])

        # Initialize resource generation only after the cohort-dependent totals
        # have been computed.
        print("\nInitializing resources...")
        self.resource_generator = ResourceGenerator(
            total_families=len(self.agents),
            initial_resource=self.config["initial_resource"]
        )
        
        if total_labor > 0:
            # Fixed M formula: M = S/L (skill constant)
            self.fixed_M = total_needs / total_labor
            
            print(f"\n{'='*60}")
            print(f"[LABOR PROCESSING CAPACITY - FIXED SKILL CONSTANT]")
            print(f"{'='*60}")
            print(f"  Base Total Needs (S): {total_needs:.2f} units")
            print(f"  Total Labor Force (L): {total_labor} laborers")
            print(f"  ✅ Fixed M = S/L = {total_needs:.2f}/{total_labor} = {self.fixed_M:.3f} units/laborer")
            print(f"  Labor Processing Capacity: {total_labor} × {self.fixed_M:.3f} = {total_labor * self.fixed_M:.1f} units")
            print(f"  ")
            print(f"  💡 Note: M is a skill constant, independent of initial resources.")
            print(f"     This ensures consistency across different resource scenarios.")
            
            # Resource abundance analysis
            alpha = initial_resources / total_needs
            print(f"\n{'='*60}")
            print(f"[RESOURCE ABUNDANCE ANALYSIS]")
            print(f"{'='*60}")
            print(f"  Initial Resources (R₀): {initial_resources:.2f} units")
            print(f"  Base Needs (S): {total_needs:.2f} units")
            print(f"  Abundance Coefficient (α): R₀/S = {alpha:.3f}")
            print(f"  ")
            if alpha < 2.0:
                level = "SCARCE"
                desc = "Resources below equilibrium point"
            elif alpha < 2.2:
                level = "ADEQUATE"
                desc = "Near equilibrium, slight growth expected"
            elif alpha < 2.5:
                level = "COMFORTABLE"
                desc = "Moderate growth expected"
            else:
                level = "ABUNDANT"
                desc = "Significant growth expected"
            print(f"  Resource Level: {level} (α={alpha:.3f})")
            print(f"  Description: {desc}")
            print(f"{'='*60}\n")
        else:
            self.fixed_M = 0.0
            print("\n[WARNING] No labor force found; production capacity is zero")
        
        print("\nSimulation environment setup complete!")
        return True
    
    def run_simulation(self):
        """Run the entire simulation process"""
        print("\n"+"="*50)
        print("Starting Community Farm Fairness Experiment Simulation")
        print(f"Experiment ID: {self.experiment_id}")
        print(f"Distribution Methods: {self.config['distribution_methods']}")
        print("="*50)
        
        # Initialize LLM interaction logger (using unified experiment_id)
        initialize_logger(log_dir="llm_logs", experiment_id=self.experiment_id)
        
        try:
            # Ensure environment is set up
            if not self.agents or not self.resource_generator:
                self.setup()
            
            # Run specified number of rounds
            for round_num in range(1, self.config["rounds"] + 1):
                self.current_round = round_num
                print(f"\nStarting round {round_num} simulation...")
                
                # Simulate for each distribution method
                for method in self.config["distribution_methods"]:
                    print(f"\n[DEBUG] Using distribution method: '{method}'")
                    
                    # Run single round simulation
                    distribution_result, evaluation_result = self.run_single_round(method)
                    
                    # Check for termination condition
                    if not distribution_result and evaluation_result.get("termination_reason") == "insufficient_survival_resources":
                        print(f"\n{'='*70}")
                        print(f"⚠️  SIMULATION TERMINATED DUE TO INSUFFICIENT SURVIVAL RESOURCES")
                        print(f"{'='*70}")
                        print(f"  Method: {method}")
                        print(f"  Termination Round: {round_num}")
                        print(f"  Survival Needs: {evaluation_result.get('survival_needs', 0):.2f}")
                        print(f"  Available Resources: {evaluation_result.get('available_resources', 0):.2f}")
                        print(f"{'='*70}\n")
                        
                        # Save what we have so far and return
                        if self.config["save_results"]:
                            self.save_simulation_results()
                        return self.evaluation_results
                    
                    # Store results
                    self.distribution_results.append(distribution_result)
                    self.evaluation_results.append(evaluation_result)
                
                print(f"\nRound {round_num} simulation complete")
            
            print("\n"+"="*50)
            print("Community Farm Fairness Experiment Simulation Ended")
            print("="*50)
            
            # Save final results
            if self.config["save_results"]:
                self.save_simulation_results()
            
            return self.evaluation_results
        
        finally:
            # Ensure logger is closed
            close_logger()
    
    def run_single_round(self, distribution_method: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Run single round simulation
        
        Args:
            distribution_method: Distribution method name
            
        Returns:
            Tuple containing distribution results and evaluation results
        """
        print(f"\n[DEBUG] run_single_round received method: '{distribution_method}'")
        current_resources = self.resource_generator.current_resources
        print(f"Currently available resources: {current_resources}")
        
        # 🎯 Calculate system resource ratio α (for information only)
        current_grain = current_resources.get("grain", 0)
        system_alpha = current_grain / self.base_needs_total if self.base_needs_total > 0 else 2.0
        
        # ℹ️ Consumption upgrade is DISABLED - always use base consumption (c=1.0)
        print(f"\n[CONSUMPTION] α={system_alpha:.2f}, c(α)=1.0 (Base Consumption - Consumption Upgrades Disabled)")
        
        # Update family needs based on fixed base consumption
        # Note: consumption coefficient is always 1.0 (no upgrade)
        for agent in self.agents:
            agent_id = agent["id"]
            needs = survival_needs.calculate_survival_needs(
                agent["members"],
                agent["labor_force"],
                system_resource_ratio=2.0  # Always use base α=2.0 (which gives c=1.0)
            )
            self.family_needs[agent_id] = needs
        
        # [CRITICAL DEBUG] Check if initial resource matches config
        if self.current_round == 1:
            configured = self.config.get("initial_resource", "NOT SET")
            actual = current_resources.get("grain", 0)
            print(f"\n{'='*60}")
            print(f"[CRITICAL] Round 1 Resource Check:")
            print(f"  Configured in config: {configured}")
            print(f"  Actual in system: {actual:.2f}")
            print(f"  Difference: {actual - configured:.2f} ({(actual - configured) / configured * 100:.1f}%)")
            print(f"{'='*60}\n")
        
        # ========== Survival Check ==========
        # Check if resources are sufficient for community survival
        total_survival_needs = sum(needs.get("grain", 0) for needs in self.family_needs.values())
        current_grain = current_resources.get("grain", 0)
        
        if current_grain < total_survival_needs:
            print(f"\n{'='*70}")
            print(f"🚨 CRITICAL: INSUFFICIENT RESOURCES FOR SURVIVAL")
            print(f"{'='*70}")
            print(f"  Total community survival needs: {total_survival_needs:.2f} units")
            print(f"  Currently available resources: {current_grain:.2f} units")
            print(f"  Deficit: {total_survival_needs - current_grain:.2f} units ({(total_survival_needs - current_grain) / total_survival_needs * 100:.1f}%)")
            print(f"\n  ❌ Simulation cannot continue - community cannot survive")
            print(f"  💀 Terminating at Round {self.current_round}")
            print(f"{'='*70}\n")
            
            # Return empty results to signal termination
            return {}, {"termination_reason": "insufficient_survival_resources", 
                       "survival_needs": total_survival_needs,
                       "available_resources": current_grain}
        
        # Distribute resources according to selected distribution method
        distribution_result = {}
        negotiation_metadata = None  # 🆕 Initialize for negotiation-based methods
        
        if distribution_method == "equal":
            print(f"[DEBUG] Matched 'equal' method, calling equal_distribution()")
            distribution_result = equal_distribution(current_resources, self.agents)
            method_name = "Equal Distribution"
        elif distribution_method == "needs_based":
            # Algorithm-driven needs-based distribution (revised version)
            distribution_result = needs_based_distribution(current_resources, self.agents, self.family_needs)
            method_name = "Needs-based Distribution (Algorithm)"
        elif distribution_method == "llm_needs_based":
            # LLM-driven needs-based distribution
            from fairness_sim.allocation.mechanisms import llm_driven_needs_based_distribution
            
            # Get previous round's distribution and evaluation
            prev_dist = None
            prev_eval = None
            if self.current_round > 1 and self.distribution_results:
                prev_dist = self.distribution_results[-1].get("distribution", {})
            if self.current_round > 1 and self.evaluation_results:
                prev_eval = self.evaluation_results[-1].get("agent_evaluations", [])
            
            distribution_result = llm_driven_needs_based_distribution(
                total_resources=current_resources,
                agents=self.agents,
                survival_needs=self.family_needs,
                round_number=self.current_round,
                previous_distribution=prev_dist,
                previous_evaluations=prev_eval
            )
            method_name = "Needs-based Distribution (LLM)"
        elif distribution_method == "contribution_based":
            distribution_result = contribution_based_distribution(
                current_resources, 
                self.agents,
                self.family_needs  # Pass survival needs to ensure basic survival
                # Note: Now distributes by labor force, not production
            )
            method_name = "Labor-based Distribution"
        elif distribution_method in ("negotiation", "negotiation_based", "distribution_based"):
            # 🆕 Receive metadata
            distribution_result, negotiation_metadata = negotiation_based_distribution(
                total_resources=current_resources,
                agents=self.agents,
                survival_needs=self.family_needs,
                round_number=self.current_round,
                experiment_id=self.experiment_id,
                return_metadata=True  # 🆕 Explicitly request metadata return
            )
            method_name = "Negotiation-based Distribution"
        elif distribution_method in ("dialogue", "dialogue_based"):
            # 🆕 Dialogue-driven negotiation distribution
            from fairness_sim.allocation.mechanisms import dialogue_based_distribution
            distribution_result, negotiation_metadata = dialogue_based_distribution(
                total_resources=current_resources,
                agents=self.agents,
                survival_needs=self.family_needs,
                round_number=self.current_round,
                experiment_id=self.experiment_id,
                return_metadata=True
            )
            method_name = "Dialogue Negotiation Distribution"
        elif distribution_method in ("discussion", "discussion_based"):
            # 🆕 Discussion-driven negotiation distribution
            distribution_result, negotiation_metadata = discussion_based_distribution(
                agents=self.agents,
                total_resources=current_resources,
                survival_needs=self.family_needs,
                round_number=self.current_round,
                memory_module=self.memory_module  # 🆕 Pass memory module for value evolution
            )
            method_name = "Discussion-Based Negotiation"
        else:
            print(f"Unknown distribution method: {distribution_method}")
            return {}, {}
        
        # 🆕 Extract dialogue results (if exists)
        dialogue_results = None
        if distribution_method in ("negotiation", "negotiation_based", "distribution_based", "dialogue", "dialogue_based", "discussion", "discussion_based"):
            if negotiation_metadata and negotiation_metadata.get("success"):
                dialogue_results = negotiation_metadata.get("dialogue_results") or negotiation_metadata.get("dialogue_history")
        
        # Update family resources
        for agent_id, resources in distribution_result.items():
            self.family_resources[agent_id] = resources
        
        # 🆕 Evaluate distribution results (pass dialogue results and negotiation metadata)
        evaluation_result = evaluate_distribution(
            distribution_result=distribution_result,
            agents=self.agents,
            total_resources=current_resources,
            round_number=self.current_round,
            distribution_method=method_name,
            survival_needs_map=self.family_needs,
            productions_map={},  # Temporarily empty, will be updated later
            dialogue_results=dialogue_results,  # Pass dialogue results
            memory_module=self.memory_module,  # 🆕 Phase 1: Pass historical memory module
            negotiation_metadata=negotiation_metadata if distribution_method in ("discussion", "discussion_based") else None  # 🆕 Pass 4-phase negotiation metadata
        )
        
        # 🎯 Calculate family production (considering satisfaction impact)
        self.family_productions = {}
        
        # 🆕 Use fixed M value (skill constant M = S/L)
        # M represents labor processing capacity (skill/physiological limit), 
        # independent of resource fluctuations or initial resource endowment
        max_resource_per_labor = self.fixed_M
        
        total_labor = sum([agent.get("labor_force", 0) for agent in self.agents])
        print(f"\n[PRODUCTION] Using Fixed M = {max_resource_per_labor:.3f} units/laborer (skill constant)")
        print(f"[PRODUCTION] Labor Processing Capacity = {total_labor} laborers × {max_resource_per_labor:.3f} = {total_labor * max_resource_per_labor:.1f} units")
        print(f"[PRODUCTION] Current Round Resources: {sum([r.get('grain', 0) for r in self.family_resources.values()]):.2f}")
        print(f"\n[DEBUG] Calculating production for {len(self.agents)} families:")
        for agent in self.agents:
            agent_id = agent["id"]
            resources = self.family_resources.get(agent_id, {})
            needs = self.family_needs.get(agent_id, {})
            labor_force = agent.get("labor_force", 0)
            print(f"  {agent['family_name']}: allocated={resources.get('grain', 0):.2f}, needs={needs.get('grain', 0):.2f}")
            
            # Get this family's satisfaction score
            satisfaction_score = None
            for eval_item in evaluation_result.get("agent_evaluations", []):
                if eval_item.get("agent_id") == agent_id:
                    satisfaction_score = eval_item.get("fairness_score")
                    break
            
            # Calculate production (with satisfaction impact and fixed M)
            production = calculate_production(
                resources, 
                needs, 
                labor_force,
                satisfaction_score=satisfaction_score,
                distribution_method=distribution_method,
                max_resource_per_labor=max_resource_per_labor  # 🆕 Pass fixed M (skill constant)
            )
            
            self.family_productions[agent_id] = production
        
        # [DEBUG] Print total production
        total_production = sum([p.get('grain', 0) for p in self.family_productions.values()])
        total_allocated = sum([r.get('grain', 0) for r in self.family_resources.values()])
        total_needs = sum([n.get('grain', 0) for n in self.family_needs.values()])
        total_available = total_allocated - total_needs
        
        # 🎯 Calculate and display incentive impact
        satisfaction_scores = [eval_item.get("fairness_score") for eval_item in evaluation_result.get("agent_evaluations", []) 
                              if eval_item.get("fairness_score") is not None]
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            avg_efficiency = 0.85 + 0.05 * avg_satisfaction
            print(f"\n[INCENTIVE IMPACT]")
            print(f"  Average Satisfaction: {avg_satisfaction:.2f}/5.0")
            print(f"  Average Efficiency Modifier: {avg_efficiency:.3f} ({(avg_efficiency-1)*100:+.1f}%)")
            print(f"  Expected base production (E=2.0): {total_available * 2.0:.2f}")
            print(f"  Actual production (with incentive): {total_production:.2f}")
            print(f"  Incentive effect: {((total_production / (total_available * 2.0) if total_available > 0 else 1) - 1) * 100:+.1f}%")
        
        print(f"\n[DEBUG] Production Summary:")
        print(f"  Total allocated: {total_allocated:.2f}")
        print(f"  Total survival needs: {total_needs:.2f}")
        print(f"  Total available for production: {total_available:.2f}")
        print(f"  Total production: {total_production:.2f}")
        
        # 🆕 Handle case where total_available is 0 or negative (possible in full resource negotiation)
        if total_available > 0:
            print(f"  Production rate: {total_production/total_available:.3f}× (should be ≈2.0-2.2)")
        else:
            print(f"  Production rate: N/A (no resources available for production - all consumed for survival)")
        
        # Generate next round resources
        next_resources = self.resource_generator.generate_next_round_resources(self.family_productions)
        
        # 🎯 Update evaluation results with production data (without calling LLM again)
        # Import statistics calculation function from evaluation_system
        from fairness_sim.evaluation.system import calculate_statistics, _compute_statistics_for_values
        
        # Compute effective input layer
        effective_input = {}
        for agent in self.agents:
            aid = agent["id"]
            alloc = distribution_result.get(aid, {})
            need = self.family_needs.get(aid, {})
            effective_input[aid] = {}
            for resource in set(list(alloc.keys()) + list(need.keys())):
                a = alloc.get(resource, 0.0)
                n = need.get(resource, 0.0)
                effective_input[aid][resource] = max(0.0, a - n)
        
        effective_stats = _compute_statistics_for_values(effective_input, self.agents)
        outcome_stats = _compute_statistics_for_values(self.family_productions, self.agents)
        
        # Update evaluation_result with layered statistics (avoid duplicate LLM calls)
        final_evaluation_result = evaluation_result.copy()
        final_evaluation_result["layered_statistics"] = {
            "allocation": evaluation_result.get("statistics", {}),
            "effective_input": effective_stats,
            "outcome": outcome_stats
        }
        # Ensure all required fields are present
        final_evaluation_result["statistics"] = evaluation_result.get("statistics", {})
        final_evaluation_result["average_satisfaction"] = evaluation_result.get("average_satisfaction")
        final_evaluation_result["agent_evaluations"] = evaluation_result.get("agent_evaluations", [])
        
        # Print distribution results summary
        print_distribution_summary(
            distribution_result=distribution_result,
            agents=self.agents,
            statistics=final_evaluation_result["statistics"],
            layered_statistics=final_evaluation_result.get("layered_statistics")
        )
        
        # Print average satisfaction
        if final_evaluation_result.get("average_satisfaction") is not None:
            print(f"\nAverage fairness satisfaction: {final_evaluation_result.get('average_satisfaction', 0):.2f}/5.0")
        else:
            print("\nUnable to calculate average satisfaction")
        
        # Build single round result
        round_result = {
            "round": self.current_round,
            "distribution_method": distribution_method,
            "method_name": method_name,
            "resources": current_resources,
            "distribution": distribution_result,
            "productions": self.family_productions,
            "next_resources": next_resources
        }
        
        # 🆕 Phase 1: After round ends, store historical data
        self.memory_module.add_round(
            round_num=self.current_round,
            distribution=distribution_result,
            evaluations=final_evaluation_result["agent_evaluations"],
            productions=self.family_productions,
            resources=current_resources
        )
        
        return round_result, final_evaluation_result
    
    def save_simulation_results(self):
        """Save simulation results to file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.config["results_dir"], f"simulation_results_{timestamp}.json")
        
        results = {
            "config": self.config,
            "agents": self.agents,
            "distribution_results": self.distribution_results,
            "evaluation_results": self.evaluation_results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nSimulation results saved to {results_file}")

def load_agents(filename: str = "agents.json") -> List[Dict[str, Any]]:
    """Load agents from file
    
    Args:
        filename: Agent file name
        
    Returns:
        Agent list
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("agents", [])
    except Exception as e:
        print(f"Error loading agents: {str(e)}")
        return []

def main():
    """Main function, run simulation"""
    # 🧪 Quick test for single mechanism
    config = {
        "rounds": 20,
        "initial_resource": None,
        "resource_multiplier": 2.0,
        "distribution_methods": ["discussion"],
        # Available mechanisms:
        # "equal"              - Equal distribution
        # "contribution_based" - Contribution-based distribution
        # "needs_based"        - Needs-based distribution
        # "negotiation"        - Negotiation-based distribution (new refactored version)
        "enable_history_awareness": True
    }
    
    print(f"[DEBUG] Configuration in main():")
    print(f"  - Rounds: {config['rounds']}")
    print(f"  - Initial Resource: {config['initial_resource']}")
    print(f"  - Distribution Methods: {config['distribution_methods']}")
    print()
    
    # Create and run simulation
    simulator = SimulationRunner(config)
    simulator.setup()
    results = simulator.run_simulation()
    
    # Output final results summary
    print("\n"+"="*50)
    print("Simulation Results Summary")
    print("="*50)
    
    # Analyze effects of various distribution methods
    if results:
        method_satisfaction = {}
        for result in results:
            method = result.get("distribution_method", "Unknown Method")
            satisfaction = result.get("average_satisfaction")
            
            if method not in method_satisfaction:
                method_satisfaction[method] = []
            
            if satisfaction is not None:
                method_satisfaction[method].append(satisfaction)
        
        # Calculate average satisfaction
        print("\n📊 Distribution Method Effectiveness Analysis:")
        for method, scores in method_satisfaction.items():
            if scores:
                avg = sum(scores) / len(scores)
                print(f"  {method}: Average satisfaction {avg:.2f}/5.0 ({len(scores)} rounds)")
            else:
                print(f"  {method}: No satisfaction data")
    else:
        print("⚠️ No result data available for analysis")

if __name__ == "__main__":
    main() 
