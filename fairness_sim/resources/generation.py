"""
Resource Generation Module - Handle dynamic evolution and regeneration of resources
"""
from typing import List, Dict, Any
import math

class ResourceGenerator:
    """Resource generator class responsible for handling dynamic resource generation and evolution"""
    
    def __init__(self, total_families: int, initial_resource: float):
        """Initialize resource generator
        
        Args:
            total_families: Total number of families
            initial_resource: System's initial total resources.
        """
        if initial_resource is None or initial_resource <= 0:
            raise ValueError("initial_resource must be greater than zero")

        total_grain = float(initial_resource)
        self.current_resources = {"grain": total_grain}
        
        # Track resource changes
        self.previous_total = total_grain
        self.sustainability_index = 1.0  # Resource sustainability index, below 1 indicates resources are decreasing
        self.overuse_warning = False  # Resource overuse warning

    def generate_next_round_resources(
        self, 
        family_productions: Dict[int, Dict[str, float]]
    ) -> Dict[str, float]:
        """Generate resources for the next round
        
        Args:
            family_productions: Family production dictionary with family ID as key and resource production dictionary as value
            
        Returns:
            Resource dictionary for next round
        """
        next_round_resources = {}
        
        # Calculate total production
        total_production = {}
        for family_id, production in family_productions.items():
            for resource_name, amount in production.items():
                if resource_name not in total_production:
                    total_production[resource_name] = 0
                total_production[resource_name] += amount
        
        # Calculate next round quantity for each resource
        for resource_name, current_amount in self.current_resources.items():
            # Family production amount
            production_amount = total_production.get(resource_name, 0)
            
            # Next round resources are only the sum of family production
            new_amount = production_amount
            
            # Update resource amount
            next_round_resources[resource_name] = new_amount
        
        # Update current resources
        self.current_resources = next_round_resources.copy()
        
        # Update sustainability index
        new_total = sum(next_round_resources.values())
        self.sustainability_index = new_total / self.previous_total if self.previous_total > 0 else 1.0
        self.previous_total = new_total
        
        # Check for resource overuse
        self.check_resource_sustainability()
        
        return next_round_resources
    
    def check_resource_sustainability(self):
        """Check resource sustainability and set overuse warning"""
        # If sustainability index is below 0.9, resources are decreasing significantly
        if self.sustainability_index < 0.9:
            self.overuse_warning = True
        else:
            self.overuse_warning = False

def calculate_production(
    family_resources: Dict[str, float],
    survival_needs: Dict[str, float],
    labor_force: int,
    satisfaction_score: float = None,
    distribution_method: str = None,
    max_resource_per_labor: float = None
) -> Dict[str, float]:
    """Calculate family's resource production (simplified model with fixed base efficiency)
    
    Args:
        family_resources: Resources owned by the family
        survival_needs: Survival needs of the family
        labor_force: Number of laborers in the family
        satisfaction_score: Family's satisfaction score with allocation (1-5)
        distribution_method: Name of distribution method
        max_resource_per_labor: Labor processing capacity M. If omitted, it is
            derived from the supplied survival needs and labor force.
        
    Returns:
        Production resource dictionary (includes both new production and unprocessed resources)
    """
    production = {}
    
    # ========== Simplified Parameters ==========
    # Fixed base efficiency (no labor density calculation)
    base_efficiency = 2.07
    
    # Labor processing capacity M (skill constant)
    # If not provided, derive the skill constant from this cohort.
    if max_resource_per_labor is None:
        total_need = sum(survival_needs.values())
        max_resource_per_labor = total_need / labor_force if labor_force > 0 else 0.0
    
    # 🎯 Satisfaction-driven efficiency adjustment
    satisfaction_efficiency = calculate_satisfaction_efficiency(
        satisfaction_score, distribution_method
    )
    
    # [DEBUG] Print satisfaction impact
    if satisfaction_score is not None:
        print(f"    [Incentive] Satisfaction={satisfaction_score:.1f} → Efficiency={satisfaction_efficiency:.3f} ({(satisfaction_efficiency-1)*100:+.1f}%)")
    
    # Calculate resources available for production (total resources minus survival needs)
    production_resources = {}
    for resource_name, amount in family_resources.items():
        needed_amount = survival_needs.get(resource_name, 0)
        # Resources available for production = Total resources - Survival needs
        available = max(0, amount - needed_amount)
        production_resources[resource_name] = available
        
        # [DEBUG] Print to check calculations
        if available > 20:  # Flag unusually high available resources
            print(f"[WARNING] Family has {available:.2f} available resources (allocated:{amount:.2f}, needs:{needed_amount:.2f})")
    
    # Calculate output for each resource
    for resource_name, available_amount in production_resources.items():
        # Calculate the actual amount of resources labor can process (has upper limit)
        max_processable = labor_force * max_resource_per_labor
        actual_processed = min(available_amount, max_processable)
        
        # Calculate unprocessed resources (due to insufficient labor)
        unprocessed = max(0, available_amount - max_processable)
        
        if actual_processed == 0 or labor_force == 0:
            # If no resources or labor, no output (no base output)
            output = 0
        else:
            # ========== Simplified Production Function ==========
            # Final efficiency = Fixed base efficiency × Satisfaction modifier
            final_efficiency = base_efficiency * satisfaction_efficiency
            
            # Output = Processed resources × Final efficiency
            output = actual_processed * final_efficiency
        
        # 🔄 Total resources carried to next round = New production + Unprocessed resources
        # Unprocessed resources (due to insufficient labor) are NOT wasted, 
        # they are carried over to the next round's resource pool
        total_next_round = output + unprocessed
        
        # Optional: Print info about unprocessed resources
        if unprocessed > 0:
            print(f"  [Carried Over] {unprocessed:.2f} units of {resource_name} could not be processed (insufficient labor), carried to next round")
        
        # Store result: includes both new production and unprocessed resources
        production[resource_name] = total_next_round
    
    return production

def calculate_satisfaction_efficiency(
    satisfaction_score: float = None, 
    distribution_method: str = None
) -> float:
    """Calculate production efficiency coefficient based on satisfaction (simplified linear mapping)
    
    Args:
        satisfaction_score: Satisfaction score (1-5), None indicates no score
        distribution_method: Name of distribution method (not used in simplified version)
        
    Returns:
        Production efficiency coefficient (0.8-1.2)
    """
    # ========== ✅ INCENTIVE MECHANISM ENABLED ==========
    # Satisfaction affects production efficiency
    
    if satisfaction_score is None:
        # Default efficiency when no satisfaction data available (neutral = 3.0)
        return 1.0
    
    # ========== Simplified Linear Mapping (±10% incentive range) ==========
    # Satisfaction 1.0 → Efficiency 0.9 (-10%)
    # Satisfaction 3.0 → Efficiency 1.0 (baseline)
    # Satisfaction 5.0 → Efficiency 1.1 (+10%)
    #
    # Formula: efficiency = 0.85 + 0.05 × satisfaction_score
    
    efficiency = 0.85 + 0.05 * satisfaction_score
    
    # Safety cap to ensure within valid range (0.9-1.1 for ±10%)
    return max(0.9, min(efficiency, 1.1))

def initialize_resources(num_families: int, initial_resource: float) -> Dict[str, float]:
    """Initialize system resources
    
    Args:
        num_families: Number of families. Retained for API compatibility.
        initial_resource: Initial resource pool for the generated cohort.
        
    Returns:
        Initial resource dictionary
    """
    return {"grain": float(initial_resource)}
