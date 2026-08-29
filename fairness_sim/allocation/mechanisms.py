"""
Distribution Mechanisms Module - Contains different resource allocation strategies

Configuration:
    DECIMAL_PLACES: Number of decimal places for allocation results (default: 2)
                   - Set to 2 for values like 25.47, 18.92
                   - Set to 1 for values like 25.5, 18.9
                   - Set to 0 for integer values like 25, 18
"""
from fairness_sim.llm_client import get_llm_client, get_model_name
from typing import List, Dict, Any, Tuple
import math
from fairness_sim.negotiation.collaborative import collaborative_negotiation_distribution
from fairness_sim.negotiation.dialogue import dialogue_based_distribution as dialogue_negotiation_impl

# ============ ALLOCATION PRECISION CONFIGURATION ============
# Number of decimal places to keep in distribution results
DECIMAL_PLACES = 2  # Change to 1 or 0 for less precision
# ============================================================

def equal_distribution(
    total_resources: Dict[str, float], 
    agents: List[Dict[str, Any]]
) -> Dict[int, Dict[str, float]]:
    """Equal distribution mechanism - Simple average distribution
    
    Allocates total resources equally among all families.
    Note: Survival checking is done at simulation level before calling this function.
    
    Args:
        total_resources: Total resources dictionary, key is resource name, value is quantity
        agents: Agent list
        
    Returns:
        Distribution result dictionary, key is agent ID, value is allocated resources dictionary
    """
    num_families = len(agents)
    if num_families == 0:
        return {}
    
    distribution_result = {}
    
    print(f"\n  🔹 Equal Distribution (Simple Average):")
    for resource_name, total_amount in total_resources.items():
        per_family_amount = total_amount / num_families
        print(f"    Total: {total_amount:.1f}, Per Family: {per_family_amount:.2f}")
        
        for agent in agents:
            agent_id = agent["id"]
            if agent_id not in distribution_result:
                distribution_result[agent_id] = {}
            
            distribution_result[agent_id][resource_name] = per_family_amount
    
    # Round to specified decimal places
    return integerize_distribution(total_resources, agents, distribution_result, 
                                   survival_needs=None, enforce_min_survival=False, 
                                   decimal_places=DECIMAL_PLACES)

def calculate_production_needs(
    agent: Dict[str, Any], 
    survival_needs: Dict[str, float],
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]] = None,
    round_number: int = 1,
    previous_distribution: Dict[int, Dict[str, float]] = None
) -> Dict[str, float]:
    """Calculate family's production needs
    
    Args:
        agent: Agent data
        survival_needs: Survival needs
        total_resources: Total resources
        agents: All agents list, used for calculating averages etc.
        round_number: Current round number, used for dynamic adjustment
        previous_distribution: Previous round distribution results, used for reference
        
    Returns:
        Production needs dictionary
    """
    production_needs = {}
    labor_force = agent.get("labor_force", 0)
    members = agent.get("members", 0)
    agent_id = agent.get("id")
    
    # Maximum resource amount each laborer can process
    max_resource_per_labor = 5.0
    
    # Get agent's value type
    value_type = agent.get("value_type", "egalitarian")
    
    # Calculate average labor and members across all families
    avg_labor = 0
    avg_members = 0
    total_labor = 0
    if agents:
        total_labor = sum(a.get("labor_force", 0) for a in agents)
        total_members = sum(a.get("members", 0) for a in agents)
        avg_labor = total_labor / len(agents) if len(agents) > 0 else 0
        avg_members = total_members / len(agents) if len(agents) > 0 else 0
    
    # Calculate family dependency ratio (members/labor) - higher means heavier burden
    dependency_ratio = members / labor_force if labor_force > 0 else 0
    avg_dependency_ratio = avg_members / avg_labor if avg_labor > 0 else 0
    
    # Calculate previous round allocation status (if available)
    previous_satisfaction = 1.0  # Default to moderate satisfaction
    if previous_distribution and agent_id in previous_distribution:
        # Calculate previous round request fulfillment rate
        prev_resources = previous_distribution.get(agent_id, {})
        
        # Simplified calculation, should actually calculate satisfaction based on request vs allocation ratio
        if prev_resources:
            # Estimate previous round request (simplified handling)
            prev_satisfaction = sum(prev_resources.values()) / (labor_force * max_resource_per_labor * len(prev_resources))
            prev_satisfaction = max(0.5, min(prev_satisfaction, 1.5))  # Limit to reasonable range
    
    # Dynamic demand adjustment factor - increase adaptability with rounds
    adaptation_factor = min(1.0 + (round_number - 1) * 0.05, 1.3)  # Maximum 30% increase in adaptability
    
    # Resource analysis coefficient - analyze total resource changes from previous round
    resource_trend = 1.0  # Default to stable resources
    
    for resource_name, survival_need in survival_needs.items():
        total_amount = total_resources.get(resource_name, 0)
        per_capita_resource = total_amount / sum(a.get("members", 0) for a in agents) if agents else 0
        
        # Analyze resource abundance
        resource_abundance = total_amount / (total_members * 2) if total_members > 0 else 1.0
        
        # Calculate base production needs based on different value types
        if value_type == "egalitarian":  # Egalitarian
            # Egalitarian: Pursue equal resources per person, request based on population proportion
            fair_share = (total_amount / sum(a.get("members", 0) for a in agents)) if agents else 0
            
            # Adjust needs based on current resource abundance
            if resource_abundance < 0.8:  # Scarce resources
                # When resources are scarce, egalitarians tend to demand strict per-capita distribution
                adjustment = 0.9 * adaptation_factor
            elif resource_abundance > 1.2:  # Abundant resources
                # When resources are abundant, can increase request to ensure family members get enough
                adjustment = 1.1 * adaptation_factor
            else:  # Moderate resources
                adjustment = 1.0 * adaptation_factor
            
            target_resource = fair_share * members * adjustment
            production_need = max(0, target_resource - survival_need)
            
            # Limit to labor processing capacity
            max_processable = labor_force * max_resource_per_labor
            production_needs[resource_name] = min(production_need, max_processable)
            
        elif value_type == "merit_based":  # Merit-based
            # Merit-based: Emphasize labor contribution, families with more laborers should get more resources
            labor_proportion = labor_force / total_labor if total_labor > 0 else 0
            
            # Adjust needs based on resource abundance
            if resource_abundance < 0.8:  # Scarce resources
                # When resources are scarce, merit-based advocates emphasize distribution by labor
                adjustment = 1.2 * adaptation_factor
                
                # When resources are tight, may advocate more aggressively for labor rights
                if labor_proportion > 0.3:  # If major labor contributor
                    adjustment *= 1.1
            elif resource_abundance > 1.2:  # Abundant resources
                # When resources are abundant, can request more moderately
                adjustment = 1.0 * adaptation_factor
            else:  # Moderate resources
                adjustment = 1.1 * adaptation_factor
                
            target_resource = total_amount * labor_proportion * adjustment
            
            # Ensure at least basic survival resources, remainder distributed by labor proportion
            production_need = max(0, target_resource - survival_need)
            
            # Limit to labor processing capacity, but allow some overflow to reflect labor priority
            max_processable = labor_force * max_resource_per_labor * 1.2
            production_needs[resource_name] = min(production_need, max_processable)
            
        elif value_type == "needs_based":  # Needs-based (report based on own needs, without deducting survival first)
            # Calculate basic need per member
            base_need_per_member = 1.0
            
            # Adjust need coefficient based on dependency ratio (higher for vulnerable families)
            need_multiplier = 1.0
            if dependency_ratio > avg_dependency_ratio:
                need_multiplier = 1.0 + (dependency_ratio - avg_dependency_ratio) * 0.5
            
            # Adjust needs based on resource abundance and round number
            if resource_abundance < 0.7:  # Resources tight
                adjustment = 0.8 * adaptation_factor
                if dependency_ratio > 1.5:
                    adjustment = 0.9 * adaptation_factor
            elif resource_abundance > 1.3:  # Resources abundant
                adjustment = 1.2 * adaptation_factor
            else:  # Resources moderate
                adjustment = 1.0 * adaptation_factor
                
            # Directly use "total own needs" as reported demand (without deducting survival first)
            total_need = members * base_need_per_member * need_multiplier * adjustment
            
            # To avoid obvious waste, still cap at production capacity limit
            max_processable = labor_force * max_resource_per_labor
            production_needs[resource_name] = min(total_need, max_processable)
            
        elif value_type == "pragmatic":  # Pragmatic
            # Pragmatic: Flexibly adjust strategy, adjust needs based on resource abundance and own capacity
            resource_scarcity = total_amount / (sum(a.get("members", 0) for a in agents) * 2) if agents else 1
            
            # Adjust strategy based on previous round satisfaction
            strategy_adjustment = 1.0
            if previous_distribution:
                if prev_satisfaction < 0.8:  # Previous round allocation insufficient
                    # If previous round resources were insufficient, pragmatists will increase request
                    strategy_adjustment = 1.2
                elif prev_satisfaction > 1.2:  # Previous round allocation sufficient
                    # If previous round resources were sufficient, may moderately reduce request to avoid waste
                    strategy_adjustment = 0.9
            
            if resource_scarcity < 0.7:  # Resources tight
                # When resources are tight, be more pragmatic, request just enough to meet production needs
                production_need = labor_force * max_resource_per_labor * 0.9 * adaptation_factor * strategy_adjustment
            elif resource_scarcity > 1.3:  # Resources abundant
                # When resources are abundant, request more to maximize benefits
                production_need = labor_force * max_resource_per_labor * 1.1 * adaptation_factor * strategy_adjustment
            else:  # Resources moderate
                # When resources are moderate, request just enough to meet optimal production
                production_need = labor_force * max_resource_per_labor * adaptation_factor * strategy_adjustment
                
            production_needs[resource_name] = production_need
            
        elif value_type == "altruistic":  # Altruistic
            # Altruistic: Prioritize collective interests, reduce own needs when resources are scarce
            total_ideal_need = total_labor * max_resource_per_labor
            resource_scarcity = total_amount / total_ideal_need if total_ideal_need > 0 else 1
            
            # Family size ratio relative to average
            size_ratio = members / avg_members if avg_members > 0 else 1
            
            # Adjust altruism level based on round number - as rounds increase, altruists may focus more on own family interests
            altruism_decay = max(0.8, 1.0 - (round_number - 1) * 0.03)  # Altruism decreases by at most 20%
            
            if resource_scarcity < 0.6:  # Resources severely insufficient
                # Significantly reduce demand, especially for larger families
                reduction_factor = (0.5 if size_ratio > 1.2 else 0.7) * altruism_decay
                production_need = labor_force * max_resource_per_labor * reduction_factor
            elif resource_scarcity < 0.9:  # Resources somewhat tight
                # Moderately reduce demand
                reduction_factor = (0.7 if size_ratio > 1.1 else 0.8) * altruism_decay
                production_need = labor_force * max_resource_per_labor * reduction_factor
            else:  # Resources sufficient
                # Request moderate resources, not exceeding fair share
                production_need = min(
                    labor_force * max_resource_per_labor * 0.9 * altruism_decay,
                    (total_amount / len(agents)) if agents else 0
                ) * adaptation_factor
            
            production_needs[resource_name] = production_need
        else:
            # Default calculation method
            production_needs[resource_name] = labor_force * max_resource_per_labor * adaptation_factor
    
    return production_needs

