"""
Survival Needs Calculation Module - Calculate basic survival resource requirements for each family
"""
from typing import Dict, Any

def calculate_consumption_coefficient(alpha: float) -> float:
    """Calculate consumption coefficient based on system resource level
    
    ✅ CONSUMPTION UPGRADE DISABLED
    - Consumption coefficient is always 1.0 (fixed base consumption)
    - Resources are not upgraded based on abundance level
    - This simplifies the system and removes the consumption mechanism
    
    Args:
        alpha: System resource level ratio (total_resources / base_needs)
        
    Returns:
        Consumption coefficient (always 1.0 - base consumption)
    """
    # 🔴 CONSUMPTION UPGRADE DISABLED
    # Always return 1.0 regardless of system resource level
    return 1.0


def calculate_survival_needs(
    total_members: int, 
    labor_force: int,
    system_resource_ratio: float = 2.0  # 🆕 System resource level α
) -> Dict[str, float]:
    """Calculate family's survival resource requirements (with consumption upgrade)
    
    Args:
        total_members: Total number of family members
        labor_force: Number of laborers
        system_resource_ratio: System resource level relative to this cohort's
            base needs.
        
    Returns:
        Survival needs dictionary with resource names as keys and requirement amounts as values
    """
    # Calculate non-labor population (children and elderly)
    non_labor = total_members - labor_force
    
    # 🎯 Get consumption coefficient based on system resource level
    consumption_coef = calculate_consumption_coefficient(system_resource_ratio)
    
    # Base consumption rates (before multiplier)
    base_labor_consumption = 2.0      # Each laborer base: 2 units
    base_non_labor_consumption = 1.0  # Each non-laborer base: 1 unit
    
    # 🎯 Apply consumption coefficient (consumption upgrade)
    labor_consumption = base_labor_consumption * consumption_coef
    non_labor_consumption = base_non_labor_consumption * consumption_coef
    
    # Calculate total grain requirement
    grain_need = (labor_force * labor_consumption) + (non_labor * non_labor_consumption)
    
    # Return only grain resource requirement
    return {"grain": grain_need}

def calculate_minimum_resource_threshold(
    agent: Dict[str, Any], 
    buffer_factor: float = 1.1
) -> Dict[str, float]:
    """Calculate agent family's minimum resource threshold (survival + buffer)
    
    Args:
        agent: Agent data dictionary
        buffer_factor: Buffer coefficient, defaults to 1.1 (10% above basic needs)
        
    Returns:
        Minimum resource threshold dictionary
    """
    # Calculate basic survival needs
    basic_needs = calculate_survival_needs(
        agent["members"],
        agent["labor_force"]
    )
    
    # Apply buffer factor
    threshold = {
        resource: amount * buffer_factor
        for resource, amount in basic_needs.items()
    }
    
    return threshold

def check_survival_status(
    family_resources: Dict[str, float],
    survival_needs: Dict[str, float]
) -> Dict[str, Any]:
    """Check family's survival status
    
    Args:
        family_resources: Resources owned by the family
        survival_needs: Survival needs of the family
        
    Returns:
        Survival status dictionary
    """
    status = {
        "survived": True,
        "deficit_resources": {},
        "survival_ratio": {}  # Satisfaction ratio for each resource
    }
    
    for resource, need_amount in survival_needs.items():
        # Get the amount of resources the family has
        have_amount = family_resources.get(resource, 0)
        
        # Calculate satisfaction ratio
        if need_amount > 0:
            ratio = have_amount / need_amount
        else:
            ratio = 1.0  # If need is 0, consider it fully satisfied
        
        status["survival_ratio"][resource] = ratio
        
        # Check if there's a deficit
        if have_amount < need_amount:
            deficit = need_amount - have_amount
            status["deficit_resources"][resource] = deficit
    
    # If any resource is below 50%, consider the family has not survived
    for ratio in status["survival_ratio"].values():
        if ratio < 0.5:
            status["survived"] = False
            break
    
    return status 
