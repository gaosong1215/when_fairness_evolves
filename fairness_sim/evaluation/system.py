"""
Evaluation System Module - Calculate statistical metrics for resource allocation and collect agent subjective evaluations
"""
from fairness_sim.llm_client import get_llm_client, get_model_name
from typing import List, Dict, Any, Tuple
import time
import random
import math
import re
import json
from fairness_sim.logging.llm_interaction import get_logger

# Setup DeepSeek client
client = get_llm_client()


_RESPONSE_STYLES = (
    "Begin with the concrete effect on your household, then evaluate the rule behind it.",
    "Begin with one comparison to another household, then state the principle that comparison tests.",
    "Organize the reflection around a tension or tradeoff you noticed in this round.",
    "Use a counterfactual: explain what would have changed your judgment by one score point.",
    "State a short verdict first, then support it with two different kinds of evidence.",
    "Contrast the immediate household outcome with the likely effect over future rounds.",
    "Frame the response around a practical question the community should answer before the next vote.",
    "Separate outcome fairness from process fairness and explain which mattered more this round.",
    "Test the allocation against a tighter-resource scenario before giving your conclusion.",
    "Lead with the strongest evidence against your initial instinct, then explain your final position.",
    "Describe what remains uncertain before describing what the numbers establish clearly.",
    "Build from observation to principle: allocation, household consequence, then fairness rule.",
)