def needs_based_distribution(
    total_resources: Dict[str, float], 
    agents: List[Dict[str, Any]], 
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    previous_distribution: Dict[int, Dict[str, float]] = None
) -> Dict[int, Dict[str, float]]:
    """Needs-based distribution mechanism (revised version)
    
    Truly distributes based on actual family needs, prioritizing basic survival needs.
    
    Key improvements:
    1. First ensure basic survival needs proportional to population
    2. Remaining resources consider population, labor, and special needs
    3. Set minimum per-capita guarantee threshold
    
    Args:
        total_resources: Total resources dictionary, key is resource name, value is quantity
        agents: Agent list
        survival_needs: Survival needs dictionary, key is agent ID, value is needed resources dictionary
        round_number: Current round number, used for dynamic adjustment
        previous_distribution: Previous round distribution results, used for reference
        
    Returns:
        Distribution result dictionary, key is agent ID, value is allocated resources dictionary
    """
    if not agents or not survival_needs:
        return {}
    
    distribution_result = {}
    
    # 🆕 Calculate community total population and total labor
    total_members = sum(agent.get("members", 0) for agent in agents)
    total_labor = sum(agent.get("labor_force", 0) for agent in agents)
    
    print("\n" + "="*50)
    print("🆕 Needs-Based Distribution (Revised Version)")
    print("="*50)
    
    for resource_name, total_amount in total_resources.items():
        # 🆕 Phase 1: Calculate basic survival needs (70% resources)
        basic_resource_pool = total_amount * 0.70
        
        # Calculate total basic survival needs
        total_survival_needs = sum(
            survival_needs.get(agent["id"], {}).get(resource_name, 0) 
            for agent in agents
        )
        
        print(f"\nResource Type: {resource_name}")
        print(f"  Total Resources: {total_amount:.2f}")
        print(f"  Basic Guarantee Pool (70%): {basic_resource_pool:.2f}")
        print(f"  Total Survival Needs: {total_survival_needs:.2f}")
        
        # Allocate basic shares (by population proportion)
        basic_allocations = {}
        if total_members > 0:
            # 🆕 Allocate basic guarantee resources by population proportion
            for agent in agents:
                agent_id = agent["id"]
                members = agent.get("members", 0)
                
                # Population proportion
                population_ratio = members / total_members
                basic_allocation = basic_resource_pool * population_ratio
                
                basic_allocations[agent_id] = basic_allocation
                
                if agent_id not in distribution_result:
                    distribution_result[agent_id] = {}
                distribution_result[agent_id][resource_name] = basic_allocation
        
        # 🆕 Phase 2: Allocate remaining resources (30% resources)
        remaining_resource_pool = total_amount * 0.30
        
        # Remaining resource allocation weights: 50% by population, 30% by labor, 20% by special needs
        for agent in agents:
            agent_id = agent["id"]
            members = agent.get("members", 0)
            labor_force = agent.get("labor_force", 0)
            
            # Calculate labor density (labor/population)
            labor_density = labor_force / members if members > 0 else 0
            
            # Calculate special needs weight (low labor density family = heavy dependent burden)
            special_need_weight = 0
            if labor_density < 0.5:  # Labor density < 50%, belongs to dependent-type family
                special_need_weight = (0.5 - labor_density) * 2  # Between 0-1
            
            # Population weight (50%)
            population_share = (members / total_members) * 0.50 if total_members > 0 else 0
            
            # Labor weight (30%)
            labor_share = (labor_force / total_labor) * 0.30 if total_labor > 0 else 0
            
            # Special needs weight (20%)
            total_special_need_weight = sum(
                ((a.get("labor_force", 0) / a.get("members", 1)) < 0.5) * 
                (0.5 - (a.get("labor_force", 0) / a.get("members", 1))) * 2
                for a in agents
            )
            special_share = (special_need_weight / total_special_need_weight) * 0.20 if total_special_need_weight > 0 else 0
            
            # Total weight
            total_share = population_share + labor_share + special_share
            
            # Allocate remaining resources
            additional_allocation = remaining_resource_pool * total_share
            distribution_result[agent_id][resource_name] += additional_allocation
            
            print(f"\n  {agent['family_name']} Family (ID:{agent_id}, {members} people, {labor_force} laborers):")
            print(f"    Basic Guarantee: {basic_allocations[agent_id]:.2f} (Population ratio: {members}/{total_members})")
            print(f"    Additional Allocation: {additional_allocation:.2f} (Population{population_share:.3f} + Labor{labor_share:.3f} + Special{special_share:.3f})")
            print(f"    Total Allocation: {distribution_result[agent_id][resource_name]:.2f}")
            print(f"    Per Capita: {distribution_result[agent_id][resource_name]/members:.2f}")
    
    # 🆕 Phase 3: Ensure minimum survival threshold (per capita >= 3.5)
    print("\n" + "-"*50)
    print("🔍 Checking Minimum Survival Threshold (per capita >= 3.5)")
    print("-"*50)
    
    for resource_name in total_resources.keys():
        min_per_capita = 3.5  # Minimum per capita resources
        adjustments = []
        
        for agent in agents:
            agent_id = agent["id"]
            members = agent.get("members", 0)
            current_allocation = distribution_result[agent_id][resource_name]
            per_capita = current_allocation / members if members > 0 else 0
            
            if per_capita < min_per_capita:
                shortage = (min_per_capita - per_capita) * members
                adjustments.append((agent_id, agent['family_name'], shortage, per_capita))
        
        if adjustments:
            print(f"\n⚠️ Found {len(adjustments)} families below survival threshold:")
            total_shortage = sum(adj[2] for adj in adjustments)
            
            for agent_id, family_name, shortage, current_per_capita in adjustments:
                print(f"  {family_name} Family: Per capita {current_per_capita:.2f} < 3.5, Gap {shortage:.2f}")
            
            # Reallocate resources from families with above-average per capita
            avg_per_capita = total_resources[resource_name] / total_members
            donors = []
            
            for agent in agents:
                agent_id = agent["id"]
                members = agent.get("members", 0)
                current_allocation = distribution_result[agent_id][resource_name]
                per_capita = current_allocation / members if members > 0 else 0
                
                if per_capita > avg_per_capita:
                    surplus = (per_capita - avg_per_capita) * members * 0.3  # Donate 30% of excess
                    donors.append((agent_id, surplus))
            
            total_surplus = sum(donor[1] for donor in donors)
            
            if total_surplus > 0:
                print(f"\n  Reallocating resources from {len(donors)} surplus families, Total reallocation: {total_surplus:.2f}")
                
                # Proportional reallocation
                for agent_id, family_name, shortage, _ in adjustments:
                    compensation = (shortage / total_shortage) * min(total_surplus, total_shortage)
                    distribution_result[agent_id][resource_name] += compensation
                    print(f"  → {family_name} Family receives compensation: +{compensation:.2f}")
                
                # Deduct from donors
                for donor_id, surplus in donors:
                    deduction = (surplus / total_surplus) * min(total_surplus, total_shortage)
                    distribution_result[donor_id][resource_name] -= deduction
            else:
                print(f"  ⚠️ No reallocatable resources, total resources insufficient to guarantee survival threshold for all families")
    
    print("\n" + "="*50)
    print("✅ Needs-Based Distribution Complete")
    print("="*50 + "\n")
    
    # Round to specified decimal places (enforcing minimum survival)
    return integerize_distribution(total_resources, agents, distribution_result, 
                                   survival_needs=survival_needs, enforce_min_survival=True, 
                                   decimal_places=DECIMAL_PLACES)

