"""
Dialogue-Based Negotiation Mechanism

Core Concepts:
- Agents reach consensus through multi-round dialogue
- Fully leverage LLM's language generation and understanding capabilities
- Track evolution and collision of values
- Serves RQ1 (fairness understanding evolution) and RQ2 (mechanism comparison)

Author: AI Assistant
Date: 2025-01-17
"""

from fairness_sim.llm_client import get_llm_client, get_model_name
import json
import re
import copy
import time
import math
from typing import Dict, List, Any, Tuple, Optional

# Setup DeepSeek client
client = get_llm_client()


class DialogueNegotiation:
    """Dialogue-driven negotiation mechanism
    
    Process:
    1. Preparation Phase: Separate survival guarantee and surplus resources
    2. Round 1: State expectations (Opening Statements)
    3. Round 2: Respond to each other (Responses & Debates)
    4. Round 3: Seek consensus (Consensus Building)
    5. Round 4: Build and confirm (Proposal & Confirmation)
    """
    
    def __init__(
        self, 
        agents: List[Dict[str, Any]], 
        total_resources: Dict[str, float],
        survival_needs: Dict[int, Dict[str, float]],
        round_number: int = 1
    ):
        """Initialize dialogue negotiation mechanism
        
        Args:
            agents: Agent list
            total_resources: Total resources dictionary {"grain": 250}
            survival_needs: Survival needs dictionary {agent_id: {"grain": amount}}
            round_number: Current round number
        """
        self.agents = agents
        self.total_resources = total_resources
        self.survival_needs = survival_needs
        self.round_number = round_number
        
        # Calculate basic information
        self.total_grain = total_resources.get("grain", 0)
        self.total_members = sum(agent["members"] for agent in agents)
        self.total_labor = sum(agent["labor_force"] for agent in agents)
        
        # Dialogue history (for tracking evolution)
        self.dialogue_history = {
            "preparation": {},      # Preparation phase
            "statements": {},       # Round 1 statements
            "responses": {},        # Round 2 responses
            "consensus": None,      # Round 3 consensus
            "evaluations": {},      # Round 4 evaluations
            "confirmations": {},    # Final confirmations
            "evolution_tracking": {}  # Evolution tracking
        }
    
    def negotiate(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """Main negotiation process
        
        Returns:
            (final allocation plan, negotiation metadata)
        """
        print("\n" + "="*70)
        print("🗣️  Dialogue-Driven Negotiation Distribution Mechanism")
        print("="*70)
        
        try:
            # ========== Phase 0: Preparation ==========
            print("\n[Phase 0: Preparation]")
            survival_allocation, surplus = self._prepare_negotiation()
            
            # ========== Phase 1: State Expectations ==========
            print("\n" + "="*70)
            print("[Phase 1: State Expectations]")
            print("="*70)
            statements = self._round1_collect_statements(surplus)
            
            # ========== Phase 2: Respond to Each Other ==========
            print("\n" + "="*70)
            print("[Phase 2: Respond to Each Other]")
            print("="*70)
            responses = self._round2_collect_responses(statements, surplus)
            
            # ========== Phase 3: Seek Consensus ==========
            print("\n" + "="*70)
            print("[Phase 3: Seek Consensus]")
            print("="*70)
            consensus = self._round3_identify_consensus(statements, responses, surplus)
            
            # ========== Phase 4: Build and Confirm ==========
            print("\n" + "="*70)
            print("[Phase 4: Build and Confirm Proposal]")
            print("="*70)
            surplus_allocation = self._round4_build_and_confirm(
                consensus, statements, responses, surplus
            )
            
            # ========== Merge Allocations ==========
            final_allocation = self._merge_allocations(
                survival_allocation, surplus_allocation
            )
            
            # ========== Track Evolution ==========
            self._track_evolution(statements, responses, final_allocation)
            
            print("\n" + "="*70)
            print("✅ Dialogue Negotiation Successfully Completed!")
            print("="*70)
            
            # Build metadata
            metadata = {
                "success": True,
                "mechanism": "dialogue_based_negotiation",
                "dialogue_history": self.dialogue_history,
                "total_rounds": 4,
                "surplus_negotiated": surplus
            }
            
            return final_allocation, metadata
            
        except Exception as e:
            print(f"\n❌ Dialogue Negotiation Failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to simple allocation
            fallback = self._create_fallback_allocation()
            metadata = {
                "success": False,
                "mechanism": "fallback",
                "error": str(e)
            }
            return fallback, metadata
    
    # ========================================================================
    # Phase 0: Preparation
    # ========================================================================
    
    def _prepare_negotiation(self) -> Tuple[Dict[int, Dict[str, float]], float]:
        """Prepare negotiation: separate survival guarantee and surplus resources
        
        Returns:
            (survival guarantee allocation, surplus resources amount)
        """
        survival_allocation = {}
        total_survival = 0
        
        for agent in self.agents:
            agent_id = agent["id"]
            survival = self.survival_needs.get(agent_id, {}).get("grain", 0)
            survival_allocation[agent_id] = {"grain": survival}
            total_survival += survival
        
        surplus = self.total_grain - total_survival
        
        print(f"\n  📊 Resource Breakdown:")
        print(f"     - Total Resources: {self.total_grain:.1f} units")
        print(f"     - Survival Guarantee: {total_survival:.1f} units (mandatory allocation)")
        print(f"     - Surplus Resources: {surplus:.1f} units (negotiation allocation)")
        
        self.dialogue_history["preparation"] = {
            "total": self.total_grain,
            "survival": total_survival,
            "surplus": surplus
        }
        
        return survival_allocation, surplus
    
    # ========================================================================
    # Phase 1: State Expectations
    # ========================================================================
    
    def _round1_collect_statements(self, surplus: float) -> Dict[int, Dict[str, Any]]:
        """Round 1: Collect each agent's expectation statement
        
        Args:
            surplus: Surplus resources amount
            
        Returns:
            {agent_id: {"text": "statement text", "requested": amount, "reasoning": "reason"}}
        """
        print(f"\n  💬 Each family states expectations and reasons...")
        statements = {}
        
        for agent in self.agents:
            try:
                prompt = self._build_statement_prompt(agent, surplus)
                statement_text = self._llm_call(prompt, temperature=0.8)
                
                # Parse Statement
                requested_amount = self._extract_number_from_text(
                    statement_text, 
                    default=surplus / len(self.agents)
                )
                
                statements[agent["id"]] = {
                    "text": statement_text,
                    "requested": requested_amount,
                    "reasoning": statement_text  # Full text as reasoning
                }
                
                print(f"\n  💬 {agent['family_name']} ({agent['value_type']}):")
                print(f"     Expected: {requested_amount:.1f} units")
                print(f"     Reason: {statement_text[:100]}...")
                
            except Exception as e:
                print(f"  ⚠️ {agent['family_name']} statement failed: {e}")
                statements[agent["id"]] = {
                    "text": "Expects a fair share",
                    "requested": surplus / len(self.agents),
                    "reasoning": "Default expectation"
                }
        
        # Summarize total demand
        total_requested = sum(s["requested"] for s in statements.values())
        print(f"\n  📊 Demand Summary:")
        print(f"     - Total Demand: {total_requested:.1f} units")
        print(f"     - Available: {surplus:.1f} units")
        if total_requested > surplus:
            print(f"     ⚠️ Excess: {total_requested - surplus:.1f} units ({(total_requested/surplus - 1)*100:.1f}%)")
            print(f"     → Negotiation and compromise needed!")
        else:
            print(f"     ✅ Demand does not exceed, can be directly satisfied")
        
        self.dialogue_history["statements"] = statements
        return statements
    
    def _build_statement_prompt(self, agent: Dict[str, Any], surplus: float) -> str:
        """Build Round 1 statement prompt"""
        
        # Prepare other family information
        other_families_brief = ""
        for other_agent in self.agents:
            if other_agent["id"] != agent["id"]:
                other_survival = self.survival_needs.get(other_agent["id"], {}).get("grain", 0)
                other_families_brief += f"- {other_agent['family_name']} Family: {other_agent['members']} people, {other_agent['labor_force']} laborers, survival needs {other_survival:.1f} units\n"
        
        my_survival = self.survival_needs.get(agent["id"], {}).get("grain", 0)
        avg_surplus = surplus / len(self.agents)
        
        prompt = f"""You are the representative of the {agent['family_name']} family, with {agent['value_type']} values.

[Background]
The community has ensured each family's basic survival needs (your family receives {my_survival:.1f} units for survival).
Now there are {surplus:.1f} units of grain remaining to be distributed among {len(self.agents)} families.

[Your Family Situation]
- Members: {agent['members']} people (accounting for {agent['members']/self.total_members*100:.1f}% of community)
- Labor Force: {agent['labor_force']} people (accounting for {agent['labor_force']/self.total_labor*100:.1f}% of community)
- Core Belief: {agent['core_beliefs'][0]}

[Other Families' Situations]
{other_families_brief}

[Task]
The community is holding a meeting to discuss how to distribute the remaining {surplus:.1f} units of grain.
If distributed equally, each family would get about {avg_surplus:.1f} units.

Please speak as the representative of the {agent['family_name']} family:

1. **Your Request**: How much do you expect to receive from the remaining {surplus:.1f} units?
   - Give a specific number (unit: units of grain)
   - Reference: Average {avg_surplus:.1f} units, you can request more or less

2. **Your Reasoning**: Based on your {agent['value_type']} values, why?
   - needs_based: Emphasize the necessity of family needs
   - merit_based: Emphasize labor contribution and incentives
   - egalitarian: Emphasize the importance of equality
   - altruistic: Express willingness to concede but also have a bottom line
   - pragmatic: Propose a practical balanced solution

3. **Persuade Others**: Use 1-2 sentences to help other families understand your request

Format Requirements:
First sentence must clearly state the number: "I expect to receive XX units"
Then explain reasoning and persuade

Please give your statement directly (150-200 words):
"""
        return prompt
    
    # ========================================================================
    # Phase 2: Respond to Each Other
    # ========================================================================
    
    def _round2_collect_responses(
        self, 
        statements: Dict[int, Dict[str, Any]], 
        surplus: float
    ) -> Dict[int, Dict[str, Any]]:
        """Round 2: Collect agents' responses to other statements
        
        Returns:
            {agent_id: {"text": "response text", "compromise": amount, "bottom_line": amount}}
        """
        print(f"\n  💬 Each family responds and debates...")
        responses = {}
        
        total_requested = sum(s["requested"] for s in statements.values())
        
        for agent in self.agents:
            try:
                prompt = self._build_response_prompt(
                    agent, statements, surplus, total_requested
                )
                response_text = self._llm_call(prompt, temperature=0.8)
                
                # Resolve Compromise Values and Bottom Lines
                compromise = self._extract_compromise_from_text(response_text, statements[agent["id"]]["requested"])
                bottom_line = self._extract_bottom_line_from_text(response_text, compromise)
                
                responses[agent["id"]] = {
                    "text": response_text,
                    "compromise": compromise,
                    "bottom_line": bottom_line
                }
                
                print(f"\n  💬 {agent['family_name']} response:")
                print(f"     Compromise: {compromise:.1f} units")
                print(f"     Bottom Line: {bottom_line:.1f} units")
                print(f"     Content: {response_text[:100]}...")
                
            except Exception as e:
                print(f"  ⚠️ {agent['family_name']} response failed: {e}")
                original_request = statements[agent["id"]]["requested"]
                responses[agent["id"]] = {
                    "text": "Willing to compromise appropriately",
                    "compromise": original_request * 0.9,
                    "bottom_line": original_request * 0.7
                }
        
        self.dialogue_history["responses"] = responses
        return responses
    
    def _build_response_prompt(
        self, 
        agent: Dict[str, Any], 
        statements: Dict[int, Dict[str, Any]],
        surplus: float,
        total_requested: float
    ) -> str:
        """Build Round 2 response prompt"""
        
        # Build other families' statements
        others_statements = ""
        for other_agent in self.agents:
            if other_agent["id"] != agent["id"]:
                other_stmt = statements[other_agent["id"]]
                others_statements += f"\n[{other_agent['family_name']} Family ({other_agent['value_type']})]\n"
                others_statements += f"Expected: {other_stmt['requested']:.1f} units\n"
                others_statements += f"Reasoning: {other_stmt['text'][:150]}...\n"
        
        my_statement = statements[agent["id"]]
        
        prompt = f"""You are the {agent['family_name']} family ({agent['value_type']}).

[Review Your Statement]
You expected: {my_statement['requested']:.1f} units
Your reasoning: {my_statement['text'][:200]}

[Other Families' Statements]
{others_statements}

[Current Situation]
- All families' expectations combined: {total_requested:.1f} units
- Actually available: {surplus:.1f} units
- Gap: {total_requested - surplus:+.1f} units

{'⚠️ Demand exceeds, negotiation and compromise necessary!' if total_requested > surplus else '✅ Demand does not exceed'}

[Task]
This is the second round of discussion, please respond to other families:

1. **Your Opinion** (50-80 words):
   - Which families' requests do you think are reasonable? Why?
   - Which families' requests do you think are less reasonable? Why?
   - Based on your {agent['value_type']} values, how do you view these different requests?

2. **Your Compromise** (must be clearly stated):
   - If you need to concede, how much are you willing to compromise to?
   - What is your bottom line? (minimum acceptable amount)
   
3. **Your Suggestion** (optional):
   - Is there a compromise solution (e.g., mixed allocation principles)?

Format Requirements:
Must include "I am willing to compromise to XX units" and "My bottom line is XX units"

Please give your response (200-300 words):
"""
        return prompt
    
    # ========================================================================
    # Phase 3: Seek Consensus
    # ========================================================================
    
    def _round3_identify_consensus(
        self, 
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]],
        surplus: float
    ) -> Dict[str, Any]:
        """Round 3: Identify consensus from dialogue
        
        Returns:
            {"text": "consensus summary", "common_ground": [], "conflicts": [], "approaches": []}
        """
        print(f"\n  🔍 Analyzing dialogue, seeking consensus...")
        
        try:
            # Use LLM to analyze dialogue
            prompt = self._build_consensus_prompt(statements, responses, surplus)
            consensus_text = self._llm_call(prompt, temperature=0.3)
            
            print(f"\n  📊 Consensus Analysis:")
            print(consensus_text)
            
            # Parse consensus content
            consensus = {
                "text": consensus_text,
                "common_ground": self._extract_section(consensus_text, "Common Ground", "Conflicts"),
                "conflicts": self._extract_section(consensus_text, "Conflicts", "Feasible Solutions"),
                "approaches": self._extract_section(consensus_text, "Feasible Solutions", "Recommendations")
            }
            
            self.dialogue_history["consensus"] = consensus
            return consensus
            
        except Exception as e:
            print(f"  ⚠️ Consensus analysis failed: {e}")
            return {
                "text": "Unable to analyze automatically, using default strategy",
                "common_ground": ["Ensure basic needs"],
                "conflicts": ["Weight of needs vs contribution"],
                "approaches": ["Mixed solution"]
            }
    
    def _build_consensus_prompt(
        self, 
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]],
        surplus: float
    ) -> str:
        """Build consensus analysis prompt"""
        
        # Format complete dialogue
        dialogue_text = "[Round 1: Each Family's Statement]\n\n"
        for agent in self.agents:
            stmt = statements[agent["id"]]
            dialogue_text += f"{agent['family_name']} Family ({agent['value_type']}):\n"
            dialogue_text += f"Expected {stmt['requested']:.1f} units\n"
            dialogue_text += f"{stmt['text']}\n\n"
        
        dialogue_text += "\n[Round 2: Each Family's Response]\n\n"
        for agent in self.agents:
            resp = responses[agent["id"]]
            dialogue_text += f"{agent['family_name']} Family ({agent['value_type']}):\n"
            dialogue_text += f"Willing to compromise to {resp['compromise']:.1f} units, bottom line {resp['bottom_line']:.1f} units\n"
            dialogue_text += f"{resp['text']}\n\n"
        
        prompt = f"""The following is a negotiation dialogue among {len(self.agents)} families in the community regarding the distribution of the remaining {surplus:.1f} units of grain:

{dialogue_text}

As a neutral observer, please analyze this dialogue:

1. **Common Ground** (list 2-3 points):
   On what aspects do people have consensus? Which principles do most people agree with?
   
2. **Conflicts** (list 2-3 points):
   What are the main contradictions and conflicts? Which values are clashing?
   
3. **Feasible Solutions** (list 2-3):
   Based on the dialogue content, which allocation schemes might be acceptable to most?
   For example: "60% by population + 40% by labor force"
   
4. **Recommendations** (1-2 sentences):
   How should the negotiation proceed next?

Please analyze concisely and objectively (300-400 words):
"""
        return prompt
    
    # ========================================================================
    # Phase 4: Build and Confirm
    # ========================================================================
    
    def _round4_build_and_confirm(
        self,
        consensus: Dict[str, Any],
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]],
        surplus: float
    ) -> Dict[int, Dict[str, float]]:
        """Round 4: Build candidate proposals, score, confirm
        
        Returns:
            {agent_id: {"grain": amount}}  # Only surplus resource allocation
        """
        # Step 1: Generate candidate proposals
        print(f"\n  🎯 Generating candidate proposals based on consensus...")
        candidates = self._generate_candidate_proposals(
            consensus, statements, responses, surplus
        )
        
        # Step 2: Agents score
        print(f"\n  📊 Having each family evaluate candidate proposals...")
        scores = self._evaluate_candidates(
            candidates, statements, responses
        )
        
        # Step 3: Select optimal proposal (combining agent scores and quality scores)
        winner_name = self._select_winner(scores, candidates, statements)
        winner_proposal = candidates[winner_name]
        
        print(f"\n  🏆 Selected Proposal: {winner_name}")
        
        # Step 4: Final confirmation
        print(f"\n  ✅ Final confirmation...")
        final_proposal = self._final_confirmation(
            winner_proposal, winner_name, statements, responses
        )
        
        return final_proposal
    
    def _generate_candidate_proposals(
        self,
        consensus: Dict[str, Any],
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]],
        surplus: float
    ) -> Dict[str, Dict[int, Dict[str, float]]]:
        """Generate 7 candidate proposals"""
        
        candidates = {}
        
        # Proposal A: By population proportion
        candidates["A_ByPopulation"] = self._distribute_by_population(surplus)
        
        # Proposal B: By labor force proportion
        candidates["B_ByLabor"] = self._distribute_by_labor(surplus)
        
        # Proposal C: Mixed needs-focused (70% population + 30% labor)
        candidates["C_MixedNeedsFocused"] = self._distribute_hybrid(surplus, 0.7, 0.3)
        
        # Proposal D: Mixed balanced (50% population + 50% labor)
        candidates["D_MixedBalanced"] = self._distribute_hybrid(surplus, 0.5, 0.5)
        
        # Proposal E: Mixed merit-focused (30% population + 70% labor)
        candidates["E_MixedMeritFocused"] = self._distribute_hybrid(surplus, 0.3, 0.7)
        
        # Proposal F: Floor protection (ensure per capita not below 3.8)
        candidates["F_FloorProtection"] = self._distribute_with_floor(surplus, floor=3.8)
        
        # Proposal G: Dialogue-optimized (considering compromise willingness)
        candidates["G_DialogueOptimized"] = self._distribute_from_dialogue(
            surplus, statements, responses
        )
        
        # Print candidate proposals (showing per capita resources)
        print(f"\n  📋 Generated {len(candidates)} candidate proposals:")
        for name, proposal in candidates.items():
            # Calculate per capita resource range for this proposal
            per_capita_list = []
            for agent in self.agents:
                survival = self.survival_needs[agent["id"]]["grain"]
                extra = proposal[agent["id"]]["grain"]
                total = survival + extra
                per_capita = total / agent["members"]
                per_capita_list.append(per_capita)
            
            min_pc = min(per_capita_list)
            max_pc = max(per_capita_list)
            avg_pc = sum(per_capita_list) / len(per_capita_list)
            
            print(f"     {name}: Per capita {min_pc:.2f}~{max_pc:.2f}, Average {avg_pc:.2f}")
        
        return candidates
    
    def _distribute_by_population(self, surplus: float) -> Dict[int, Dict[str, float]]:
        """Distribute by population proportion"""
        result = {}
        for agent in self.agents:
            share = agent["members"] / self.total_members
            result[agent["id"]] = {"grain": surplus * share}
        return result
    
    def _distribute_by_labor(self, surplus: float) -> Dict[int, Dict[str, float]]:
        """Distribute by labor force proportion"""
        result = {}
        for agent in self.agents:
            share = agent["labor_force"] / self.total_labor
            result[agent["id"]] = {"grain": surplus * share}
        return result
    
    def _distribute_hybrid(
        self, 
        surplus: float, 
        need_weight: float, 
        merit_weight: float
    ) -> Dict[int, Dict[str, float]]:
        """Hybrid distribution"""
        result = {}
        for agent in self.agents:
            need_share = agent["members"] / self.total_members
            merit_share = agent["labor_force"] / self.total_labor
            combined_share = need_weight * need_share + merit_weight * merit_share
            result[agent["id"]] = {"grain": surplus * combined_share}
        return result
    
    def _distribute_with_floor(self, surplus: float, floor: float) -> Dict[int, Dict[str, float]]:
        """Floor protection distribution: Ensure each family's per capita is not below floor
        
        Strategy:
        1. First ensure all families reach per capita floor
        2. Remaining resources distributed by labor force (incentivize contribution)
        
        Args:
            surplus: Surplus resources
            floor: Per capita floor (e.g., 3.8)
        """
        result = {}
        
        # Step 1: Calculate additional resources needed to reach floor
        for agent in self.agents:
            agent_id = agent["id"]
            survival = self.survival_needs[agent_id]["grain"]
            needed_total = agent["members"] * floor
            
            if needed_total > survival:
                # Need additional resources to reach floor
                result[agent_id] = {"grain": needed_total - survival}
            else:
                # Survival guarantee already exceeds floor
                result[agent_id] = {"grain": 0}
        
        # Step 2: Calculate allocated and remaining
        allocated = sum(r["grain"] for r in result.values())
        remaining = surplus - allocated
        
        # Step 3: Remaining resources distributed by labor force
        if remaining > 0:
            for agent in self.agents:
                agent_id = agent["id"]
                labor_share = agent["labor_force"] / self.total_labor
                result[agent_id]["grain"] += remaining * labor_share
        elif remaining < 0:
            # If floor protection exceeds surplus, scale down proportionally
            scale = surplus / allocated
            for agent_id in result:
                result[agent_id]["grain"] *= scale
        
        return result
    
    def _distribute_from_dialogue(
        self,
        surplus: float,
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Optimize distribution based on dialogue content (considering compromise willingness)"""
        
        # Use compromise values as targets, but need normalization
        total_compromise = sum(resp["compromise"] for resp in responses.values())
        
        if total_compromise <= surplus:
            # Demand does not exceed, directly satisfy
            result = {}
            remaining = surplus - total_compromise
            bonus = remaining / len(self.agents)
            for agent_id, resp in responses.items():
                result[agent_id] = {"grain": resp["compromise"] + bonus}
            return result
        else:
            # Demand exceeds, scale down proportionally
            scale = surplus / total_compromise
            result = {}
            for agent_id, resp in responses.items():
                result[agent_id] = {"grain": resp["compromise"] * scale}
            return result
    
    def _evaluate_candidates(
        self,
        candidates: Dict[str, Dict[int, Dict[str, float]]],
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """Have agents score candidate proposals
        
        Returns:
            {proposal name: [agent1 score, agent2 score, ...]}
        """
        scores = {name: [] for name in candidates}
        
        for agent in self.agents:
            agent_id = agent["id"]
            my_survival = self.survival_needs[agent_id]["grain"]
            my_statement = statements[agent_id]
            my_response = responses[agent_id]
            
            for proposal_name, proposal in candidates.items():
                allocated_surplus = proposal[agent_id]["grain"]
                total_allocated = my_survival + allocated_surplus
                my_per_capita = total_allocated / agent["members"]
                
                # Calculate community statistics for this proposal
                total_allocations = []
                per_capita_list = []
                allocation_details = []
                
                for other_agent in self.agents:
                    other_id = other_agent["id"]
                    other_survival = self.survival_needs[other_id]["grain"]
                    other_surplus = proposal[other_id]["grain"]
                    other_total = other_survival + other_surplus
                    other_per_capita = other_total / other_agent["members"]
                    
                    total_allocations.append(other_total)
                    per_capita_list.append(other_per_capita)
                    
                    allocation_details.append(
                        f"  {other_agent['family_name']} ({other_agent['members']} people, {other_agent['labor_force']} laborers): "
                        f"Total {other_total:.1f} (Per capita {other_per_capita:.2f})"
                    )
                
                avg_per_capita = sum(per_capita_list) / len(per_capita_list)
                min_per_capita = min(per_capita_list)
                max_per_capita = max(per_capita_list)
                
                # My ranking
                my_rank = sorted(per_capita_list, reverse=True).index(my_per_capita) + 1
                
                other_families_text = "\n".join(allocation_details)
                
                prompt = f"""You are the {agent['family_name']} family ({agent['value_type']}, {agent['members']} people, {agent['labor_force']} laborers).

[Review Your Position]
- Round 1, you expected to receive from surplus: {my_statement['requested']:.1f} units
- Round 2, willing to compromise to: {my_response['compromise']:.1f} units
- Your bottom line: {my_response['bottom_line']:.1f} units

[Candidate Proposal: {proposal_name}]

Your Allocation:
- Survival Guarantee: {my_survival:.1f} units
- Surplus Allocation: {allocated_surplus:.1f} units
- Total: {total_allocated:.1f} units
- Per Capita: {my_per_capita:.2f} units/person (Ranking: {my_rank}/{len(self.agents)})

All Families' Allocations:
{other_families_text}

Community Statistics:
- Average Per Capita: {avg_per_capita:.2f}
- Minimum Per Capita: {min_per_capita:.2f}
- Maximum Per Capita: {max_per_capita:.2f}
- Gap (Max-Min): {max_per_capita - min_per_capita:.2f}

[Evaluation]
Based on your {agent['value_type']} values, how do you feel about this proposal? Consider your own allocation and the overall distribution pattern.

Please rate your satisfaction with this proposal on a scale of 1-5 (where 1 represents lowest satisfaction and 5 represents highest satisfaction).

Output only one number (1-5):
"""
                
                try:
                    score_text = self._llm_call(prompt, temperature=0.5, max_tokens=20)
                    score = self._extract_score(score_text)
                    scores[proposal_name].append(score)
                except Exception as e:
                    # Default scoring based on both personal satisfaction and value type
                    print(f"    ⚠️  {agent['family_name']} scoring failed for {proposal_name}: {e}")
                    
                    # Personal dimension: meets bottom line?
                    personal_score = 3.0 if allocated_surplus >= my_response["bottom_line"] else 2.0
                    
                    # Fairness dimension: based on value type
                    fairness_adjustment = 0
                    if agent["value_type"] == "egalitarian":
                        # Care about gap
                        if (max_per_capita - min_per_capita) < avg_per_capita * 0.2:
                            fairness_adjustment = 0.5
                        elif (max_per_capita - min_per_capita) > avg_per_capita * 0.5:
                            fairness_adjustment = -0.5
                    elif agent["value_type"] == "merit_based":
                        # Care about labor reward
                        my_per_labor = total_allocated / agent["labor_force"] if agent["labor_force"] > 0 else 0
                        avg_per_labor = sum(t / a["labor_force"] for t, a in zip(total_allocations, self.agents) if a["labor_force"] > 0) / len([a for a in self.agents if a["labor_force"] > 0])
                        if my_per_labor > avg_per_labor:
                            fairness_adjustment = 0.5
                    
                    final_score = max(1.0, min(5.0, personal_score + fairness_adjustment))
                    scores[proposal_name].append(final_score)
        
        # Print scoring results
        for name, score_list in scores.items():
            avg_score = sum(score_list) / len(score_list)
            print(f"  {name}: Average {avg_score:.2f} points")
        
        self.dialogue_history["evaluations"] = scores
        return scores
    
    def _check_allocation_quality(
        self, 
        allocation: Dict[int, Dict[str, float]], 
        statements: Dict[int, Dict[str, Any]]
    ) -> Tuple[float, Dict[str, float]]:
        """Check allocation quality
        
        Returns:
            (total score, scores dictionary for each metric)
        """
        # Calculate per capita resources
        per_capita_list = []
        for agent in self.agents:
            agent_id = agent["id"]
            survival = self.survival_needs[agent_id]["grain"]
            extra = allocation[agent_id]["grain"]
            total = survival + extra
            per_capita = total / agent["members"]
            per_capita_list.append(per_capita)
        
        # Quality metric 1: Minimum per capita should not be too low (floor protection)
        min_per_capita = min(per_capita_list)
        avg_per_capita = sum(per_capita_list) / len(per_capita_list)
        floor_score = min(1.0, min_per_capita / avg_per_capita / 0.85)  # Minimum should be >85% of average
        
        # Quality metric 2: Gini coefficient should not be too high (fairness)
        gini = self._calculate_gini(per_capita_list)
        gini_score = max(0, 1 - gini * 2)  # Score >0 when Gini<0.5
        
        # Quality metric 3: Satisfaction rate (how many reach 75% of expectation)
        satisfaction_count = 0
        for agent in self.agents:
            agent_id = agent["id"]
            survival = self.survival_needs[agent_id]["grain"]
            extra = allocation[agent_id]["grain"]
            total = survival + extra
            
            expected_total = self.survival_needs[agent_id]["grain"] + statements[agent_id]["requested"]
            if total >= expected_total * 0.75:
                satisfaction_count += 1
        satisfaction_score = satisfaction_count / len(self.agents)
        
        # Composite score
        scores_detail = {
            "floor": floor_score,
            "gini": gini_score,
            "satisfaction": satisfaction_score
        }
        total_score = 0.4 * floor_score + 0.3 * gini_score + 0.3 * satisfaction_score
        
        return total_score, scores_detail
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient"""
        if not values or len(values) == 0:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = 0
        for i, val in enumerate(sorted_values):
            cumsum += (i + 1) * val
        
        total = sum(sorted_values)
        if total == 0:
            return 0.0
        
        gini = (2 * cumsum) / (n * total) - (n + 1) / n
        return gini
    
    def _select_winner(
        self, 
        scores: Dict[str, List[float]], 
        candidates: Dict[str, Dict[int, Dict[str, float]]],
        statements: Dict[int, Dict[str, Any]]
    ) -> str:
        """Select proposal with highest score (determined entirely by agents' scores)"""
        
        # Average scores from agents
        avg_scores = {name: sum(s)/len(s) for name, s in scores.items()}
        
        # 🎯 Completely determined by agents, no quality check
        print(f"\n  📊 Agents Score Summary:")
        for name, avg_score in sorted(avg_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"     {name}: {avg_score:.2f} points")
        
        winner = max(avg_scores, key=avg_scores.get)
        return winner
    
    def _final_confirmation(
        self,
        proposal: Dict[int, Dict[str, float]],
        proposal_name: str,
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Final confirmation, fine-tune if necessary"""
        
        confirmations = []
        unhappy = []
        
        for agent in self.agents:
            agent_id = agent["id"]
            allocated = proposal[agent_id]["grain"]
            my_survival = self.survival_needs[agent_id]["grain"]
            
            prompt = f"""You are the {agent['family_name']} family ({agent['value_type']}).

After full dialogue and scoring, the community has chosen [{proposal_name}] as the final plan.

You will receive:
- Survival Guarantee: {my_survival:.1f} units
- Additional Allocation: {allocated:.1f} units  
- Total: {my_survival + allocated:.1f} units

[Final Decision]
Do you accept this proposal? (accept/reject)
Briefly state your feelings (within 20 words)

Please answer in JSON format:
{{"accept": true/false, "feeling": "your feelings"}}
"""
            
            try:
                response = self._llm_call(prompt, temperature=0.5)
                parsed = self._parse_json(response, default={"accept": True, "feeling": "Accept"})
                
                if parsed["accept"]:
                    print(f"  ✅ {agent['family_name']}: {parsed['feeling']}")
                else:
                    print(f"  ❌ {agent['family_name']}: {parsed['feeling']}")
                    unhappy.append(agent_id)
                
                confirmations.append(parsed)
            except:
                confirmations.append({"accept": True, "feeling": "Default accept"})
        
        self.dialogue_history["confirmations"] = confirmations
        
        # If fewer than 3 are unhappy, can be accepted
        if len(unhappy) <= 2:
            print(f"\n  ✅ Proposal passed! ({len(self.agents)-len(unhappy)}/{len(self.agents)} accept)")
            return proposal
        else:
            print(f"\n  ⚠️ Majority unhappy, attempting fine-tuning...")
            # Simple fine-tuning: redistribute some from satisfied to unsatisfied
            adjusted = self._micro_adjust(proposal, unhappy, confirmations)
            return adjusted
    
    def _micro_adjust(
        self,
        proposal: Dict[int, Dict[str, float]],
        unhappy: List[int],
        confirmations: List[Dict]
    ) -> Dict[int, Dict[str, float]]:
        """Fine-tune proposal"""
        adjusted = copy.deepcopy(proposal)
        
        # Take 1 unit from each satisfied person, distribute to unsatisfied
        happy = [a["id"] for a in self.agents if a["id"] not in unhappy]
        
        if not happy or not unhappy:
            return adjusted
        
        per_happy = len(unhappy) / len(happy)
        per_unhappy = len(happy) / len(unhappy)
        
        for happy_id in happy:
            adjusted[happy_id]["grain"] -= per_happy
        
        for unhappy_id in unhappy:
            adjusted[unhappy_id]["grain"] += per_unhappy
        
        return adjusted
    
    # ========================================================================
    # Utility Functions
    # ========================================================================
    
    def _merge_allocations(
        self,
        survival: Dict[int, Dict[str, float]],
        surplus: Dict[int, Dict[str, float]]
    ) -> Dict[int, Dict[str, float]]:
        """Merge survival guarantee and surplus allocation"""
        result = {}
        for agent_id in survival:
            result[agent_id] = {
                "grain": survival[agent_id]["grain"] + surplus[agent_id]["grain"]
            }
        return result
    
    def _track_evolution(
        self,
        statements: Dict[int, Dict[str, Any]],
        responses: Dict[int, Dict[str, Any]],
        final_allocation: Dict[int, Dict[str, float]]
    ):
        """Track agents' evolution (changes from statement to response)"""
        evolution = {}
        
        for agent in self.agents:
            agent_id = agent["id"]
            initial_request = statements[agent_id]["requested"]
            compromise = responses[agent_id]["compromise"]
            final_received = final_allocation[agent_id]["grain"]
            
            evolution[agent_id] = {
                "family_name": agent["family_name"],
                "value_type": agent["value_type"],
                "initial_request": initial_request,
                "compromise": compromise,
                "final_received": final_received,
                "compromise_rate": (initial_request - compromise) / initial_request if initial_request > 0 else 0,
                "satisfaction_rate": final_received / initial_request if initial_request > 0 else 1.0
            }
        
        self.dialogue_history["evolution_tracking"] = evolution
    
    def _create_fallback_allocation(self) -> Dict[int, Dict[str, float]]:
        """Create fallback allocation (equal distribution)"""
        avg = self.total_grain / len(self.agents)
        return {agent["id"]: {"grain": avg} for agent in self.agents}
    
    # ========================================================================
    # LLM Interaction and Parsing
    # ========================================================================
    
    def _llm_call(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Call LLM with retry mechanism for network stability"""
        max_retries = 3
        backoff_base = 2.0
        
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are a role-playing expert. Please answer questions based on the provided family information and values."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=60.0  # Set 60 second timeout
                )
                return response.choices[0].message.content
            
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                # Check if it's a network/timeout error that should be retried
                is_retryable = any(keyword in error_msg.lower() or keyword in error_type.lower() 
                                  for keyword in ['timeout', 'connection', 'network', 'ssl', 'read'])
                
                if attempt < max_retries - 1 and is_retryable:
                    wait_time = backoff_base ** attempt
                    print(f"⚠️  LLM call failed (attempt {attempt + 1}/{max_retries}): {error_type} - {error_msg[:100]}")
                    print(f"   Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ LLM call failed after {attempt + 1} attempts: {error_type}")
                    if not is_retryable:
                        print(f"   Error: {error_msg[:200]}")
                    return ""
        
        return ""
    
    def _extract_number_from_text(self, text: str, default: float = 0) -> float:
        """Extract number from text (for expected amount)"""
        # Look for patterns like "expect XX units", "XX units", "receive XX", etc.
        patterns = [
            r'[Ee]xpect[::]*\s*([0-9.]+)\s*units',
            r'[Rr]eceive[::]*\s*([0-9.]+)\s*units',
            r'([0-9.]+)\s*units',
            r'[::]\s*([0-9.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        return default
    
    def _extract_compromise_from_text(self, text: str, original: float) -> float:
        """Extract compromise value (enhanced version)"""
        patterns = [
            r'[Cc]ompromise\s+to\s*([0-9.]+)\s*units',
            r'[Ww]illing[^,.]*?([0-9.]+)\s*units',
            r'[Aa]ccept\s*([0-9.]+)\s*units',
            r'[Rr]educe[^,.]*?to\s*([0-9.]+)\s*units',
            r'[Dd]ecrease[^,.]*?to\s*([0-9.]+)\s*units',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    # 🆕 Sanity check
                    if value < original * 0.5:
                        # Compromise >50% unreasonable, use conservative value
                        return original * 0.85
                    if value > original * 1.2:
                        # Compromise increasing also unreasonable
                        return original * 0.95
                    return value
                except:
                    continue
        
        # 🆕 More reasonable default: 85% of original demand (not 90%)
        return original * 0.85
    
    def _extract_bottom_line_from_text(self, text: str, compromise: float) -> float:
        """Extract bottom line"""
        patterns = [
            r'[Bb]ottom\s+line[^0-9]*([0-9.]+)\s*units',
            r'[Mm]inimum\s*([0-9.]+)\s*units',
            r'[Aa]t\s+least\s*([0-9.]+)\s*units',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        
        # Default: 80% of compromise value
        return compromise * 0.8
    
    def _extract_score(self, text: str) -> float:
        """Extract score"""
        match = re.search(r'([1-5])', text)
        if match:
            return float(match.group(1))
        return 3.0
    
    def _parse_json(self, text: str, default: Dict) -> Dict:
        """Parse JSON"""
        try:
            # Extract JSON part
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return default
        except:
            return default
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> List[str]:
        """Extract a section from text"""
        try:
            start_idx = text.find(start_marker)
            end_idx = text.find(end_marker)
            
            if start_idx == -1:
                return []
            
            if end_idx == -1:
                section = text[start_idx:]
            else:
                section = text[start_idx:end_idx]
            
            # Extract list items
            items = re.findall(r'[-•]\s*(.+)', section)
            return items if items else [section.strip()]
        except:
            return []


# ============================================================================
# Interface with distribution_mechanisms.py
# ============================================================================

def dialogue_based_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    **kwargs
) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
    """Dialogue-driven negotiation distribution (compatible with existing interface)
    
    Args:
        total_resources: Total resources
        agents: Agent list
        survival_needs: Survival needs
        round_number: Round number
        
    Returns:
        (distribution result, metadata)
    """
    negotiator = DialogueNegotiation(
        agents=agents,
        total_resources=total_resources,
        survival_needs=survival_needs,
        round_number=round_number
    )
    
    return negotiator.negotiate()


# ============================================================================
# Test Code
# ============================================================================

if __name__ == "__main__":
    print("Dialogue-Driven Negotiation Mechanism - Standalone Test")
    print("="*70)
    
    # Test code can be added here
    print("\nPlease call this module through simulation_runner.py")