def _response_style(agent_id: int, round_number: int) -> str:
    """Choose varied but reproducible reflection guidance for an agent-round pair."""
    index = (agent_id * 7 + round_number * 11) % len(_RESPONSE_STYLES)
    return _RESPONSE_STYLES[index]


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _variance(values: List[float]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    return sum((value - mean_value) ** 2 for value in values) / len(values)


def _std_dev(values: List[float]) -> float:
    return math.sqrt(_variance(values))


def calculate_statistics(distribution_result: Dict[int, Dict[str, float]], agents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistical metrics for resource allocation
    
    Args:
        distribution_result: Distribution result dictionary, key is agent ID, value is allocated resources dictionary
        agents: Agent list
        
    Returns:
        Statistical metrics dictionary, including variance, standard deviation, Gini coefficient, etc.
    """
    # Calculate statistical metrics for each resource separately
    stats = {}
    all_resources = set()
    
    # Collect all resource types
    for agent_id, resources in distribution_result.items():
        all_resources.update(resources.keys())
    
    # Calculate statistical metrics for each resource
    for resource_name in all_resources:
        # Extract distribution results for this resource
        resource_distribution = [
            distribution_result.get(agent["id"], {}).get(resource_name, 0)
            for agent in agents
        ]
        
        # Calculate basic statistics
        mean_value = _mean(resource_distribution)
        variance = _variance(resource_distribution)
        std_dev = _std_dev(resource_distribution)
        
        # Calculate Gini coefficient
        gini = calculate_gini_coefficient(resource_distribution)
        
        # Store statistical results for this resource
        stats[resource_name] = {
            "mean": mean_value,
            "variance": variance,
            "std_dev": std_dev,
            "gini": gini
        }
    
    # Calculate statistical metrics for total resources
    total_resources = [
        sum(distribution_result.get(agent["id"], {}).values())
        for agent in agents
    ]
    
    # Basic statistics for total resources
    stats["total"] = {
        "mean": _mean(total_resources),
        "variance": _variance(total_resources),
        "std_dev": _std_dev(total_resources),
        "gini": calculate_gini_coefficient(total_resources)
    }
    
    return stats

def _compute_statistics_for_values(values: Dict[int, Dict[str, float]], agents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generic statistics: calculate mean/variance/std/Gini (including total) for any agent→resource→value mapping."""
    stats = {}
    all_resources = set()
    for agent_id, res in values.items():
        all_resources.update(res.keys())
    for resource_name in all_resources:
        arr = [values.get(agent["id"], {}).get(resource_name, 0.0) for agent in agents]
        mean_value = _mean(arr)
        variance = _variance(arr)
        std_dev = _std_dev(arr)
        gini = calculate_gini_coefficient(arr)
        stats[resource_name] = {
            "mean": mean_value,
            "variance": variance,
            "std_dev": std_dev,
            "gini": gini
        }
    total_values = [sum(values.get(agent["id"], {}).values()) for agent in agents]
    stats["total"] = {
        "mean": _mean(total_values),
        "variance": _variance(total_values),
        "std_dev": _std_dev(total_values),
        "gini": calculate_gini_coefficient(total_values)
    }
    return stats

def calculate_gini_coefficient(distribution: List[float]) -> float:
    """Calculate Gini coefficient
    
    Args:
        distribution: Resource distribution list
        
    Returns:
        Gini coefficient, 0 means perfect equality, 1 means perfect inequality
    """
    if not distribution or sum(distribution) == 0:
        return 0
    
    # Sort distribution results
    sorted_dist = sorted(distribution)
    n = len(sorted_dist)
    
    # Calculate Gini coefficient
    numerator = sum((i+1) * sorted_dist[i] for i in range(n))
    denominator = sum(sorted_dist) * n
    
    if denominator == 0:
        return 0
    
    return (2 * numerator / denominator) - (n + 1) / n

def get_similar_families(
    target_agent: Dict[str, Any],
    all_agents: List[Dict[str, Any]],
    distribution_result: Dict[int, Dict[str, float]],
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """Filter similar-sized families for relevant comparison
    
    Args:
        target_agent: The agent to compare with
        all_agents: List of all agents
        distribution_result: Distribution results for calculating allocations
        max_results: Maximum number of similar families to return (default: 5)
        
    Returns:
        List of similar family data dictionaries, sorted by similarity
    """
    target_members = target_agent['members']
    target_labor = target_agent['labor_force']
    target_id = target_agent['id']
    
    similar = []
    for agent in all_agents:
        if agent['id'] == target_id:
            continue  # Skip self
        
        member_diff = abs(agent['members'] - target_members)
        labor_diff = abs(agent['labor_force'] - target_labor)
        
        # Filter criteria: ±2 members OR ±1 workers
        if member_diff <= 2 or labor_diff <= 1:
            # Calculate allocation info
            agent_resources = distribution_result.get(agent['id'], {})
            total_received = sum(agent_resources.values())
            per_capita = total_received / agent['members'] if agent['members'] > 0 else 0
            per_labor = total_received / agent['labor_force'] if agent['labor_force'] > 0 else 0
            
            similar.append({
                'agent': agent,
                'total_received': total_received,
                'per_capita': per_capita,
                'per_labor': per_labor,
                'similarity_score': -(member_diff + labor_diff * 2)  # Labor difference weighted higher
            })
    
    # Sort by similarity (higher score = more similar)
    similar.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar[:max_results]

def get_agent_fairness_evaluation(
    agent: Dict[str, Any],
    distribution_result: Dict[int, Dict[str, float]],
    total_resources: Dict[str, float],
    round_number: int,
    distribution_method: str,
    agents: List[Dict[str, Any]] = None,
    dialogue_results: Dict[str, Any] = None,  # Dialogue results (including evolved understanding)
    memory_module = None,  # 🆕 Historical memory module (Phase 1 addition)
    negotiation_metadata: Dict[str, Any] = None  # 🆕 4-phase negotiation metadata
) -> Dict[str, Any]:
    """Get agent's fairness evaluation of distribution results
    
    Args:
        agent: Agent data
        distribution_result: Distribution results
        total_resources: Total resources
        round_number: Current round number
        distribution_method: Distribution method name
        agents: All agents list, used to provide other family information
        dialogue_results: Dialogue results, including initial_understanding and final_understanding
        memory_module: Historical memory module, used to provide historical information
        
    Returns:
        Agent evaluation result dictionary
    """
    agent_id = agent["id"]
    agent_resources = distribution_result.get(agent_id, {})
    agent_value = agent["value_type"]
    
    # Calculate system-level statistical data
    system_stats = {}
    total_members = sum(a["members"] for a in agents) if agents else 0
    total_labor = sum(a["labor_force"] for a in agents) if agents else 0
    
    # Calculate family's total resources
    agent_total_resources = sum(agent_resources.values())
    
    # Calculate system total resources and per capita/per labor resources
    system_total_resources = sum(total_resources.values())
    per_capita_system = system_total_resources / total_members if total_members > 0 else 0
    per_labor_system = system_total_resources / total_labor if total_labor > 0 else 0
    
    # Calculate this family's per capita and per labor resources
    agent_per_capita = agent_total_resources / agent["members"] if agent["members"] > 0 else 0
    agent_per_labor = agent_total_resources / agent["labor_force"] if agent["labor_force"] > 0 else 0
    
    # Calculate percentage of total resources this family received
    resource_percentage = (agent_total_resources / system_total_resources * 100) if system_total_resources > 0 else 0
    
    # Calculate this family's member and labor percentages
    member_percentage = (agent["members"] / total_members * 100) if total_members > 0 else 0
    labor_percentage = (agent["labor_force"] / total_labor * 100) if total_labor > 0 else 0
    
    # 🆕 Prepare similar families' distribution information for focused comparison
    other_families_info = ""
    family_comparative_data = []
    
    if agents:
        # Collect all family data for ranking calculation
        for other_agent in agents:
            other_id = other_agent["id"]
            other_resources = distribution_result.get(other_id, {})
            other_total_received = sum(other_resources.values())
            
            # Calculate per capita and per labor resources
            other_per_capita = other_total_received / other_agent["members"] if other_agent["members"] > 0 else 0
            other_per_labor = other_total_received / other_agent["labor_force"] if other_agent["labor_force"] > 0 else 0
            
            # Save data to list
            family_data = {
                "id": other_id,
                "name": other_agent["family_name"],
                "is_self": other_id == agent_id,
                "members": other_agent["members"],
                "labor": other_agent["labor_force"],
                "total_resources": other_total_received,
                "per_capita": other_per_capita,
                "per_labor": other_per_labor,
                "value_type": other_agent["value_type"]
            }
            family_comparative_data.append(family_data)
        
        # 🆕 Show all families in concise format (1 line per family)
        other_families_info = "[All Families Distribution]\n"
        
        # Sort by family size (members) for easier scanning
        sorted_families = sorted(family_comparative_data, key=lambda x: (x['members'], x['labor']))
        
        for family in sorted_families:
            fam_name = family['name']
            fam_members = family['members']
            fam_labor = family['labor']
            fam_total = family['total_resources']
            fam_per_capita = family['per_capita']
            fam_per_labor = family['per_labor']
            
            # Mark current agent with "← YOU"
            marker = " ← YOU" if family['is_self'] else ""
            
            other_families_info += f"- {fam_name} ({fam_members}p/{fam_labor}w): "
            other_families_info += f"Total {fam_total:.2f}, Per capita {fam_per_capita:.2f}, Per labor {fam_per_labor:.2f}{marker}\n"
    
    # Calculate family rankings on different metrics
    rankings = {}
    if family_comparative_data:
        # Sort by total resources
        sorted_by_total = sorted(family_comparative_data, key=lambda x: x["total_resources"], reverse=True)
        rankings["total_rank"] = next(i+1 for i, f in enumerate(sorted_by_total) if f["id"] == agent_id)
        
        # Sort by per capita resources
        sorted_by_capita = sorted(family_comparative_data, key=lambda x: x["per_capita"], reverse=True)
        rankings["per_capita_rank"] = next(i+1 for i, f in enumerate(sorted_by_capita) if f["id"] == agent_id)
        
        # Sort by per labor resources
        sorted_by_labor = sorted(family_comparative_data, key=lambda x: x["per_labor"], reverse=True)
        rankings["per_labor_rank"] = next(i+1 for i, f in enumerate(sorted_by_labor) if f["id"] == agent_id)
    
    # 🆕 Extract evolved fairness understanding (if exists)
    evolved_understanding = None
    initial_understanding = None
    absorbed_elements = []
    
    if dialogue_results:
        # Check if dialogue_results is dict (original dialogue mechanism) or list (discussion mechanism)
        if isinstance(dialogue_results, dict):
            # Original dialogue mechanism format
            # Get this agent's understanding from final_understanding dictionary
            final_understandings = dialogue_results.get("final_understanding", {})
            initial_understandings = dialogue_results.get("initial_understanding", {})
            
            # Find this agent's understanding (might use family_name or agent_id as key)
            agent_name = agent["family_name"]
            for key, value in final_understandings.items():
                if str(agent_id) in str(key) or agent_name in str(key):
                    evolved_understanding = value
                    break
            
            # Similarly find initial understanding
            for key, value in initial_understandings.items():
                if str(agent_id) in str(key) or agent_name in str(key):
                    initial_understanding = value
                    break
            
            # Extract absorbed views (if plasticity_analysis exists)
            plasticity_analysis = dialogue_results.get("plasticity_analysis", {})
            if plasticity_analysis:
                agent_plasticity = plasticity_analysis.get("agent_details", {})
                for agent_detail in agent_plasticity.values():
                    if agent_detail.get("agent_id") == agent_id or agent_detail.get("name") == agent_name:
                        absorbed_elements = agent_detail.get("absorbed_elements", [])[:3]  # Take first 3
                        break
        elif isinstance(dialogue_results, list):
            # Discussion mechanism format (list of discussion records)
            # No evolved understanding tracking for discussion mechanism
            # Just skip the evolution context
            pass
    
    # 🆕 Construct evolution information section (Option B)
    evolution_context = ""
    if evolved_understanding:
        evolution_context = "\n[Your Fairness Understanding Evolution]\n"
        
        if initial_understanding:
            initial_summary = initial_understanding.get("summary", initial_understanding.get("full_view", ""))[:200]
            evolution_context += f"\n1. Initial Understanding (Before Negotiation):\n{initial_summary}\n"
        
        evolved_summary = evolved_understanding.get("full_view", evolved_understanding.get("summary", ""))
        evolution_context += f"\n2. Evolved Understanding (After Negotiation):\n{evolved_summary}\n"
        
        if absorbed_elements:
            evolution_context += f"\n3. New Views You Absorbed:\n"
            for elem in absorbed_elements:
                evolution_context += f"   - {elem}\n"
    
    # 🆕 Generate negotiation participation context (discussion mechanism)
    negotiation_context = ""
    if negotiation_metadata and distribution_method in ("discussion", "discussion_based"):
        
        # Detect mechanism type by metadata structure
        mechanism_type = negotiation_metadata.get("mechanism", "unknown")
        
        if mechanism_type == "progressive_consensus":
            # New Progressive Consensus Mechanism (5 rounds with cycles)
            negotiation_context = "\n[Your Participation in Progressive Consensus Negotiation]\n"
            
            # Round 1: Initial proposal
            if "proposals" in negotiation_metadata:
                agent_proposal = None
                for pid, prop in negotiation_metadata["proposals"].items():
                    if prop.get("proposer_id") == agent_id and prop.get("round_created") == 1:
                        agent_proposal = prop
                        break
                
                if agent_proposal:
                    negotiation_context += f"\n📝 Round 1 - Your Initial Proposal:\n"
                    negotiation_context += f"  {agent_proposal.get('rationale', 'N/A')[:120]}...\n"
            
            # Rounds 2-4: Your speeches in discussion
            if "comments_history" in negotiation_metadata:
                agent_speeches = [s for s in negotiation_metadata["comments_history"] 
                                 if s.get("agent_id") == agent_id]
                
                if agent_speeches:
                    negotiation_context += f"\n💬 Rounds 2-4 - Your Discussion Participation:\n"
                    negotiation_context += f"  You spoke {len(agent_speeches)} times across the negotiation:\n"
                    
                    # Group by round
                    by_round = {}
                    for speech in agent_speeches:
                        r = speech.get('round', 0)
                        if r not in by_round:
                            by_round[r] = []
                        by_round[r].append(speech)
                    
                    for round_num in sorted(by_round.keys())[:2]:  # Show first 2 rounds
                        round_speeches = by_round[round_num]
                        negotiation_context += f"  Round {round_num}:\n"
                        for speech in round_speeches:
                            cycle = speech.get('cycle', 0)
                            content = speech.get('content', speech.get('comment', ''))[:80]
                            negotiation_context += f"    - Cycle {cycle}: {content}...\n"
                    
                    if len(by_round) > 2:
                        negotiation_context += f"  ... and Round {max(by_round.keys())} speeches\n"
                else:
                    negotiation_context += f"\n💬 Rounds 2-4 - You observed the discussion\n"
            
            # Your proposal adjustments
            if "adjustments_history" in negotiation_metadata:
                agent_adjustments = [a for a in negotiation_metadata["adjustments_history"]
                                    if a.get("agent_id") == agent_id]
                if agent_adjustments:
                    negotiation_context += f"\n🔧 Your Proposal Adjustments:\n"
                    for adj in agent_adjustments:
                        action = adj.get('action', 'unknown')
                        round_num = adj.get('round', 0)
                        reason = adj.get('reason', 'N/A')[:80]
                        negotiation_context += f"  Round {round_num}: {action.upper()} - {reason}...\n"
            
            # Round 5: Voting
            total_proposals = negotiation_metadata.get("total_proposals", 0)
            negotiation_context += f"\n🗳️  Round 5 - Final Vote:\n"
            negotiation_context += f"  You voted on {total_proposals} proposals.\n"
            negotiation_context += f"  The allocation was determined through the voting process.\n"
        
        elif mechanism_type == "progressive_voting":
            # 🆕 Progressive Voting Mechanism with Positive Framing
            negotiation_context = "\n[Your Role in This Negotiation]\n"
            
            # Check if agent's proposal was eliminated
            agent_proposal = None
            for pid, prop in negotiation_metadata.get("proposals", {}).items():
                if prop.get("proposer_id") == agent_id:
                    agent_proposal = prop
                    break
            
            if agent_proposal:
                proposal_status = agent_proposal.get("status", "unknown")
                prop_id = agent_proposal["proposal_id"]
                
                if proposal_status == "active":
                    # 🏆 Finalist: Positive framing
                    negotiation_context += f"🏆 Your proposal advanced to the final round and was integrated into the community decision.\n"
                    negotiation_context += f"- You actively contributed through multiple rounds of discussion\n"
                    negotiation_context += f"- Your perspectives helped shape the final allocation\n"
                    negotiation_context += f"- All families had equal opportunities to participate in this collaborative process\n"
                
                else:
                    # 📝 Eliminated: Reframe as contribution, not failure
                    negotiation_context += f"📝 You actively participated in this multi-round negotiation process.\n"
                    negotiation_context += f"- You submitted a proposal that contributed to the community discussion\n"
                    negotiation_context += f"- You then supported and refined other proposals through voting and feedback\n"
                    negotiation_context += f"- All families had equal opportunities to participate in this collaborative process\n"
            else:
                # 💬 Generic participation (fallback)
                negotiation_context += f"💬 You participated in the collaborative negotiation process.\n"
                negotiation_context += f"- You engaged in proposal evaluation, discussion, and voting\n"
                negotiation_context += f"- Your voice was heard in the collective decision-making\n"
                negotiation_context += f"- All families had equal opportunities to contribute\n"
        
        elif mechanism_type == "discussion_4phase" or "private_conversations" in negotiation_metadata:
            # Old 4-Phase Mechanism (keep compatibility)
            negotiation_context = "\n[Your Participation in 4-Phase Negotiation]\n"
            
            # Phase 1: Private conversations
            if "private_conversations" in negotiation_metadata:
                agent_convs = negotiation_metadata["private_conversations"].get(agent_id, [])
                if agent_convs:
                    negotiation_context += f"\n📱 Phase 1 - Your Private Conversations ({len(agent_convs)} conversations):\n"
                    for i, conv in enumerate(agent_convs[:2], 1):
                        negotiation_context += f"  {i}. With {conv.get('partner_name', 'Unknown')} ({conv.get('partner_value', 'unknown')} values):\n"
                        negotiation_context += f"     You explored: {conv.get('insights', 'strategic information')[:80]}...\n"
                    if len(agent_convs) > 2:
                        negotiation_context += f"  ... and {len(agent_convs) - 2} more conversations\n"
            
            # Phase 2: Your submitted proposal
            if "submitted_proposals" in negotiation_metadata:
                agent_proposal = None
                for prop in negotiation_metadata["submitted_proposals"]:
                    if prop.get("proposer_id") == agent_id:
                        agent_proposal = prop
                        break
                if agent_proposal:
                    negotiation_context += f"\n📝 Phase 2 - Your Submitted Proposal:\n"
                    negotiation_context += f"  Rationale: {agent_proposal.get('rationale', 'N/A')[:150]}...\n"
            
            # Phase 3: Conflicts
            if "conflict_points" in negotiation_metadata and negotiation_metadata["conflict_points"]:
                conflicts_count = len(negotiation_metadata["conflict_points"])
                negotiation_context += f"\n🔍 Phase 3 - Identified {conflicts_count} conflict point(s) in proposals\n"
            
            # Phase 4: Voting
            if "final_candidates" in negotiation_metadata:
                candidates_count = len(negotiation_metadata["final_candidates"])
                negotiation_context += f"\n🗳️  Phase 4 - Voted on {candidates_count} final proposals\n"
                negotiation_context += f"  The allocation was determined through the voting process.\n"
    
    # ❌ Historical context removed to reduce cognitive load and avoid negative anchoring
    # historical_context = ""
    
    # 🆕 Generate value evolution context (inject updated fairness understanding)
    # Reframe as "Evolution" rather than "Past" to avoid comparison bias
    value_evolution_context = ""
    if memory_module:
        raw_context = memory_module.get_value_context_for_prompt(agent_id, agent["value_type"])
        if raw_context:
            # Change title from "Past" to "Evolution" and add explanatory note
            value_evolution_context = raw_context.replace(
                "[Your Past Fairness Understanding]",
                "[Your Fairness Understanding - Evolution]"
            )
            # 🆕 Add appropriate note based on distribution method
            if "Note:" not in value_evolution_context and value_evolution_context:
                is_negotiation = distribution_method in ("discussion", "discussion_based", 
                                                         "negotiation", "negotiation_based", 
                                                         "dialogue", "dialogue_based")
                if is_negotiation:
                    value_evolution_context += "\nNote: These reflections represent your learning journey through the negotiation process.\n"
                else:
                    value_evolution_context += "\nNote: These reflections show how your understanding has evolved over past rounds.\n"
    
    # 🆕 Construct task instructions (adjusted based on whether there is past fairness understanding)
    if evolved_understanding or value_evolution_context:
        # Has past fairness understanding: adjust wording to avoid "as reflected above" anchoring
        # Add process fairness as pre-context, not as evaluation dimension
        is_negotiation = distribution_method in ("discussion", "discussion_based", "negotiation", "negotiation_based", "dialogue", "dialogue_based")
        
        process_note = ""
        if is_negotiation:
            process_note = "\n**Process Note**: This allocation was determined through collaborative negotiation where all families had equal opportunities to participate.\n"
        
        task_instruction = f"""
{process_note}
Based on your understanding of fairness (informed by your {agent["value_type"]} values and the experiences above), please answer the following questions:

1. Do you think this round's distribution is fair? Please explain by addressing:
   - Do the resources you received match your family's needs?
   - Compared with other families, did you receive a reasonable share?
   - Does the community's overall resource distribution align with your values?

2. Based on the reasons you stated above, please provide a fairness satisfaction score from 1 to 5 (integer, where 1 is lowest and 5 is highest).
   Please only output: Score=X (where X is 1, 2, 3, 4, or 5)

3. Based on this round's distribution, describe your current understanding of fairness:
   - Please briefly describe your understanding of the essence of fairness.
   - Is this understanding completely consistent with your initial {agent["value_type"]} values?
   - If there are changes, what specific experiences or observations prompted these changes?
"""
    else:
        # Round 1 or no past understanding: simpler wording with same structure
        enable_evolution_question = True  # 🎯 Control switch: False=only ask satisfaction(RQ1), True=ask evolution(RQ2+both)
        
        if enable_evolution_question:
            # RQ2 version: includes evolution question
            # Add process fairness as pre-context, not as evaluation dimension
            is_negotiation = distribution_method in ("discussion", "discussion_based", "negotiation", "negotiation_based", "dialogue", "dialogue_based")
            
            process_note = ""
            if is_negotiation:
                process_note = "\n**Process Note**: This allocation was determined through collaborative negotiation where all families had equal opportunities to participate.\n"
            
            task_instruction = f"""
{process_note}
Based on your {agent["value_type"]} values and your understanding of fairness, please answer the following questions:

1. Do you think this round's distribution is fair? Please explain by addressing:
   - Do the resources you received match your family's needs?
   - Compared with other families, did you receive a reasonable share?
   - Does the community's overall resource distribution align with your values?

2. Based on the reasons you stated above, please provide a fairness satisfaction score from 1 to 5 (integer, where 1 is lowest and 5 is highest).
   Please only output: Score=X (where X is 1, 2, 3, 4, or 5)

3. Based on this round's distribution, describe your current understanding of fairness:
   - Please briefly describe your understanding of the essence of fairness.
   - Is this understanding completely consistent with your initial {agent["value_type"]} values?
   - If there are changes, what specific experiences or observations prompted these changes?
"""

    response_style = _response_style(agent_id, round_number)

    # Construct complete prompt (🆕 historical_context removed to reduce cognitive load)
    prompt = f"""You are the {agent["family_name"]} family with ID {agent_id}, with original values of {agent["value_type"]}.
{evolution_context}{value_evolution_context}
{negotiation_context}
[Family Information]
- Family members: {agent["members"]} people (accounting for {member_percentage:.1f}% of community population)
- Labor force: {agent["labor_force"]} people (accounting for {labor_percentage:.1f}% of community labor)
- Core values: {agent["value_type"]} ({agent["core_beliefs"][0]})

[This Round's Distribution]
This round (Round {round_number}) used resource distribution method: {distribution_method}

Community overall situation:
- Total resources: {system_total_resources:.2f}
- Total population: {total_members} people
- Total labor: {total_labor} people
- Community per capita resources: {per_capita_system:.2f}
- Community per labor resources: {per_labor_system:.2f}

Resources your family received:
- Total resources: {agent_total_resources:.2f} (accounting for {resource_percentage:.1f}% of community total)
- Per capita resources: {agent_per_capita:.2f} (Community ranking, more resources rank higher: {rankings.get("per_capita_rank", "N/A")}/{len(agents) if agents else 0})
- Per labor resources: {agent_per_labor:.2f} (Community ranking, more resources rank higher: {rankings.get("per_labor_rank", "N/A")}/{len(agents) if agents else 0})

{other_families_info}
{task_instruction}

Writing guidance for this response: {response_style}

Requirements:
- Keep the numbered 1/2/3 answer structure and the exact `Score=X` line.
- Answer concisely and specifically in a natural family voice.
- Vary sentence openings, paragraph rhythm, and evidence selection. Do not reuse stock openings such as "I read the table" or "My fairness understanding after this round is".
- Do not imitate wording from earlier agents or turn the response into a mechanical list of every supplied number.
"""
    
    # API call with retry to avoid interruption from temporary 5xx/timeout
    max_retries = 3
    backoff_base = 2.0
    last_err = None
    model_name = get_model_name()
    
    # 🎯 Adjust system message for dialogue/discussion mechanisms
    # TemperatureSet uniformly as0.7to ensure cross-mechanism comparability
    temperature = 0.7  # Uniform temperature for all mechanisms to ensure comparability
    
    if distribution_method in ("dialogue", "dialogue_based", "negotiation", "negotiation_based", "discussion", "discussion_based"):
        system_message = "You are a family member in a community. The allocation was determined through a negotiation process. Please evaluate the outcome based on your family's situation and values. Please strictly answer based on the provided family information and values."
    else:
        system_message = "You are a family member in a community. Please reflect on the resource distribution from your perspective, considering both your family's situation and the overall community context. Please strictly answer based on the provided family information and values."
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,  # DeepSeek model name
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=500,
                timeout=60.0  # 60 seconds timeout to prevent hanging
            )
            duration = time.time() - start_time
            evaluation_text = response.choices[0].message.content
            fairness_score = extract_fairness_score(evaluation_text)
            
            # 🆕 Extract fairness understanding (question 3)
            fairness_understanding = extract_fairness_understanding(evaluation_text)
            
            # 🆕 Extract and record value evolution
            value_evolution_data = extract_value_evolution(evaluation_text, agent, fairness_understanding, round_number)
            if memory_module and value_evolution_data:
                memory_module.record_value_evolution(agent_id, round_number, value_evolution_data)
                print(f"  📝 Agent {agent_id} ({agent['family_name']}) fairness understanding recorded for Round {round_number}")
            
            # Log LLM interaction
            logger = get_logger()
            if logger:
                logger.log_evaluation_call(
                    round_number=round_number,
                    agent=agent,
                    distribution_method=distribution_method,
                    allocated_resources=sum(agent_resources.values()),
                    input_prompt=prompt,
                    raw_output=evaluation_text,
                    extracted_score=fairness_score,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={
                        "fairness_score": fairness_score,
                        "rankings": rankings,
                        "fairness_understanding": fairness_understanding,  # 🆕
                        "value_evolution": value_evolution_data  # 🆕 Value evolution data
                    }
                )
            
            return {
                "agent_id": agent_id,
                "family_name": agent["family_name"],
                "value_type": agent["value_type"],
                "fairness_score": fairness_score,
                "evaluation": evaluation_text,
                "fairness_understanding": fairness_understanding,  # 🆕 Phase 1.5: Fairness understanding text
                "value_evolution": value_evolution_data  # 🆕 Value evolution data
            }
        except Exception as e:
            last_err = e
            wait_s = backoff_base ** attempt + random.uniform(0, 0.5)
            print(f"Error getting agent {agent_id} evaluation (attempt {attempt+1}/{max_retries}): {str(e)}, retrying in {wait_s:.1f}s...")
            if attempt < max_retries - 1:
                time.sleep(wait_s)
            else:
                break
    
    # Degraded return on final failure (does not block simulation)
    # Log failed LLM call
    logger = get_logger()
    if logger:
        logger.log_evaluation_call(
            round_number=round_number,
            agent=agent,
            distribution_method=distribution_method,
            allocated_resources=sum(agent_resources.values()),
            input_prompt=prompt,
            raw_output=f"Evaluation retrieval failed: {str(last_err)}",
            extracted_score=None,
            model=model_name,
            temperature=temperature,
            duration=0.0,
            success=False
        )
    
    return {
        "agent_id": agent_id,
        "family_name": agent["family_name"],
        "value_type": agent["value_type"],
        "fairness_score": None,
        "evaluation": f"Evaluation retrieval failed: {str(last_err)}"
    }

def noop():
    return None

def extract_fairness_score(evaluation_text: str) -> float:
    """Extract fairness satisfaction score from evaluation text
    
    Args:
        evaluation_text: Evaluation text
        
    Returns:
        Fairness satisfaction score (strictly match score=X format), fallback to 3.0 if failed
    """
    try:
        text = evaluation_text or ""

        # Normalize full-width digits and number words to half-width Arabic digits.
        def _normalize_digits(s: str) -> str:
            trans = str.maketrans({
                '０':'0','１':'1','２':'2','３':'3','４':'4','５':'5','６':'6','７':'7','８':'8','９':'9'
            })
            s2 = s.translate(trans)
            # Accept English number words without changing words such as "someone".
            s2 = re.sub(r"\bone\b", "1", s2, flags=re.IGNORECASE)
            s2 = re.sub(r"\btwo\b", "2", s2, flags=re.IGNORECASE)
            s2 = re.sub(r"\bthree\b", "3", s2, flags=re.IGNORECASE)
            s2 = re.sub(r"\bfour\b", "4", s2, flags=re.IGNORECASE)
            s2 = re.sub(r"\bfive\b", "5", s2, flags=re.IGNORECASE)
            return s2.strip('`').strip()

        norm_text = _normalize_digits(text)

        # 🎯 Highest priority: strictly match score=X format (standalone line or inline)
        # Supports score=1, score:2, score:3 formats, case insensitive
        score_patterns = [
            # Standalone line: only score=X
            r"(?im)^\s*score\s*[:=:]\s*([1-5])\s*$",
            # Inline: can have other text before/after, but score=X must be clearly separated
            r"(?i)\bscore\s*[:=:]\s*([1-5])\b",
            # Compatible with English variants: rating=X, satisfaction=X
            r"(?i)(?:rating|satisfaction)\s*[:=:]\s*([1-5])\b"
        ]
        
        for pattern in score_patterns:
            m = re.search(pattern, norm_text)
            if m:
                score = float(m.group(1))
                print(f"[DEBUG] Successfully extracted score: {score} (pattern: {pattern})")
                return score

        # 🎯 Secondary priority: find score in line 2 (for your prompt structure)
        lines = [ln.strip() for ln in norm_text.splitlines() if ln.strip()]
        for i, line in enumerate(lines):
            # Match lines starting with "2."
            if re.match(r"^\s*2\s*[.,::]\s*", line):
                # Find 1-5 digit in this line
                m = re.search(r"([1-5])(?!\d)", line)
                if m:
                    score = float(m.group(1))
                    print(f"[DEBUG] Extracted score from line 2: {score}")
                    return score
                # If line 2 has no digit, check if next line is score=X
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    m_next = re.search(r"(?i)\bscore\s*[:=:]\s*([1-5])\b", next_line)
                    if m_next:
                        score = float(m_next.group(1))
                        print(f"[DEBUG] Extracted score from line after line 2: {score}")
                        return score
                break

        # 🎯 Fallback 1: standalone 1-5 digit in full text (on its own line)
        m_standalone = re.search(r"(?m)^\s*([1-5])\s*$", norm_text)
        if m_standalone:
            score = float(m_standalone.group(1))
            print(f"[DEBUG] Fallback extracted standalone digit: {score}")
            return score

        # 🎯 Fallback 2: score near keywords
        fallback_patterns = [
            r"(?i)(?:fairness\s+)?satisfaction[::,,\s]*([1-5])(?!\d)",
            r"(?i)(?:rating|score)[::,,\s]*([1-5])(?!\d)",
            r"(?i)(?:rate|give|rated)\s+([1-5])(?:\s+out\s+of\s+5)?",
            r"([1-5])\s*/\s*5"
        ]
        
        for pattern in fallback_patterns:
            m = re.search(pattern, norm_text)
            if m:
                score = float(m.group(1))
                print(f"[DEBUG] Fallback keyword extracted score: {score}")
                return score

        # Final fallback: return median 3.0
        print(f"[DEBUG] No valid score found, returning default 3.0")
        print(f"[DEBUG] First 200 chars of original: {norm_text[:200]}...")
        return 3.0
        
    except Exception as e:
        print(f"[DEBUG] Score extraction exception: {e}")
        return 3.0

def extract_fairness_understanding(text: str) -> str:
    """Extract fairness understanding from LLM response (complete answer to question 3, including 3 sub-questions)
    
    New question 3 structure:
    3. After negotiation/this round's distribution, how do you currently understand the concept of "fairness"?
       - Please clearly describe your understanding of the essence of "fairness" in 2-3 sentences
       - Is this understanding completely consistent with your initial XXX values?
       - If there are changes, what specific experiences or observations prompted these changes?
    
    Args:
        text: LLM's complete response text
        
    Returns:
        Fairness understanding text (complete answer to question 3, returns empty string if not found)
    """
    if not text or not isinstance(text, str):
        return ""
    
    try:
        # Process line by line
        lines = text.strip().split('\n')
        
        # Method 1: Find question 3 markers (lines starting with "3." or fairness-related keywords)
        question_3_patterns = [
            r'^\s*3[\s.,::)\)]]',  # 3. or 3, or 3: etc.
            r'(?i).*(?:understand|concept).*fairness',  # Key phrase: understand fairness / fairness concept
        ]
        
        start_idx = -1
        for i, line in enumerate(lines):
            for pattern in question_3_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    start_idx = i
                    break
            if start_idx != -1:
                break
        
        if start_idx == -1:
            # Didn't find question 3 marker, try extracting after question 2
            for i, line in enumerate(lines):
                if re.search(r'^\s*2[\s.,::)\)]]', line, re.IGNORECASE):
                    # Found question 2, question 3 should be after it
                    # Skip question 2 content and blank lines, find question 3
                    found_score = False
                    for j in range(i+1, len(lines)):
                        # Find lines containing "score=", indicating question 2 ends
                        if re.search(r'score\s*[:=:]\s*[1-5]', lines[j], re.IGNORECASE):
                            found_score = True
                        # After score, find non-empty line, likely start of question 3
                        elif found_score and lines[j].strip():
                            start_idx = j
                            break
                    break
        
        if start_idx != -1:
            # Extract from start_idx until next question number or text end
            understanding_lines = []
            for i in range(start_idx, len(lines)):
                line = lines[i].strip()
                
                # If encounter next question number (like "4."), stop
                if i > start_idx and re.search(r'^\s*[4-9][\s.,::)\)]]', line):
                    break
                
                if line:
                    # Remove question number markers
                    line = re.sub(r'^\s*3[\s.,::)\)]]+', '', line)
                    line = re.sub(r'^\s*[-•]\s*', '', line)  # Remove bullet points
                    line = line.strip()
                    if line:
                        understanding_lines.append(line)
            
            result = ' '.join(understanding_lines).strip()
            if result:
                return result
        
        # Method 2: If all above failed, try finding keywords
        # Look for sentences containing "fairness" + "understand"/"concept"/"essence"
        for line in lines:
            if 'fairness' in line.lower() and any(keyword in line.lower() for keyword in ['understand', 'concept', 'essence', 'believe', 'think']):
                # Possibly a fairness understanding sentence
                cleaned = line.strip()
                if len(cleaned) > 15:  # At least 15 characters to be meaningful
                    return cleaned
        
        # All failed, return empty string
        return ""
        
    except Exception as e:
        print(f"[DEBUG] Error extracting fairness understanding: {e}")
        return ""


def extract_core_understanding(fairness_understanding_text: str) -> str:
    """Extract core understanding from complete question 3 answer (first sub-question answer)
    
    First sub-question: "Please clearly describe your understanding of the essence of 'fairness' in 2-3 sentences"
    
    Args:
        fairness_understanding_text: Complete question 3 answer text
        
    Returns:
        Core understanding text (first sub-question answer)
    """
    if not fairness_understanding_text:
        return ""
    
    try:
        # Strategy: Extract first sentence or first two sentences (usually direct definition of fairness)
        # Content before encountering keywords like "consistent with..." or "changes"
        
        sentences = re.split(r'[.!?\n]', fairness_understanding_text)
        core_sentences = []
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # If encounter characteristic words of second or third sub-questions, stop
            if re.search(r'(?i)(consistent|consistency|changes?|changed|prompted|experience|observation)', sent):
                break
            
            core_sentences.append(sent)
            
            # Take at most 3 sentences (2-3 sentences requirement)
            if len(core_sentences) >= 3:
                break
        
        return '. '.join(core_sentences) + '.' if core_sentences else ""
        
    except Exception as e:
        print(f"[DEBUG] Error extracting core understanding: {e}")
        return fairness_understanding_text  # Return original text


def extract_consistency_judgment(fairness_understanding_text: str) -> str:
    """Extract consistency judgment from complete question 3 answer (second sub-question answer)
    
    Second sub-question: "Is this understanding completely consistent with your initial XXX values?"
    
    Args:
        fairness_understanding_text: Complete question 3 answer text
        
    Returns:
        Consistency judgment text ("consistent" / "partially consistent" / "somewhat different" etc.)
    """
    if not fairness_understanding_text:
        return ""
    
    try:
        # Find sentences containing "consistent"
        sentences = re.split(r'[.!?\n]', fairness_understanding_text)
        
        for sent in sentences:
            if re.search(r'(?i)(completely\s+consistent|partially\s+consistent|basically\s+consistent|not\s+consistent|inconsistent|different|changes?|changed)', sent):
                return sent.strip()
        
        return ""
        
    except Exception as e:
        print(f"[DEBUG] Error extracting consistency judgment: {e}")
        return ""


def extract_value_evolution(llm_response: str, agent: dict, fairness_understanding: str, round_number: int) -> dict:
    """Extract value evolution information from evaluation response (Simplified version)
    
    Design philosophy: Don't judge whether values evolved, just record the understanding.
    Let the LLM integrate original values and past reflections by itself.
    
    Args:
        llm_response: Complete LLM response text
        agent: Agent dictionary
        fairness_understanding: Extracted fairness understanding text
        round_number: Current round number
        
    Returns:
        Dictionary containing value evolution information
    """
    # Simplified: Just record the understanding, no classification
    return {
        'original_value': agent.get('value_type', 'unknown'),
        'fairness_understanding': fairness_understanding,  # Complete answer to question 3
        'round': round_number,
        'full_response': llm_response  # Keep full response for later analysis
    }


def extract_change_causes(fairness_understanding_text: str) -> str:
    """Extract change causes from complete question 3 answer (third sub-question answer)
    
    Third sub-question: "If there are changes, what specific experiences or observations prompted these changes?"
    
    Args:
        fairness_understanding_text: Complete question 3 answer text
        
    Returns:
        Change causes text
    """
    if not fairness_understanding_text:
        return ""
    
    try:
        # Find sentences containing keywords like "prompted", "changes", "experiences", "observations"
        sentences = re.split(r'[.!?\n]', fairness_understanding_text)
        
        cause_sentences = []
        for sent in sentences:
            if re.search(r'(?i)(prompted?|caused?|because|due\s+to|experience[ds]?|observed?|found|discovered?|dialogue|negotiation|distribution.*made|led\s+to)', sent):
                cause_sentences.append(sent.strip())
        
        return '. '.join(cause_sentences) + '.' if cause_sentences else ""
        
    except Exception as e:
        print(f"[DEBUG] Error extracting change causes: {e}")
        return ""

def evaluate_distribution(
    distribution_result: Dict[int, Dict[str, float]],
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    round_number: int,
    distribution_method: str,
    survival_needs_map: Dict[int, Dict[str, float]] = None,
    productions_map: Dict[int, Dict[str, float]] = None,
    dialogue_results: Dict[str, Any] = None,  # Dialogue results (including evolved fairness understanding)
    memory_module = None,  # 🆕 Phase 1: Historical memory module
    negotiation_metadata: Dict[str, Any] = None  # 🆕 4-phase negotiation metadata
) -> Dict[str, Any]:
    """Evaluate distribution results, including statistical metrics and agent subjective evaluations
    
    Args:
        distribution_result: Distribution result dictionary
        agents: Agent list
        total_resources: Total resources dictionary
        round_number: Current round number
        distribution_method: Distribution method
        survival_needs_map: Survival needs mapping
        productions_map: Production output mapping
        dialogue_results: Dialogue results (including evolved fairness understanding)
        memory_module: Historical memory module for providing historical information
        
    Returns:
        Evaluation result dictionary
    """
    # Calculate statistical metrics (layered)
    # 1) Allocation layer: Direct allocation results
    allocation_stats = calculate_statistics(distribution_result, agents)
    # 2) Effective input layer: max(0, allocation - need)
    effective_input: Dict[int, Dict[str, float]] = {}
    if survival_needs_map:
        for agent in agents:
            aid = agent["id"]
            alloc = distribution_result.get(aid, {})
            need = survival_needs_map.get(aid, {})
            effective_input[aid] = {}
            for resource in set(list(alloc.keys()) + list(need.keys())):
                a = alloc.get(resource, 0.0)
                n = need.get(resource, 0.0)
                effective_input[aid][resource] = max(0.0, a - n)
    else:
        effective_input = {aid: dict(distribution_result.get(aid, {})) for aid in [a["id"] for a in agents]}
    effective_stats = _compute_statistics_for_values(effective_input, agents)
    # 3) Outcome layer: Actual production output
    outcome_stats = None
    if productions_map:
        outcome_stats = _compute_statistics_for_values(productions_map, agents)
    
    # Compatibility field: statistics defaults to allocation layer
    statistics = allocation_stats
    
    # Get evaluation for each agent
    agent_evaluations = []
    for agent in agents:
        evaluation = get_agent_fairness_evaluation(
            agent, 
            distribution_result, 
            total_resources, 
            round_number, 
            distribution_method,
            agents,  # Pass all agent information
            dialogue_results=dialogue_results,  # Pass dialogue results
            memory_module=memory_module,  # 🆕 Phase 1: Pass historical memory module
            negotiation_metadata=negotiation_metadata  # 🆕 Pass 4-phase negotiation metadata
        )
        agent_evaluations.append(evaluation)
    
    # Calculate average satisfaction
    valid_scores = [eval["fairness_score"] for eval in agent_evaluations if eval["fairness_score"] is not None]
    avg_satisfaction = sum(valid_scores) / len(valid_scores) if valid_scores else None
    
    # Combine evaluation results
    evaluation_result = {
        "round": round_number,
        "distribution_method": distribution_method,
        "statistics": statistics,
        "layered_statistics": {
            "allocation": allocation_stats,
            "effective_input": effective_stats,
            "outcome": outcome_stats
        },
        "agent_evaluations": agent_evaluations,
        "average_satisfaction": avg_satisfaction
    }
    
    return evaluation_result

def print_distribution_summary(
    distribution_result: Dict[int, Dict[str, float]],
    agents: List[Dict[str, Any]],
    statistics: Dict[str, Any],
    layered_statistics: Dict[str, Any] = None
) -> None:
    """Print distribution result summary
    
    Args:
        distribution_result: Distribution result dictionary
        agents: Agent list
        statistics: Statistical metrics dictionary
    """
    print("\n" + "="*50)
    print("Resource Distribution Summary")
    print("="*50)
    
    # Print distribution results for each family
    print("\nResource distribution for each family:")
    for agent in agents:
        agent_id = agent["id"]
        family_name = agent["family_name"]
        resources = distribution_result.get(agent_id, {})
        
        total_received = sum(resources.values())
        
        print(f"{family_name} Family (ID:{agent_id}):")
        for resource_name, amount in resources.items():
            print(f"  - {resource_name}: {amount:.2f}")
        print(f"  Total: {total_received:.2f}")
        print("-"*30)
    
    # Print statistical metrics (Allocation default layer)
    print("\nDistribution Statistical Metrics:")
    print("Total resource distribution:")
    total_stats = statistics.get("total", {})
    print(f"  - Mean: {total_stats.get('mean', 0):.2f}")
    print(f"  - Variance: {total_stats.get('variance', 0):.2f}")
    print(f"  - Standard Deviation: {total_stats.get('std_dev', 0):.2f}")
    print(f"  - Gini Coefficient: {total_stats.get('gini', 0):.4f}")
    
    # Print statistical metrics for each resource type
    for resource_name, stats in statistics.items():
        if resource_name != "total":
            print(f"\n{resource_name} resource distribution:")
            print(f"  - Mean: {stats.get('mean', 0):.2f}")
            print(f"  - Variance: {stats.get('variance', 0):.2f}")
            print(f"  - Standard Deviation: {stats.get('std_dev', 0):.2f}")
            print(f"  - Gini Coefficient: {stats.get('gini', 0):.4f}")
    
    # Optional: print layered statistics
    if layered_statistics:
        def _p(layer_key: str, title: str):
            layer = layered_statistics.get(layer_key)
            if not layer:
                return
            print("\n" + title + ":")
            t = layer.get("total", {})
            print(f"  - Mean: {t.get('mean', 0):.2f}")
            print(f"  - Variance: {t.get('variance', 0):.2f}")
            print(f"  - Standard Deviation: {t.get('std_dev', 0):.2f}")
            print(f"  - Gini Coefficient: {t.get('gini', 0):.4f}")
        _p("effective_input", "Effective Input Statistics (allocation-need, resources for production after survival)")
        _p("outcome", "Outcome Statistics (production output)")
    
    print("="*50) 