def contribution_based_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    minimum_survival_resources: Dict[int, Dict[str, float]] = None,
    previous_production: Dict[int, Dict[str, float]] = None  # Preserve parameters for compatibility calls,Do not use
) -> Dict[int, Dict[str, float]]:
    """Labor-based distribution mechanism (Two-tier allocation)
    
    Two-tier allocation structure:
    1. Tier 1 - Survival Guarantee: Each family receives survival needs
    2. Tier 2 - Surplus Allocation: Remaining resources distributed by labor force proportion
    
    Distribution logic:
    - Always distribute surplus by labor force proportion
    - More laborers = more surplus allocation (incentivizes large labor force)
    
    Args:
        total_resources: Total resources dictionary, key is resource name, value is quantity
        agents: Agent list
        minimum_survival_resources: Minimum survival resource needs, key is agent ID, value is resources dictionary
        previous_production: (Unused, kept for compatibility)
        
    Returns:
        Distribution result dictionary, key is agent ID, value is allocated resources dictionary
    """
    if not agents:
        return {}
    
    # Calculate total workforce
    total_labor_force = sum(agent.get("labor_force", 0) for agent in agents)
    if total_labor_force == 0:
        # If no labor force, use equal distribution
        return equal_distribution(total_resources, agents, minimum_survival_resources)
    
    distribution_result = {}
    
    # Two-tier allocation with clear printout
    if minimum_survival_resources:
        print(f"\n  🔹 Labor-Based Distribution (Two-tier):")
    
    # Process each resource separately
    for resource_name, total_amount in total_resources.items():
        # Step 1: Calculate total survival needs
        survival_resources_total = 0
        if minimum_survival_resources:
            for agent_id, needs in minimum_survival_resources.items():
                survival_resources_total += needs.get(resource_name, 0)
        
        # Step 2: Calculate surplus
        distributable_resources = max(0, total_amount - survival_resources_total)
        
        if minimum_survival_resources:
            if distributable_resources < 0:
                print(f"    ⚠️  WARNING: Insufficient resources! Total={total_amount:.1f}, Survival={survival_resources_total:.1f}")
                distributable_resources = 0
            print(f"    Total: {total_amount:.1f}, Survival: {survival_resources_total:.1f}, Surplus: {distributable_resources:.1f}")
        
        # Step 3: Distribute
        for agent in agents:
            agent_id = agent["id"]
            
            if agent_id not in distribution_result:
                distribution_result[agent_id] = {}
            
            # Survival guarantee
            base_survival_amount = 0
            if minimum_survival_resources and agent_id in minimum_survival_resources:
                base_survival_amount = minimum_survival_resources[agent_id].get(resource_name, 0)
            
            # 🎯 Surplus allocation: by labor force
            labor_force = agent.get("labor_force", 0)
            labor_proportion = labor_force / total_labor_force if total_labor_force > 0 else 0
            contribution_amount = labor_proportion * distributable_resources
            
            # Total allocation
            distribution_result[agent_id][resource_name] = base_survival_amount + contribution_amount
    
    # Round to specified decimal places
    return integerize_distribution(total_resources, agents, distribution_result, 
                                   survival_needs=minimum_survival_resources, enforce_min_survival=False, 
                                   decimal_places=DECIMAL_PLACES)

