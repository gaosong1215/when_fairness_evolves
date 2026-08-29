"""
Discussion-Based Negotiation Mechanism (4-Phase)
Discussion-driven allocation negotiation mechanism(4Phase)

Four-Phase Process:
- Phase 1: Private Cross-Value Conversations (4 rounds) - Communicate privately across values
- Phase 2: Proposal Submission Based on Private Intelligence - Submit a plan based on private information
- Phase 3: Conflict Identification & Confirmation - Disagreement Identification and Acknowledgement
- Phase 4: Fine-tuning & Final Voting - Fine-tuning and final voting

Author: AI Assistant
Date: 2024-10-20
"""

from fairness_sim.llm_client import get_llm_client, get_model_name
import json
import re
import copy
import time
import random
from typing import Dict, List, Any, Tuple, Optional

# Setup DeepSeek client
client = get_llm_client()


class DiscussionBasedNegotiation:
    """Discussion-driven negotiation mechanism with 4 phases
    
    Process:
    Phase 1: Private Cross-Value Conversations (4 rounds)
    Phase 2: Proposal Submission Based on Private Intelligence
    Phase 3: Conflict Identification & Confirmation
    Phase 4: Fine-tuning & Final Voting
    """
    
    def __init__(
        self, 
        agents: List[Dict[str, Any]], 
        total_resources: Dict[str, float],
        survival_needs: Dict[int, Dict[str, float]],
        round_number: int = 1
    ):
        """Initialize discussion-based negotiation
        
        Args:
            agents: Agent list
            total_resources: Total resources {"grain": 250}
            survival_needs: Survival needs {agent_id: {"grain": amount}}
            round_number: Current round number
        """
        self.agents = agents
        self.total_resources = total_resources
        self.survival_needs = survival_needs
        self.round_number = round_number
        
        # Calculate basic info
        self.total_grain = total_resources.get("grain", 0)
        self.total_members = sum(agent["members"] for agent in agents)
        self.total_labor = sum(agent["labor_force"] for agent in agents)
        
        # Debug info
        total_survival = sum(survival_needs[a['id']].get('grain', 0) for a in agents)
        print(f"\n[INIT] 4-Phase Discussion Mechanism:")
        print(f"  Total resources: {self.total_grain:.1f} units")
        print(f"  Total survival needs: {total_survival:.1f} units")
        print(f"  Available for negotiation: {self.total_grain:.1f} units (full resource negotiation)")
        
        # Tracking structures
        self.private_conversations = {}  # {agent_id: [{partner_id, round, my_speech, partner_response, insights}]}
        self.submitted_proposals = []  # [{proposer, allocation, rationale}]
        self.conflict_points = []  # Identified conflicts
        self.final_candidates = []  # Final candidate proposals
        
    def negotiate(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """Main 4-phase negotiation process
        
        Returns:
            (final_allocation, metadata)
        """
        print("\n" + "="*80)
        print("💬 4-Phase Discussion-Based Negotiation Mechanism")
        print("="*80)
        
        try:
            # Phase 1: Private Cross-Value Conversations (4 rounds)
            print("\n" + "="*80)
            print("[PHASE 1: Private Cross-Value Conversations]")
            print("="*80)
            self._phase1_private_conversations()
            
            # Phase 2: Proposal Submission Based on Private Intelligence
            print("\n" + "="*80)
            print("[PHASE 2: Proposal Submission]")
            print("="*80)
            self._phase2_submit_proposals()
            
            # Phase 3: Conflict Identification & Confirmation
            print("\n" + "="*80)
            print("[PHASE 3: Conflict Identification & Confirmation]")
            print("="*80)
            self._phase3_identify_conflicts()
            
            # Phase 4: Fine-tuning & Final Voting
            print("\n" + "="*80)
            print("[PHASE 4: Fine-tuning & Final Voting]")
            print("="*80)
            final_allocation = self._phase4_finalize_voting()
            
            # Validate allocation
            self._validate_allocation(final_allocation)
            
            # Return results with detailed metadata for evaluation
            metadata = {
                "mechanism": "discussion_4phase",
                "total_private_conversations": sum(len(convs) for convs in self.private_conversations.values()),
                "submitted_proposals": self.submitted_proposals,  # 🆕 Full proposal data
                "conflict_points": self.conflict_points,  # 🆕 Full conflict data
                "final_candidates": self.final_candidates,  # 🆕 Full candidate data
                "private_conversations": self.private_conversations,  # 🆕 Full conversation history per agent
                "success": True  # Negotiation succeeded
            }
            
            return final_allocation, metadata
            
        except Exception as e:
            print(f"\n❌ Negotiation Failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_allocation(), {"error": str(e)}
    
    # ===== PHASE 1: Private Cross-Value Conversations =====
    
    def _phase1_private_conversations(self):
        """Phase 1: 4 rounds of private cross-value conversations
        
        Strategy:
        - Each agent has 4 private conversations with agents of different value types
        - Pairing rotates each round to cover all value type combinations
        - Conversations are bidirectional (both agents speak and respond)
        - Agents store insights privately for later use
        """
        print("\n🔒 Starting 4 rounds of private cross-value conversations...")
        print(f"   Total agents: {len(self.agents)}, Value types: 5")
        print(f"   Each agent will have 4 private conversations\n")
        
        # Initialize private conversation storage for each agent
        for agent in self.agents:
            self.private_conversations[agent['id']] = []
        
        # Generate pairing schedule for 4 rounds
        pairing_schedule = self._generate_pairing_schedule()
        
        # Execute 4 rounds
        for round_num in range(4):
            print(f"\n{'='*70}")
            print(f"  🗣️  Private Conversation Round {round_num + 1}/4")
            print(f"{'='*70}\n")
            
            pairs = pairing_schedule[round_num]
            print(f"  Pairs for this round: {len(pairs)} conversations\n")
            
            for pair_idx, (agent_a, agent_b) in enumerate(pairs, 1):
                print(f"  [{pair_idx}/{len(pairs)}] {agent_a['family_name']} ({agent_a['value_type']}) ↔ "
                      f"{agent_b['family_name']} ({agent_b['value_type']})")
                
                # Conduct bidirectional conversation
                conversation_result = self._conduct_private_conversation(
                    agent_a, agent_b, round_num
                )
                
                # Store conversation for both agents
                self.private_conversations[agent_a['id']].append({
                    'round': round_num + 1,
                    'partner_id': agent_b['id'],
                    'partner_name': agent_b['family_name'],
                    'partner_value': agent_b['value_type'],
                    'my_speech': conversation_result['a_to_b'],
                    'partner_response': conversation_result['b_to_a'],
                    'insights': conversation_result['a_insights']
                })
                
                self.private_conversations[agent_b['id']].append({
                    'round': round_num + 1,
                    'partner_id': agent_a['id'],
                    'partner_name': agent_a['family_name'],
                    'partner_value': agent_a['value_type'],
                    'my_speech': conversation_result['b_to_a'],
                    'partner_response': conversation_result['a_to_b'],
                    'insights': conversation_result['b_insights']
                })
                
                print(f"      ✓ Conversation completed and stored\n")
        
        # Summary
        print(f"\n✅ Phase 1 Complete!")
        print(f"   Total private conversations conducted: {sum(len(convs) for convs in self.private_conversations.values())}")
        for agent in self.agents:
            print(f"   - {agent['family_name']}: {len(self.private_conversations[agent['id']])} conversations")
    
    def _generate_pairing_schedule(self) -> List[List[Tuple[Dict, Dict]]]:
        """Generate pairing schedule for 4 rounds of cross-value conversations
        
        Returns:
            List of 4 rounds, each containing list of (agent_a, agent_b) pairs
        """
        # Group agents by value type
        value_groups = {}
        for agent in self.agents:
            vtype = agent['value_type']
            if vtype not in value_groups:
                value_groups[vtype] = []
            value_groups[vtype].append(agent)
        
        value_types = list(value_groups.keys())
        print(f"  Value type groups: {value_types}")
        for vtype in value_types:
            print(f"    {vtype}: {[a['family_name'] for a in value_groups[vtype]]}")
        
        # Generate 4 rounds of pairings
        # Strategy: Each round, pair each value type with a different value type
        # Rotate to ensure each agent talks to 4 different value types
        
        schedule = []
        used_pairs = set()  # Track (agent_id, agent_id) pairs to avoid duplicates
        
        for round_num in range(4):
            round_pairs = []
            round_used = set()  # Agents used in this round
            
            # Shuffle agents to get variety
            all_agents_shuffled = self.agents.copy()
            random.shuffle(all_agents_shuffled)
            
            for agent in all_agents_shuffled:
                if agent['id'] in round_used:
                    continue
                
                # Find a partner with different value type that hasn't been paired before
                my_conversations = self.private_conversations.get(agent['id'], [])
                talked_to = {conv['partner_id'] for conv in my_conversations}
                
                # Find candidate partners
                candidates = [
                    a for a in self.agents
                    if a['value_type'] != agent['value_type']  # Different value type
                    and a['id'] not in talked_to  # Haven't talked before
                    and a['id'] not in round_used  # Not used in this round
                    and a['id'] != agent['id']  # Not self
                ]
                
                if candidates:
                    partner = random.choice(candidates)
                    round_pairs.append((agent, partner))
                    round_used.add(agent['id'])
                    round_used.add(partner['id'])
                    
                    # Mark as talked in the tracking structure
                    pair_key = tuple(sorted([agent['id'], partner['id']]))
                    used_pairs.add(pair_key)
            
            schedule.append(round_pairs)
            print(f"  Round {round_num + 1}: {len(round_pairs)} pairs scheduled")
        
        return schedule
    
    def _conduct_private_conversation(
        self, 
        agent_a: Dict, 
        agent_b: Dict, 
        round_num: int
    ) -> Dict[str, str]:
        """Conduct a private conversation between two agents
        
        Args:
            agent_a: First agent
            agent_b: Second agent
            round_num: Conversation round number (0-3)
        
        Returns:
            {
                'a_to_b': Agent A's speech,
                'b_to_a': Agent B's response,
                'a_insights': Agent A's insights from conversation,
                'b_insights': Agent B's insights from conversation
            }
        """
        # Agent A speaks first
        a_speech = self._get_private_speech(agent_a, agent_b, round_num, is_first=True)
        
        # Small delay for API
        time.sleep(0.3)
        
        # Agent B responds
        b_speech = self._get_private_speech(agent_b, agent_a, round_num, is_first=False, partner_speech=a_speech)
        
        # Both agents extract insights (optional, could skip to reduce LLM calls)
        # For now, we'll just use the speeches themselves as insights
        a_insights = f"Learned that {agent_b['family_name']} holds {agent_b['value_type']} values"
        b_insights = f"Learned that {agent_a['family_name']} holds {agent_a['value_type']} values"
        
        print(f"        A→B: {a_speech[:80]}...")
        print(f"        B→A: {b_speech[:80]}...")
        
        return {
            'a_to_b': a_speech,
            'b_to_a': b_speech,
            'a_insights': a_insights,
            'b_insights': b_insights
        }
    
    def _get_private_speech(
        self, 
        agent: Dict, 
        partner: Dict, 
        round_num: int, 
        is_first: bool,
        partner_speech: str = None
    ) -> str:
        """Get an agent's private conversation speech
        
        Args:
            agent: The speaking agent
            partner: The conversation partner
            round_num: Round number (0-3)
            is_first: Whether this agent speaks first
            partner_speech: Partner's speech (if responding)
        
        Returns:
            Agent's speech text
        """
        agent_survival = self.survival_needs[agent['id']]['grain']
        partner_survival = self.survival_needs[partner['id']]['grain']
        total_survival = sum(self.survival_needs[a['id']]['grain'] for a in self.agents)
        
        # Get previous conversations for context
        previous_convs = self.private_conversations.get(agent['id'], [])
        conv_context = ""
        if previous_convs:
            conv_context = "\n[Your Previous Private Conversations]\n"
            for conv in previous_convs[-2:]:  # Last 2 conversations
                conv_context += f"- With {conv['partner_name']} ({conv['partner_value']}): {conv['insights']}\n"
        
        if is_first:
            # Agent A speaks first
            prompt = f"""You are {agent['family_name']} family ({agent['value_type']} values, {agent['members']} people, {agent['labor_force']} laborers).

[Private Conversation Context]
You are having a PRIVATE one-on-one conversation with {partner['family_name']} family.
- Their value type: {partner['value_type']} (different from yours!)
- Their family: {partner['members']} people, {partner['labor_force']} laborers
- Their survival needs: {partner_survival:.1f} units

[Your Value Type: {agent['value_type']}]
- **Egalitarian**: Fairness = equal per capita distribution
- **Needs-based**: Fairness = allocation by actual needs, prioritizing vulnerable groups
- **Merit-based**: Fairness = distribution by contribution
- **Altruistic**: Fairness = prioritizing community welfare
- **Pragmatic**: Fairness = balancing efficiency and equity

[Community Context]
- Total resources to allocate: {self.total_grain:.1f} units
- Total survival needs: {total_survival:.1f} units ({total_survival/self.total_grain*100:.1f}% of total)
- Your survival needs: {agent_survival:.1f} units
{conv_context}
[Conversation Round {round_num + 1}/4]
This is a private conversation. What you learn here is YOUR strategic intelligence.

[Your Objectives]
1. Understand their bottom line and priorities
2. Explore potential cooperation or conflicts
3. Gather information advantage for later public negotiation
4. Test if they can be convinced or need to be opposed

Please start the conversation (100 words max, be strategic):
"""
        else:
            # Agent B responds to Agent A
            prompt = f"""You are {agent['family_name']} family ({agent['value_type']} values, {agent['members']} people, {agent['labor_force']} laborers).

[Private Conversation Context]
You are having a PRIVATE one-on-one conversation with {partner['family_name']} family.
- Their value type: {partner['value_type']} (different from yours!)
- Their family: {partner['members']} people, {partner['labor_force']} laborers

[Their Message to You]
{partner_speech}

[Your Value Type: {agent['value_type']}]
Your fairness understanding is based on {agent['value_type']} values.

[Community Context]
- Total resources: {self.total_grain:.1f} units
- Your survival needs: {agent_survival:.1f} units
{conv_context}
[Your Response Strategy]
- Be honest about your position but also strategic
- Seek common ground if beneficial
- Defend your interests while gathering information

Please respond (100 words max):
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family with {agent['value_type']} values in a resource allocation negotiation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
                timeout=60.0
            )
            
            speech = response.choices[0].message.content.strip()
            return speech
            
        except Exception as e:
            print(f"      ⚠️  LLM call failed: {e}")
            return f"As a {agent['value_type']} family, I believe in {agent['value_type']} distribution principles."
    
    # ===== PHASE 2: Proposal Submission =====
    
    def _phase2_submit_proposals(self):
        """Phase 2: Each agent submits 1-2 proposals based on private intelligence"""
        print("\n📝 Each agent submits proposals based on private intelligence...\n")
        
        for agent in self.agents:
            print(f"  {agent['family_name']} ({agent['value_type']}) submitting proposal...")
            
            # Generate proposal based on private conversations
            proposal = self._generate_proposal_from_intelligence(agent)
            
            if proposal:
                self.submitted_proposals.append(proposal)
                print(f"    ✓ Proposal submitted")
            else:
                print(f"    ⚠️  Failed to generate proposal")
        
        print(f"\n✅ Phase 2 Complete!")
        print(f"   Total proposals submitted: {len(self.submitted_proposals)}")
        
        # Display all proposals
        print(f"\n📋 Submitted Proposals Summary:")
        for i, prop in enumerate(self.submitted_proposals, 1):
            print(f"\n  [{i}] {prop['proposer']} ({prop['proposer_value']}):")
            print(f"      Rationale: {prop['rationale'][:100]}...")
            # Show allocation summary
            allocations = [prop['allocation'][aid]['grain'] for aid in sorted(prop['allocation'].keys())]
            print(f"      Allocation range: {min(allocations):.1f} - {max(allocations):.1f} units")
            print(f"      Variance: {max(allocations) - min(allocations):.1f}")
    
    def _generate_proposal_from_intelligence(self, agent: Dict) -> Optional[Dict]:
        """Generate a proposal based on agent's private intelligence
        
        Args:
            agent: The proposing agent
        
        Returns:
            {
                'proposer': family_name,
                'proposer_id': agent_id,
                'proposer_value': value_type,
                'allocation': {agent_id: {'grain': amount}},
                'rationale': explanation
            }
        """
        # Gather private intelligence
        convs = self.private_conversations.get(agent['id'], [])
        intel_summary = ""
        if convs:
            intel_summary = "\n[Your Private Intelligence]\n"
            for conv in convs:
                intel_summary += f"- {conv['partner_name']} ({conv['partner_value']}): \n"
                intel_summary += f"  Their speech: {conv['partner_response'][:100]}...\n"
                intel_summary += f"  Your insight: {conv['insights']}\n"
        
        # Build family info for proposal
        family_info = "\n[All Families]\n"
        for a in self.agents:
            survival = self.survival_needs[a['id']]['grain']
            family_info += f"- {a['family_name']}: {a['members']} people, {a['labor_force']} laborers, "
            family_info += f"{survival:.1f} survival needs ({a['value_type']} values)\n"
        
        agent_survival = self.survival_needs[agent['id']]['grain']
        total_survival = sum(self.survival_needs[a['id']]['grain'] for a in self.agents)
        
        prompt = f"""You are {agent['family_name']} family ({agent['value_type']} values, {agent['members']} people, {agent['labor_force']} laborers).

[Situation]
You've completed 4 private conversations and now must submit a COMPLETE allocation proposal.
- Total resources: {self.total_grain:.1f} units
- Total survival needs: {total_survival:.1f} units
- Your survival needs: {agent_survival:.1f} units

{intel_summary}

{family_info}

[Your Task]
Based on your private intelligence and {agent['value_type']} values, propose a complete allocation plan.

**IMPORTANT**: Your proposal must:
1. List EXACTLY all {len(self.agents)} families with specific amounts
2. Total must equal {self.total_grain:.1f} units
3. Reflect your strategic understanding from private conversations
4. Be defensible in public negotiation

Format your response EXACTLY as:
RATIONALE: [Your 2-sentence explanation of why this allocation is fair]

ALLOCATION:
{self.agents[0]['family_name']} = X.X units
{self.agents[1]['family_name']} = X.X units
[... all families ...]

Please propose:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family with {agent['value_type']} values submitting a resource allocation proposal."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=60.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse response
            rationale_match = re.search(r'RATIONALE:\s*(.+?)(?=ALLOCATION:)', content, re.DOTALL)
            rationale = rationale_match.group(1).strip() if rationale_match else "No rationale provided"
            
            # Parse allocation
            allocation_section = re.search(r'ALLOCATION:(.+)', content, re.DOTALL)
            if allocation_section:
                allocation = self._parse_allocation_text(allocation_section.group(1))
                
                if allocation and len(allocation) == len(self.agents):
                    # Normalize to exact total
                    allocation = self._normalize_allocation(allocation, self.total_grain)
                    
                    return {
                        'proposer': agent['family_name'],
                        'proposer_id': agent['id'],
                        'proposer_value': agent['value_type'],
                        'allocation': allocation,
                        'rationale': rationale
                    }
            
            return None
            
        except Exception as e:
            print(f"      ⚠️  LLM call failed: {e}")
            return None
    
    def _parse_allocation_text(self, text: str) -> Optional[Dict[int, Dict[str, float]]]:
        """Parse allocation from text like 'Smith = 20.5 units'"""
        allocation = {}
        
        # Find all family = number patterns
        for agent in self.agents:
            pattern = rf"{re.escape(agent['family_name'])}\s*=\s*([\d.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                allocation[agent['id']] = {'grain': amount}
        
        return allocation if len(allocation) == len(self.agents) else None
    
    def _normalize_allocation(self, allocation: Dict[int, Dict[str, float]], target_total: float) -> Dict[int, Dict[str, float]]:
        """Normalize allocation to exactly match target total"""
        current_total = sum(allocation[aid]['grain'] for aid in allocation)
        
        if current_total == 0:
            # Equal distribution fallback
            per_family = target_total / len(allocation)
            return {aid: {'grain': per_family} for aid in allocation}
        
        # Scale proportionally
        ratio = target_total / current_total
        normalized = {}
        
        for aid in allocation:
            normalized[aid] = {'grain': allocation[aid]['grain'] * ratio}
        
        # Fix rounding error on last agent
        actual_total = sum(normalized[aid]['grain'] for aid in normalized)
        diff = target_total - actual_total
        last_id = list(normalized.keys())[-1]
        normalized[last_id]['grain'] += diff
        
        return normalized
    
    # ===== PHASE 3: Conflict Identification =====
    
    def _phase3_identify_conflicts(self):
        """Phase 3: Identify conflicts and seek confirmation/compromise"""
        print("\n🔍 Analyzing submitted proposals for conflicts...\n")
        
        if len(self.submitted_proposals) < 2:
            print("  ⚠️  Not enough proposals to identify conflicts")
            return
        
        # Analyze variance in allocations for each family
        conflicts = self._analyze_allocation_conflicts()
        
        self.conflict_points = conflicts
        
        if conflicts:
            print(f"  Found {len(conflicts)} conflict points:\n")
            for i, conflict in enumerate(conflicts, 1):
                print(f"  [{i}] {conflict['family']}: {conflict['description']}")
                print(f"      Range: {conflict['min']:.1f} - {conflict['max']:.1f} units (variance: {conflict['variance']:.1f})")
        
        # Ask agents to respond to conflicts (optional, can skip to reduce LLM calls)
        print(f"\n  Asking agents to respond to identified conflicts...")
        
        for agent in self.agents:
            relevant_conflicts = [c for c in conflicts if c['family'] == agent['family_name']]
            if relevant_conflicts:
                response = self._get_conflict_response(agent, relevant_conflicts)
                print(f"    {agent['family_name']}: {response[:80]}...")
        
        print(f"\n✅ Phase 3 Complete!")
    
    def _analyze_allocation_conflicts(self) -> List[Dict]:
        """Analyze conflicts across all submitted proposals"""
        conflicts = []
        
        for agent in self.agents:
            agent_id = agent['id']
            allocations_for_agent = []
            
            for proposal in self.submitted_proposals:
                if agent_id in proposal['allocation']:
                    allocations_for_agent.append(proposal['allocation'][agent_id]['grain'])
            
            if len(allocations_for_agent) >= 2:
                min_alloc = min(allocations_for_agent)
                max_alloc = max(allocations_for_agent)
                variance = max_alloc - min_alloc
                
                # Consider it a conflict if variance > 10% of total resources
                if variance > self.total_grain * 0.10:
                    conflicts.append({
                        'family': agent['family_name'],
                        'family_id': agent_id,
                        'min': min_alloc,
                        'max': max_alloc,
                        'variance': variance,
                        'description': f"Proposals range from {min_alloc:.1f} to {max_alloc:.1f} units"
                    })
        
        return conflicts
    
    def _get_conflict_response(self, agent: Dict, conflicts: List[Dict]) -> str:
        """Get agent's response to conflicts about their allocation"""
        conflict_desc = "\n".join([f"- {c['description']}" for c in conflicts])
        
        prompt = f"""You are {agent['family_name']} family ({agent['value_type']} values).

[Conflict Alert]
Different proposals suggest very different allocations for your family:
{conflict_desc}

[Your Position]
Given your {agent['value_type']} values and the community situation, what is your response?
- Do you accept the lower end, higher end, or somewhere in between?
- What is your bottom line?

Please respond briefly (50 words):
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family responding to allocation conflicts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"I maintain my {agent['value_type']} position."
    
    # ===== PHASE 4: Fine-tuning & Voting =====
    
    def _phase4_finalize_voting(self) -> Dict[int, Dict[str, float]]:
        """Phase 4: Generate final candidates and vote"""
        print("\n🗳️  Generating final candidate proposals and voting...\n")
        
        # Generate final candidates from submitted proposals
        self.final_candidates = self._generate_final_candidates()
        
        print(f"  Final candidates: {len(self.final_candidates)}\n")
        
        for i, candidate in enumerate(self.final_candidates, 1):
            print(f"  [{i}] {candidate['name']}")
            print(f"      Source: {candidate['source']}")
            allocations = [candidate['allocation'][aid]['grain'] for aid in sorted(candidate['allocation'].keys())]
            print(f"      Range: {min(allocations):.1f} - {max(allocations):.1f} units\n")
        
        # Voting
        print(f"  Conducting final vote across {len(self.agents)} agents...\n")
        
        votes = self._conduct_final_vote()
        
        # Determine winner
        winner_name = max(votes, key=votes.get)
        winner = next(c for c in self.final_candidates if c['name'] == winner_name)
        
        print(f"\n📊 Voting Results:")
        for name, score in sorted(votes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {name}: {score:.2f}/5.0 average")
        
        print(f"\n🏆 Winner: {winner_name}")
        print(f"   Average score: {votes[winner_name]:.2f}/5.0\n")
        
        # Display final allocation
        self._display_final_allocation(winner['allocation'])
        
        return winner['allocation']
    
    def _generate_final_candidates(self) -> List[Dict]:
        """Generate final candidate proposals from submissions"""
        candidates = []
        
        # Take top submitted proposals (max 6)
        for i, proposal in enumerate(self.submitted_proposals[:6], 1):
            candidates.append({
                'name': f"{proposal['proposer']}_Proposal",
                'source': f"{proposal['proposer']} ({proposal['proposer_value']})",
                'allocation': proposal['allocation'],
                'rationale': proposal['rationale']
            })
        
        # Add backup proposals if needed
        if len(candidates) < 3:
            # Add equal distribution
            equal_alloc = {a['id']: {'grain': self.total_grain / len(self.agents)} for a in self.agents}
            candidates.append({
                'name': 'Equal_Distribution',
                'source': 'System (backup)',
                'allocation': equal_alloc,
                'rationale': 'Equal per-family distribution as fallback'
            })
            
            # Add needs-based
            total_survival = sum(self.survival_needs[a['id']]['grain'] for a in self.agents)
            if total_survival > 0 and total_survival < self.total_grain:
                needs_alloc = {}
                surplus = self.total_grain - total_survival
                for a in self.agents:
                    base = self.survival_needs[a['id']]['grain']
                    extra = surplus * (self.survival_needs[a['id']]['grain'] / total_survival)
                    needs_alloc[a['id']] = {'grain': base + extra}
                candidates.append({
                    'name': 'Needs_Based',
                    'source': 'System (backup)',
                    'allocation': needs_alloc,
                    'rationale': 'Proportional to needs'
                })
        
        return candidates
    
    def _conduct_final_vote(self) -> Dict[str, float]:
        """Conduct final voting on candidates
        
        Returns:
            {candidate_name: average_score}
        """
        all_scores = {c['name']: [] for c in self.final_candidates}
        
        for agent in self.agents:
            for candidate in self.final_candidates:
                score = self._score_candidate(agent, candidate)
                all_scores[candidate['name']].append(score)
        
        # Calculate averages
        avg_scores = {}
        for name, scores in all_scores.items():
            avg_scores[name] = sum(scores) / len(scores) if scores else 0.0
        
        return avg_scores
    
    def _score_candidate(self, agent: Dict, candidate: Dict) -> float:
        """Agent scores a candidate proposal (1-5)"""
        my_allocation = candidate['allocation'][agent['id']]['grain']
        my_survival = self.survival_needs[agent['id']]['grain']
        my_per_capita = my_allocation / agent['members']
        
        # Build context
        convs = self.private_conversations.get(agent['id'], [])
        intel_context = ""
        if convs:
            intel_context = "\n[Your Private Intelligence]\n"
            for conv in convs[:2]:
                intel_context += f"- {conv['partner_name']}: {conv['insights']}\n"
        
        prompt = f"""You are {agent['family_name']} family ({agent['value_type']} values, {agent['members']} people).

[Proposal to Evaluate]
Name: {candidate['name']}
Source: {candidate['source']}
Rationale: {candidate['rationale']}

Your allocation: {my_allocation:.1f} units ({my_per_capita:.2f} per person)
Your survival needs: {my_survival:.1f} units
{intel_context}

[Your Task]
Rate this proposal from 1-5 based on:
- Does it align with your {agent['value_type']} values?
- Does it meet your family's needs?
- Is it consistent with what you learned in private conversations?

Reply with ONLY a number 1-5:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family scoring a resource allocation proposal. Reply with only a number 1-5."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            score = float(re.search(r'[1-5]', score_text).group())
            return max(1.0, min(5.0, score))
            
        except:
            # Fallback heuristic
            if my_allocation >= my_survival:
                return 3.0
            else:
                return 2.0
    
    def _display_final_allocation(self, allocation: Dict[int, Dict[str, float]]):
        """Display the final allocation"""
        print(f"  📋 Final Allocation:")
        for agent in self.agents:
            allocated = allocation[agent['id']]['grain']
            survival = self.survival_needs[agent['id']]['grain']
            per_capita = allocated / agent['members']
            
            if allocated >= survival:
                surplus = allocated - survival
                print(f"     {agent['family_name']}: {allocated:.1f} units ({per_capita:.2f}/person) "
                      f"[✓ {surplus:.1f} above survival]")
            else:
                deficit = survival - allocated
                print(f"     {agent['family_name']}: {allocated:.1f} units ({per_capita:.2f}/person) "
                      f"[⚠️  {deficit:.1f} BELOW survival!]")
    
    # ===== Utilities =====
    
    def _validate_allocation(self, allocation: Dict[int, Dict[str, float]]):
        """Validate final allocation meets survival needs"""
        print(f"\n🔍 Validating final allocation...")
        
        total_allocated = sum(allocation[a['id']]['grain'] for a in self.agents)
        print(f"  Total allocated: {total_allocated:.1f} / {self.total_grain:.1f} units")
        
        violations = []
        for agent in self.agents:
            allocated = allocation[agent['id']]['grain']
            survival = self.survival_needs[agent['id']]['grain']
            if allocated < survival:
                deficit = survival - allocated
                violations.append(f"{agent['family_name']}: {deficit:.1f} units below survival")
        
        if violations:
            print(f"\n  ⚠️  Survival violations detected:")
            for v in violations:
                print(f"     - {v}")
        else:
            print(f"  ✅ All families meet survival needs")
    
    def _fallback_allocation(self) -> Dict[int, Dict[str, float]]:
        """Fallback to equal distribution if negotiation fails"""
        print("\n⚠️  Using fallback: equal distribution")
        per_family = self.total_grain / len(self.agents)
        return {agent['id']: {'grain': per_family} for agent in self.agents}


# ===== Wrapper Function for Compatibility =====

def discussion_based_distribution(
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1
) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
    """
    Wrapper function for 4-phase discussion-based negotiation mechanism
    (Compatible with simulation_runner.py interface)
    
    Args:
        agents: List of agent dictionaries
        total_resources: Total available resources {"grain": amount}
        survival_needs: Survival needs per agent {agent_id: {"grain": amount}}
        round_number: Current simulation round
    
    Returns:
        (allocation_result, metadata)
        - allocation_result: {agent_id: {"grain": amount}}
        - metadata: {mechanism, statistics, etc.}
    """
    negotiator = DiscussionBasedNegotiation(
        agents=agents,
        total_resources=total_resources,
        survival_needs=survival_needs,
        round_number=round_number
    )
    
    allocation, metadata = negotiator.negotiate()
    
    return allocation, metadata