def negotiation_based_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    previous_distribution: Dict[int, Dict[str, float]] = None,
    max_negotiation_rounds: int = 3,
    experiment_id: str = None,
    return_metadata: bool = True
) -> Any:
    """Negotiation-based distribution mechanism - new version using collaborative negotiation
    
    Through multi-stage negotiation discussions, family agents jointly construct allocation plan
    
    Args:
        total_resources: Total resources dictionary
        agents: Agent list
        survival_needs: Survival needs dictionary
        round_number: Current round number
        previous_distribution: Previous round distribution results
        max_negotiation_rounds: Maximum negotiation rounds
        experiment_id: Experiment ID, used to unify logs across all rounds
        return_metadata: Whether to return negotiation metadata
        
    Returns:
        If return_metadata=True: (final_allocation, negotiation_data)
        If return_metadata=False: final_allocation
    """
    print("\n🔄 Using new collaborative negotiation distribution mechanism")
    
    # Call new collaborative negotiation distribution
    return collaborative_negotiation_distribution(
        total_resources=total_resources,
        agents=agents,
        survival_needs=survival_needs,
        round_number=round_number,
        previous_distribution=previous_distribution,
        max_negotiation_rounds=max_negotiation_rounds,
        experiment_id=experiment_id,
        return_metadata=return_metadata
    )

def generate_initial_proposals(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int,
    previous_distribution: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, float]]:
    """Generate Initial Proposal
    
    Each agent proposes an initial allocation proposal based on their values
    """
    proposals = {}
    
    for agent in agents:
        agent_id = agent["id"]
        value_type = agent["value_type"]
        
        # Generate proposals based on values
        if value_type == "egalitarian":
            # Egalitarianism:Equal distribution
            proposal = equal_distribution(total_resources, agents)
            proposals[agent_id] = proposal
            
        elif value_type == "needs_based":
            # Demand-oriented:Allocate as needed
            proposal = needs_based_distribution(
                total_resources, agents, survival_needs, round_number, previous_distribution
            )
            proposals[agent_id] = proposal
            
        elif value_type == "merit_based":
            # Contribution Orientation:Distribution by Contribution
            proposal = contribution_based_distribution(
                total_resources, agents, survival_needs
            )
            proposals[agent_id] = proposal
            
        elif value_type == "altruistic":
            # Altruism:Prioritize vulnerable groups
            proposal = altruistic_distribution(
                total_resources, agents, survival_needs
            )
            proposals[agent_id] = proposal
            
        elif value_type == "pragmatic":
            # Pragmatism:Hybrid Scheme
            proposal = pragmatic_distribution(
                total_resources, agents, survival_needs, round_number, previous_distribution
            )
            proposals[agent_id] = proposal
    
    return proposals

def altruistic_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, float]]:
    """Altruistic Allocation
    
    Prioritize the needs of vulnerable populations,I am willing to allocate less
    """
    distribution_result = {}
    
    # Calculate dependency ratio per household(Number of members/Workforce)
    dependency_ratios = {}
    for agent in agents:
        agent_id = agent["id"]
        members = agent.get("members", 1)
        labor_force = agent.get("labor_force", 1)
        dependency_ratios[agent_id] = members / labor_force if labor_force > 0 else float('inf')
    
    # Sort by dependency ratio,High Dependency Ratio First
    sorted_agents = sorted(agents, key=lambda x: dependency_ratios[x["id"]], reverse=True)
    
    remaining_resources = total_resources.copy()
    
    # Ensure that all families have access to basic subsistence resources first
    for agent in sorted_agents:
        agent_id = agent["id"]
        distribution_result[agent_id] = {}
        
        for resource_name, total_amount in remaining_resources.items():
            survival_need = survival_needs.get(agent_id, {}).get(resource_name, 0)
            allocated = min(survival_need, remaining_resources[resource_name])
            
            distribution_result[agent_id][resource_name] = allocated
            remaining_resources[resource_name] -= allocated
    
    # Remaining resources are allocated according to the level of demand
    for agent in sorted_agents:
        agent_id = agent["id"]
        dependency_ratio = dependency_ratios[agent_id]
        
        for resource_name, remaining_amount in remaining_resources.items():
            if remaining_amount <= 0:
                continue
                
            # Rely on families with high ratios for more surplus resources
            additional_share = remaining_amount * (dependency_ratio / sum(dependency_ratios.values()))
            additional_share = min(additional_share, remaining_amount)
            
            distribution_result[agent_id][resource_name] += additional_share
            remaining_resources[resource_name] -= additional_share
    
    return distribution_result

def pragmatic_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int,
    previous_distribution: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, float]]:
    """Pragmatic Allocation
    
    Comprehensive consideration of multiple factors,Seeking balance
    """
    # Calculate weights
    survival_weight = 0.4  # Survival Requirement Weight
    equality_weight = 0.3  # Equal weight
    merit_weight = 0.3     # Contribution Weight
    
    # Generate three basic allocation scenarios
    survival_allocation = needs_based_distribution(
        total_resources, agents, survival_needs, round_number, previous_distribution
    )
    equality_allocation = equal_distribution(total_resources, agents)
    merit_allocation = contribution_based_distribution(
        total_resources, agents, survival_needs
    )
    
    # Weighted Merge
    final_allocation = {}
    for agent in agents:
        agent_id = agent["id"]
        final_allocation[agent_id] = {}
        
        for resource_name in total_resources.keys():
            survival_amount = survival_allocation.get(agent_id, {}).get(resource_name, 0)
            equality_amount = equality_allocation.get(agent_id, {}).get(resource_name, 0)
            merit_amount = merit_allocation.get(agent_id, {}).get(resource_name, 0)
            
            weighted_amount = (
                survival_amount * survival_weight +
                equality_amount * equality_weight +
                merit_amount * merit_weight
            )
            
            final_allocation[agent_id][resource_name] = weighted_amount
    
    return final_allocation

def evaluate_proposals(
    proposals: Dict[int, Dict[int, Dict[str, float]]],
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, Any]]:
    """Evaluate each proposal
    
    Each agent scores the proposals of other agents
    """
    evaluations = {}
    
    for agent in agents:
        agent_id = agent["id"]
        value_type = agent["value_type"]
        evaluations[agent_id] = {}
        
        for proposer_id, proposal in proposals.items():
            # Evaluate proposals based on values
            score = evaluate_proposal_by_values(
                proposal, agent, total_resources, survival_needs, agents
            )
            evaluations[agent_id][proposer_id] = {
                "score": score,
                "agreement": score >= 3.0  # 3Minutes or more to agree
            }
    
    return evaluations

def evaluate_proposal_by_values(
    proposal: Dict[int, Dict[str, float]],
    evaluator: Dict[str, Any],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    agents: List[Dict[str, Any]]
) -> float:
    """Evaluate proposals based on values"""
    value_type = evaluator["value_type"]
    evaluator_id = evaluator["id"]
    
    # Get Evaluator's Own Assignment
    my_allocation = proposal.get(evaluator_id, {})
    
    # Calculate base metrics
    total_allocated = sum(sum(allocation.values()) for allocation in proposal.values())
    resource_efficiency = total_allocated / sum(total_resources.values()) if sum(total_resources.values()) > 0 else 0
    
    # Check Survival Needs Satisfaction
    my_survival_needs = survival_needs.get(evaluator_id, {})
    survival_satisfaction = 0
    if my_survival_needs:
        survival_satisfaction = sum(
            min(my_allocation.get(resource, 0) / need, 1.0) 
            for resource, need in my_survival_needs.items() if need > 0
        ) / len(my_survival_needs)
    
    # Rated according to values
    if value_type == "egalitarian":
        # Egalitarianism:Focus on distributive equity
        allocations = list(proposal.values())
        if allocations:
            variance = calculate_allocation_variance(allocations)
            equality_score = max(0, 5 - variance * 2)  # The smaller the variance, the higher the score
            return (equality_score + survival_satisfaction * 5) / 2
            
    elif value_type == "needs_based":
        # Demand-oriented:Focus on Demand Satisfaction
        overall_survival_satisfaction = calculate_overall_survival_satisfaction(
            proposal, survival_needs
        )
        return (overall_survival_satisfaction * 5 + survival_satisfaction * 5) / 2
        
    elif value_type == "merit_based":
        # Contribution Orientation:Focus on efficiency and rewards for the workforce
        labor_efficiency = calculate_labor_efficiency(proposal, agents)
        return (labor_efficiency * 5 + resource_efficiency * 5) / 2
        
    elif value_type == "altruistic":
        # Altruism:Focus on the vulnerable
        weak_group_satisfaction = calculate_weak_group_satisfaction(
            proposal, agents, survival_needs
        )
        return (weak_group_satisfaction * 5 + survival_satisfaction * 5) / 2
        
    elif value_type == "pragmatic":
        # Pragmatism:Comprehensive assessment
        overall_score = (
            survival_satisfaction * 2 +
            resource_efficiency * 2 +
            calculate_allocation_balance(proposal) * 1
        ) / 5
        return overall_score * 5
    
    return 2.5  # Default moderate rating

def calculate_allocation_variance(allocations: List[Dict[str, float]]) -> float:
    """Calculate allocation variance"""
    if not allocations:
        return 0
    
    # Calculate total for each allocation
    totals = [sum(allocation.values()) for allocation in allocations]
    mean_total = sum(totals) / len(totals)
    
    # Calculate variance
    variance = sum((total - mean_total) ** 2 for total in totals) / len(totals)
    return variance

def calculate_overall_survival_satisfaction(
    proposal: Dict[int, Dict[str, float]],
    survival_needs: Dict[int, Dict[str, float]]
) -> float:
    """Calculate overall survival needs satisfaction"""
    if not survival_needs:
        return 1.0
    
    total_satisfaction = 0
    count = 0
    
    for agent_id, needs in survival_needs.items():
        allocation = proposal.get(agent_id, {})
        if needs:
            satisfaction = sum(
                min(allocation.get(resource, 0) / need, 1.0)
                for resource, need in needs.items() if need > 0
            ) / len(needs)
            total_satisfaction += satisfaction
            count += 1
    
    return total_satisfaction / count if count > 0 else 1.0

def calculate_labor_efficiency(
    proposal: Dict[int, Dict[str, float]],
    agents: List[Dict[str, Any]]
) -> float:
    """Calculate labor efficiency"""
    total_labor = sum(agent.get("labor_force", 0) for agent in agents)
    if total_labor == 0:
        return 1.0
    
    # Calculate average allocation per laborer
    total_allocated = sum(sum(allocation.values()) for allocation in proposal.values())
    labor_efficiency = total_allocated / total_labor
    
    # Normalize to 0-1 range
    return min(labor_efficiency / 10, 1.0)  # Assume 10 units per laborer as ideal value

def calculate_weak_group_satisfaction(
    proposal: Dict[int, Dict[str, float]],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]]
) -> float:
    """Calculate vulnerable group satisfaction"""
    # Identify vulnerable groups (families with high dependency ratio)
    weak_groups = []
    for agent in agents:
        members = agent.get("members", 1)
        labor_force = agent.get("labor_force", 1)
        dependency_ratio = members / labor_force if labor_force > 0 else float('inf')
        if dependency_ratio > 2.0:  # Dependency ratio > 2 considered vulnerable
            weak_groups.append(agent["id"])
    
    if not weak_groups:
        return 1.0
    
    # Calculate average satisfaction of vulnerable groups
    total_satisfaction = 0
    for agent_id in weak_groups:
        allocation = proposal.get(agent_id, {})
        needs = survival_needs.get(agent_id, {})
        if needs:
            satisfaction = sum(
                min(allocation.get(resource, 0) / need, 1.0)
                for resource, need in needs.items() if need > 0
            ) / len(needs)
            total_satisfaction += satisfaction
    
    return total_satisfaction / len(weak_groups)

def calculate_allocation_balance(proposal: Dict[int, Dict[str, float]]) -> float:
    """Calculate allocation balance"""
    if not proposal:
        return 1.0
    
    # Calculate coefficient of variation for allocations
    allocations = list(proposal.values())
    totals = [sum(allocation.values()) for allocation in allocations]
    mean_total = sum(totals) / len(totals)
    
    if mean_total == 0:
        return 1.0
    
    std_dev = (sum((total - mean_total) ** 2 for total in totals) / len(totals)) ** 0.5
    coefficient_of_variation = std_dev / mean_total
    
    # Smaller coefficient of variation means better balance
    return max(0, 1 - coefficient_of_variation)

def check_consensus(
    evaluations: Dict[int, Dict[int, Dict[str, Any]]],
    agents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Check if consensus is reached"""
    consensus_threshold = 0.8  # 80% of agents agree
    
    for proposer_id in evaluations[list(evaluations.keys())[0]].keys():
        agreements = 0
        total_evaluators = 0
        
        for evaluator_id, evaluation in evaluations.items():
            if proposer_id in evaluation:
                total_evaluators += 1
                if evaluation[proposer_id]["agreement"]:
                    agreements += 1
        
        consensus_ratio = agreements / total_evaluators if total_evaluators > 0 else 0
        
        if consensus_ratio >= consensus_threshold:
            return {
                "consensus_reached": True,
                "agreed_proposal": proposer_id
            }
    
    return {
        "consensus_reached": False,
        "agreed_proposal": None
    }

def generate_negotiation_proposals(
    current_proposals: Dict[int, Dict[int, Dict[str, float]]],
    evaluations: Dict[int, Dict[int, Dict[str, Any]]],
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    negotiation_round: int
) -> Dict[int, Dict[int, Dict[str, float]]]:
    """Generate New Negotiation Proposal"""
    new_proposals = {}
    
    for agent in agents:
        agent_id = agent["id"]
        value_type = agent["value_type"]
        
        # Analyze feedback on current proposal
        feedback = analyze_proposal_feedback(agent_id, evaluations)
        
        # Adjust proposal based on feedback
        adjusted_proposal = adjust_proposal_by_feedback(
            current_proposals[agent_id], feedback, agent, 
            total_resources, survival_needs, negotiation_round
        )
        
        new_proposals[agent_id] = adjusted_proposal
    
    return new_proposals

def analyze_proposal_feedback(
    agent_id: int,
    evaluations: Dict[int, Dict[int, Dict[str, Any]]]
) -> Dict[str, Any]:
    """Analyze Proposal Feedback"""
    feedback = {
        "average_score": 0,
        "agreement_rate": 0,
        "criticisms": [],
        "suggestions": []
    }
    
    scores = []
    agreements = 0
    total_evaluators = 0
    
    for evaluator_id, evaluation in evaluations.items():
        if evaluator_id != agent_id and agent_id in evaluation:
            score = evaluation[agent_id]["score"]
            scores.append(score)
            total_evaluators += 1
            
            if evaluation[agent_id]["agreement"]:
                agreements += 1
    
    if scores:
        feedback["average_score"] = sum(scores) / len(scores)
        feedback["agreement_rate"] = agreements / total_evaluators if total_evaluators > 0 else 0
    
    return feedback

def adjust_proposal_by_feedback(
    current_proposal: Dict[int, Dict[str, float]],
    feedback: Dict[str, Any],
    agent: Dict[str, Any],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    negotiation_round: int
) -> Dict[int, Dict[str, float]]:
    """Adjust proposal based on feedback"""
    value_type = agent["value_type"]
    adjustment_factor = 1.0
    
    # Adjust strategy based on feedback
    if feedback["average_score"] < 2.5:
        # Low rating,Needs Adjustment
        adjustment_factor = 0.8
    elif feedback["average_score"] > 4.0:
        # Higher ratings,Slightly persistent
        adjustment_factor = 1.1
    
    # Align strategy with values
    if value_type == "altruistic":
        # It's easier for altruists to give in
        adjustment_factor *= 0.9
    elif value_type == "merit_based":
        # Contribution oriented people are relatively persistent
        adjustment_factor *= 1.05
    elif value_type == "pragmatic":
        # Pragmatist Flexibility Based on Feedback
        if feedback["agreement_rate"] < 0.5:
            adjustment_factor *= 0.85
        else:
            adjustment_factor *= 1.0
    
    # Apply Adjustments
    adjusted_proposal = {}
    for agent_id, allocation in current_proposal.items():
        adjusted_proposal[agent_id] = {}
        for resource_name, amount in allocation.items():
            adjusted_amount = amount * adjustment_factor
            adjusted_proposal[agent_id][resource_name] = adjusted_amount
    
    return adjusted_proposal

def voting_mechanism(
    proposals: Dict[int, Dict[int, Dict[str, float]]],
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]]
) -> Dict[int, Dict[str, float]]:
    """Voting Mechanism
    
    When negotiation fails to reach consensus,Use Voting to Decide on Final Plan
    """
    # Calculate voting weight for each proposal
    proposal_scores = {}
    
    for proposer_id, proposal in proposals.items():
        total_score = 0
        total_weight = 0
        
        for agent in agents:
            agent_id = agent["id"]
            value_type = agent["value_type"]
            
            # Voting weight based on values
            weight = get_voting_weight(value_type)
            
            # Evaluate Proposal
            score = evaluate_proposal_by_values(
                proposal, agent, total_resources, survival_needs, agents
            )
            
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            proposal_scores[proposer_id] = total_score / total_weight
    
    # Select the proposal with the highest score
    if proposal_scores:
        best_proposer = max(proposal_scores.keys(), key=lambda x: proposal_scores[x])
        return proposals[best_proposer]
    
    # If there is no valid proposal,Use Equal Distribution
    return equal_distribution(total_resources, agents)

def get_voting_weight(value_type: str) -> float:
    """Get voting weight"""
    weights = {
        "egalitarian": 1.0,
        "needs_based": 1.0,
        "merit_based": 1.0,
        "altruistic": 1.0,
        "pragmatic": 1.2  # Pragmatists have slightly higher weight as they are better at balancing
    }
    return weights.get(value_type, 1.0)


def integerize_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    distribution_result: Dict[int, Dict[str, float]],
    survival_needs: Dict[int, Dict[str, float]] = None,
    enforce_min_survival: bool = False,
    decimal_places: int = 2
) -> Dict[int, Dict[str, float]]:
    """Round distribution results to specified decimal places while maintaining total consistency
    
    Args:
        total_resources: Total available resources
        agents: List of agent dictionaries
        distribution_result: Raw distribution result (may have many decimal places)
        survival_needs: Minimum survival needs for each agent
        enforce_min_survival: Whether to enforce minimum survival floor
        decimal_places: Number of decimal places to keep (default: 2)
        
    Algorithm:
        1. Round each allocation to specified decimal places
        2. Calculate total difference from target
        3. Adjust allocations with largest fractional parts to match total exactly
    """
    if not agents or not distribution_result:
        return distribution_result
    
    grain_total = float(total_resources.get("grain", 0.0))
    agent_ids = [agent["id"] for agent in agents]
    
    # Get raw values
    real = {aid: float(distribution_result.get(aid, {}).get("grain", 0.0)) for aid in agent_ids}
    
    # Calculate minimum needs if enforcing survival
    min_need = {}
    if enforce_min_survival and survival_needs:
        for aid in agent_ids:
            need = float(survival_needs.get(aid, {}).get("grain", 0.0))
            min_need[aid] = round(need, decimal_places) if need > 0 else 0.0
    else:
        min_need = {aid: 0.0 for aid in agent_ids}
    
    # Initial rounding to decimal places
    multiplier = 10 ** decimal_places
    rounded = {}
    for aid in agent_ids:
        value = real[aid]
        # Enforce minimum if needed
        if enforce_min_survival and value < min_need[aid]:
            value = min_need[aid]
        rounded[aid] = round(value, decimal_places)
    
    # Calculate target total (also rounded)
    target_total = round(sum(real.values()), decimal_places)
    current_total = round(sum(rounded.values()), decimal_places)
    
    # Adjust for rounding errors to match target exactly
    diff = round(target_total - current_total, decimal_places)
    
    if abs(diff) > 0:
        # Sort by fractional part after rounding (to distribute adjustment fairly)
        # For each agent, calculate what we "lost" or "gained" in rounding
        rounding_remainder = {}
        for aid in agent_ids:
            original = real[aid]
            rounded_val = rounded[aid]
            rounding_remainder[aid] = original - rounded_val
        
        # Adjustment step size
        step = round(1.0 / multiplier, decimal_places)
        
        if diff > 0:
            # Need to add more (target > current)
            # Give to those who lost most in rounding (most negative remainder)
            sorted_aids = sorted(agent_ids, key=lambda a: rounding_remainder[a])
            adjustments_needed = int(round(abs(diff) / step))
            
            for i in range(min(adjustments_needed, len(sorted_aids))):
                aid = sorted_aids[i]
                rounded[aid] = round(rounded[aid] + step, decimal_places)
        else:
            # Need to subtract (target < current)
            # Take from those who gained most in rounding (most positive remainder)
            sorted_aids = sorted(agent_ids, key=lambda a: rounding_remainder[a], reverse=True)
            adjustments_needed = int(round(abs(diff) / step))
            
            for i in range(min(adjustments_needed, len(sorted_aids))):
                aid = sorted_aids[i]
                # Don't go below minimum need
                new_val = round(rounded[aid] - step, decimal_places)
                if new_val >= min_need[aid]:
                    rounded[aid] = new_val
    
    # Assemble final result
    out = {}
    for aid in agent_ids:
        out[aid] = dict(distribution_result.get(aid, {}))
        out[aid]["grain"] = rounded[aid]
    
    return out


# ========================================================================================
# LLMDriven on-demand allocation
# ========================================================================================

def llm_driven_needs_based_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    previous_distribution: Dict[int, Dict[str, float]] = None,
    previous_evaluations: List[Dict] = None
) -> Dict[int, Dict[str, float]]:
    """
    LLMDriven on-demand allocation mechanism(Simple version - Unconstrained)
    
    Process:
    1. Each family passesLLMSelf-declaration of requirements(Include Demand,Reason,Minimum Acceptable Quantity)
    2. Summarize all declarations
    3. If the total demand<=Total resources:Satisfy all declarations
       If the total demand>Total resources:Proportional reduction
    
    Features:
    - No external constraints:agentsSelf-declaration,Is prone to strategic exaggeration
    - Reflect"The Tragedy of the Commons":Overreporting leads to wasted resources and inefficiencies
    - For comparative studies:Demonstrate idealistic but out-of-control distribution mechanisms
    
    Parameter:
        total_resources: Total Resources Dictionary
        agents: Proxy List
        survival_needs: Survival Needs Dictionary(Used to provide information)
        round_number: Current number of rounds
        previous_distribution: Previous Round Allocation Result
        previous_evaluations: Results from the previous round
    
    Back:
        Assignment Result Dictionary
    """
    import json
    import re
        
    # SettingsDeepSeekClient
    client = get_llm_client()
    
    if not agents or not survival_needs:
        return {}
    
    distribution_result = {}
    
    # Calculate the community as a whole
    total_members = sum(agent.get("members", 0) for agent in agents)
    total_labor = sum(agent.get("labor_force", 0) for agent in agents)
    
    print("\n" + "="*60)
    print("🆕 Needs-Based Distribution (LLM-Driven - Simple Version)")
    print("="*60)
    
    for resource_name, total_amount in total_resources.items():
        print(f"\nResource Type: {resource_name}")
        print(f"  Total Resources: {total_amount:.1f} units")
        print(f"  Community Total Population: {total_members} people")
        print(f"  Community Total Labor: {total_labor} people")
        
        # Phase 1: Collect family needs reports
        print(f"\n{'─'*60}")
        print("📋 Phase 1: Collect Needs Reports")
        print(f"{'─'*60}")
        
        family_reports = {}
        
        for agent in agents:
            agent_id = agent["id"]
            family_name = agent.get("family_name", f"Family{agent_id}")
            members = agent.get("members", 0)
            labor_force = agent.get("labor_force", 0)
            value_type = agent.get("value_type", "pragmatic")
            
            # Acquire Survival Needs
            agent_survival_needs = survival_needs.get(agent_id, {})
            survival_amount = agent_survival_needs.get(resource_name, 0)
            
            # Get previous round
            prev_allocation = None
            prev_per_capita = None
            prev_satisfaction = None
            
            if previous_distribution and agent_id in previous_distribution:
                prev_allocation = previous_distribution[agent_id].get(resource_name, 0)
                prev_per_capita = prev_allocation / members if members > 0 else 0
            
            if previous_evaluations:
                for eval_item in previous_evaluations:
                    if eval_item.get("agent_id") == agent_id:
                        prev_satisfaction = eval_item.get("fairness_score")
                        break
            
            # PassLLMGet demand declarations
            report = get_family_need_report_via_llm(
                family_name=family_name,
                members=members,
                labor_force=labor_force,
                value_type=value_type,
                survival_amount=survival_amount,
                total_resources=total_amount,
                total_members=total_members,
                round_number=round_number,
                prev_allocation=prev_allocation,
                prev_per_capita=prev_per_capita,
                prev_satisfaction=prev_satisfaction
            )
            
            family_reports[agent_id] = report
            
            print(f"\n{family_name} Family ({members} people, {labor_force} laborers, {get_value_type_name(value_type)}):")
            print(f"  💬 Reported Needs: {report['requested_amount']:.1f} units")
            print(f"  📝 Reason: {report['reason']}")
            print(f"  ⚖️ Minimum Acceptable: {report['minimum_acceptable']:.1f} units")
            if report.get('reasoning_process'):
                print(f"  🤔 Decision Process: {report['reasoning_process']}")
        
        # Phase 2: Aggregate needs and allocate
        print(f"\n{'─'*60}")
        print("📊 Phase 2: Aggregate Needs and Decide Allocation")
        print(f"{'─'*60}")
        
        total_requested = sum(r['requested_amount'] for r in family_reports.values())
        total_minimum = sum(r['minimum_acceptable'] for r in family_reports.values())
        
        print(f"\nTotal Reported Needs: {total_requested:.1f} units")
        print(f"Total Minimum Needs: {total_minimum:.1f} units")
        print(f"Actually Available: {total_amount:.1f} units")
        
        if total_requested <= total_amount:
            # Resources sufficient, meet all reports
            print(f"\n✅ Resources Sufficient (demand/resource = {total_requested/total_amount:.1%})")
            print(f"   Meeting all families' reported needs")
            
            for agent_id, report in family_reports.items():
                if agent_id not in distribution_result:
                    distribution_result[agent_id] = {}
                distribution_result[agent_id][resource_name] = report['requested_amount']
        
        elif total_minimum <= total_amount < total_requested:
            # Resources between minimum needs and reported needs
            gap = total_requested - total_amount
            gap_ratio = gap / total_requested
            
            print(f"\n⚠️ Resources Slightly Tight (gap {gap:.1f} units, {gap_ratio:.1%})")
            print(f"   Allocating proportionally within [minimum-reported] range")
            
            # Proportionally in[Lowest value, Declared value]Interval Allocation
            for agent_id, report in family_reports.items():
                min_val = report['minimum_acceptable']
                max_val = report['requested_amount']
                range_size = max_val - min_val
                
                # Calculate the household's share of the range
                total_range = sum(r['requested_amount'] - r['minimum_acceptable'] 
                                 for r in family_reports.values())
                
                if total_range > 0:
                    # Distribute remaining resources proportionally by interval size
                    remaining = total_amount - total_minimum
                    allocation = min_val + (range_size / total_range) * remaining
                else:
                    # If all households have a minimum value=Declared value,Prorated
                    proportion = max_val / total_requested
                    allocation = proportion * total_amount
                
                if agent_id not in distribution_result:
                    distribution_result[agent_id] = {}
                distribution_result[agent_id][resource_name] = allocation
        
        else:
            # Resources severely insufficient, cannot meet even minimum needs
            gap = total_requested - total_amount
            gap_ratio = gap / total_requested
            min_gap = total_minimum - total_amount
            
            print(f"\n🚨 Resources Severely Insufficient (gap {gap:.1f} units, {gap_ratio:.1%})")
            print(f"   Cannot meet even minimum needs (minimum gap {min_gap:.1f})")
            print(f"   Reducing by reported proportion")
            
            # Reduce by reported proportion
            for agent_id, report in family_reports.items():
                proportion = report['requested_amount'] / total_requested
                allocation = proportion * total_amount
                
                if agent_id not in distribution_result:
                    distribution_result[agent_id] = {}
                distribution_result[agent_id][resource_name] = allocation
        
        # Display final allocation results
        print(f"\n{'─'*60}")
        print("✅ Final Allocation Results")
        print(f"{'─'*60}")
        
        for agent in agents:
            agent_id = agent["id"]
            family_name = agent.get("family_name", f"Family{agent_id}")
            members = agent.get("members", 0)
            
            allocated = distribution_result[agent_id][resource_name]
            requested = family_reports[agent_id]['requested_amount']
            per_capita = allocated / members if members > 0 else 0
            fulfillment = allocated / requested if requested > 0 else 0
            
            print(f"\n{family_name} Family ({members} people):")
            print(f"  Reported: {requested:.1f} → Actual Allocation: {allocated:.1f} (Fulfillment: {fulfillment:.1%})")
            print(f"  Per Capita: {per_capita:.2f} units/person")
    
    print("\n" + "="*60)
    print("✅ LLM-Driven Needs-Based Distribution Complete")
    print("="*60 + "\n")
    
    # Round to specified decimal places
    return integerize_distribution(
        total_resources, agents, distribution_result,
        survival_needs=survival_needs,
        enforce_min_survival=True,
        decimal_places=DECIMAL_PLACES
    )


def get_family_need_report_via_llm(
    family_name: str,
    members: int,
    labor_force: int,
    value_type: str,
    survival_amount: float,
    total_resources: float,
    total_members: int,
    round_number: int = 1,
    prev_allocation: float = None,
    prev_per_capita: float = None,
    prev_satisfaction: float = None
) -> Dict[str, Any]:
    """
    Get family's need declaration via LLM
    
    Returns:
    {
        "requested_amount": float,
        "reason": str,
        "minimum_acceptable": float,
        "reasoning_process": str
    }
    """
    import json
    import re
    
    # Setup DeepSeek client
    client = get_llm_client()
    
    # Get value type description
    value_desc = get_value_type_description(value_type)
    
    # Build prompt
    prompt = f"""You are the representative of the {family_name} family, and need to declare your resource needs to the community for this round.

[Family Basic Information]
- Family members: {members} people
- Labor force: {labor_force} people
- Labor density: {labor_force/members:.1%} (average labor per person)
- Value orientation: {value_desc}

[Survival Needs]
- Basic rations: {survival_amount:.1f} units (minimum requirement to sustain {members} people's basic life)

[Community Resource Situation]
- Resources available for distribution this round: {total_resources:.1f} units
- Total community population: {total_members} people
- Your family's population share: {members/total_members:.1%}
- If distributed equally, your family would receive: {total_resources * members / total_members:.1f} units (per capita {total_resources/total_members:.2f})
"""

    # Add historical information (if available)
    if prev_allocation is not None:
        prompt += f"""
[Previous Round Situation]
- Previous allocation: {prev_allocation:.1f} units
- Previous per capita: {prev_per_capita:.2f} units/person
"""
        if prev_satisfaction is not None:
            prompt += f"- Your satisfaction rating: {prev_satisfaction:.1f} points (1-5 scale)\n"

    prompt += f"""
[Distribution Principles]
This round uses "needs-based distribution" mechanism:
- Each family declares their needs autonomously
- If total needs <= total resources, all declarations are satisfied
- If total needs > total resources, proportional reduction applies

[Declaration Requirements]
Please declare your needs for this round based on your family situation and values. Consider:
1. Basic living needs of family population
2. Production capacity needs of labor force
3. Your value orientation ({value_desc})
4. Abundance level of community resources
5. Previous round's allocation and satisfaction (if applicable)


Please respond in JSON format (return only JSON, no other text):
{{
    "requested_amount": number (amount of resources you wish to receive),
    "reason": "reason for needs (2-3 sentences explaining why you need this much)",
    "minimum_acceptable": number (if resources are tight, the minimum acceptable amount),
    "reasoning_process": "decision process (briefly explain how you made this decision)"
}}
"""

    # Call LLM
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Call DeepSeek API
            completion = client.chat.completions.create(
                model=get_model_name(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            response = completion.choices[0].message.content
            
            # Parse JSON
            report = parse_json_from_response(response)
            
            # Validate and fix
            report = validate_and_fix_report(
                report, members, labor_force, survival_amount, 
                total_resources, total_members
            )
            
            return report
            
        except Exception as e:
            print(f"  ⚠️ LLM call failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # Last attempt failed, use default values
                print(f"  Using default declaration strategy")
                return get_default_need_report(
                    members, labor_force, value_type, 
                    survival_amount, total_resources, total_members
                )


def parse_json_from_response(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response"""
    import json
    import re
    
    # Try direct parsing
    try:
        return json.loads(response)
    except:
        pass
    
    # Try extracting JSON code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Try extracting content within braces
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    raise ValueError(f"Unable to parse JSON from response: {response[:200]}")


def validate_and_fix_report(
    report: Dict[str, Any],
    members: int,
    labor_force: int,
    survival_amount: float,
    total_resources: float,
    total_members: int
) -> Dict[str, Any]:
    """Validate and fix need declaration"""
    
    # Extract values
    requested = float(report.get('requested_amount', 0))
    minimum = float(report.get('minimum_acceptable', 0))
    reason = str(report.get('reason', ''))
    reasoning = str(report.get('reasoning_process', ''))
    
    # Calculate reasonable range
    avg_per_family = total_resources / (total_members / (members if members > 0 else 1))
    min_survival = survival_amount * 0.8
    max_reasonable = avg_per_family * 3
    
    # Fix requested amount
    if requested <= 0 or requested > max_reasonable:
        requested = min(members * (total_resources / total_members), max_reasonable)
    
    # Fix minimum value
    if minimum < min_survival:
        minimum = min_survival
    if minimum > requested:
        minimum = requested
    
    return {
        'requested_amount': requested,
        'reason': reason if reason else f"Basic needs for {members}-person family",
        'minimum_acceptable': minimum,
        'reasoning_process': reasoning
    }


def get_default_need_report(
    members: int,
    labor_force: int,
    value_type: str,
    survival_amount: float,
    total_resources: float,
    total_members: int
) -> Dict[str, Any]:
    """
    Generate need declaration using default strategy when LLM call fails
    """
    
    # Base need: by population proportion
    base_request = total_resources * (members / total_members)
    
    # Adjust based on value type
    if value_type == "egalitarian":
        # Egalitarian: close to per capita average
        requested = base_request
        minimum = survival_amount
        reason = f"Hope to receive fair per capita share ({members} people)"
        
    elif value_type == "needs_based":
        # Needs-based: by population needs
        requested = max(base_request, survival_amount * 1.3)
        minimum = survival_amount
        reason = f"Have {members} people to support, hope to ensure basic living"
        
    elif value_type == "merit_based":
        # Merit-based: by labor contribution
        labor_ratio = labor_force / (total_members / len([1]))  # Simplified calculation
        requested = base_request * (1 + labor_ratio * 0.3)
        minimum = survival_amount * 1.1
        reason = f"Have {labor_force} laborers, hope to receive resources based on contribution"
        
    elif value_type == "altruistic":
        # Altruistic: moderate declaration
        requested = base_request * 0.85
        minimum = survival_amount * 0.9
        reason = f"Willing to give up some resources for other families in the community"
        
    else:  # pragmatic
        # Pragmatic: flexible declaration based on resource situation
        resource_abundance = total_resources / (total_members * 4)  # Assume 4 per capita as standard
        if resource_abundance > 1.2:
            requested = base_request * 1.1
        elif resource_abundance < 0.8:
            requested = base_request * 0.9
        else:
            requested = base_request
        minimum = survival_amount
        reason = f"Flexible declaration based on resource situation"
    
    return {
        'requested_amount': requested,
        'reason': reason,
        'minimum_acceptable': minimum,
        'reasoning_process': f"Default strategy based on {get_value_type_name(value_type)} values"
    }


def get_value_type_description(value_type: str) -> str:
    """Get detailed description of value type"""
    descriptions = {
        "egalitarian": "Egalitarian - Believes everyone is equal, resources should be distributed fairly, opposes privilege and excessive inequality",
        "needs_based": "Needs-based - Believes distribution should be based on actual needs, caring for families with more members and heavier burdens",
        "merit_based": "Merit-based - Believes in more work more reward, distribute resources based on labor contribution",
        "altruistic": "Altruistic - Willing to consider others, proactively care for vulnerable families",
        "pragmatic": "Pragmatic - Flexible and practical, adjusts strategy based on actual situation"
    }
    return descriptions.get(value_type, "Pragmatic")


def get_value_type_name(value_type: str) -> str:
    """Get value type name"""
    names = {
        "egalitarian": "Egalitarian",
        "needs_based": "Needs-based",
        "merit_based": "Merit-based",
        "altruistic": "Altruistic",
        "pragmatic": "Pragmatic"
    }
    return names.get(value_type, "Pragmatic")


def dialogue_based_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    experiment_id: str = None,
    return_metadata: bool = True,
    **kwargs
) -> Any:
    """Dialogue-driven negotiation distribution mechanism (wrapper function)
    
    Agents reach consensus through 4 rounds of dialogue:
    1. State expectations
    2. Respond to each other
    3. Seek consensus
    4. Build and confirm
    
    Args:
        total_resources: Total resources dictionary
        agents: Agent list
        survival_needs: Survival needs dictionary
        round_number: Current round number
        experiment_id: Experiment ID
        return_metadata: Whether to return metadata
        
    Returns:
        If return_metadata=True: (final_allocation, metadata)
        If return_metadata=False: final_allocation
    """
    print("\n🗣️  Using dialogue-driven negotiation distribution mechanism")
    
    # Call implementation
    final_allocation, metadata = dialogue_negotiation_impl(
        total_resources=total_resources,
        agents=agents,
        survival_needs=survival_needs,
        round_number=round_number
    )
    
    if return_metadata:
        return final_allocation, metadata
    else:
        return final_allocation
