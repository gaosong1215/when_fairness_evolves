"""
Progressive Consensus Negotiation Mechanism
Progressive Consensus Consultation Mechanism - A True Dynamic Negotiation Process

Core Design:
- Multi-round proposal-feedback-adjustment cycles
- Agents see ALL history in EVERY prompt (no memory between calls)
- Dynamic coalition formation
- Gradual convergence to consensus
- Real negotiation with compromise and adjustment

Author: AI Assistant
Date: 2024-10-21
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


class ProgressiveConsensusNegotiation:
    """Progressive consensus negotiation - gradual convergence through multiple rounds
    
    Process:
    Round 1: Initial Proposals (10 agents submit proposals)
    Round 2-4: Discuss-Feedback-Adjust (agents comment, adjust proposals, form coalitions)
    Round 5: Final Consensus Vote (vote on surviving proposals)
    """
    
    def __init__(
        self,
        agents: List[Dict[str, Any]],
        total_resources: Dict[str, float],
        survival_needs: Dict[int, Dict[str, float]],
        round_number: int = 1
    ):
        """Initialize progressive consensus negotiation"""
        self.agents = agents
        self.total_resources = total_resources
        self.survival_needs = survival_needs
        self.round_number = round_number
        
        self.total_grain = total_resources.get("grain", 0)
        self.total_members = sum(agent["members"] for agent in agents)
        self.total_labor = sum(agent["labor_force"] for agent in agents)
        
        # Tracking structures
        self.proposals = {}  # {proposal_id: {proposer, allocation, rationale, supporters, round_created}}
        self.comments_history = []  # [{round, agent, proposal_id, comment, action}]
        self.adjustments_history = []  # [{round, agent, old_proposal, new_proposal, reason}]
        self.coalitions = {}  # {coalition_id: {members, shared_proposal}}
        
        print(f"\n[INIT] Progressive Consensus Negotiation:")
        print(f"  Total resources: {self.total_grain:.1f} units")
        print(f"  Agents: {len(agents)}")
        print(f"  Max rounds: 5")
    
    def negotiate(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """Main progressive consensus process
        
        Returns:
            (final_allocation, metadata)
        """
        print("\n" + "="*80)
        print("🔄 Progressive Consensus Negotiation Mechanism")
        print("="*80)
        
        try:
            # Round 1: Initial Proposals
            print("\n" + "="*80)
            print("[ROUND 1: Initial Proposals]")
            print("="*80)
            self._round1_initial_proposals()
            
            # Rounds 2-4: Discuss-Feedback-Adjust
            for nego_round in range(2, 5):
                print("\n" + "="*80)
                print(f"[ROUND {nego_round}: Discuss-Feedback-Adjust]")
                print("="*80)
                self._negotiation_round(nego_round)
            
            # Round 5: Final Consensus Vote
            print("\n" + "="*80)
            print("[ROUND 5: Final Consensus Vote]")
            print("="*80)
            final_allocation = self._round5_final_vote()
            
            # Validate
            self._validate_allocation(final_allocation)
            
            # Metadata with complete negotiation history
            metadata = {
                "mechanism": "progressive_consensus",
                "total_proposals": len(self.proposals),
                "total_comments": len(self.comments_history),
                "total_adjustments": len(self.adjustments_history),
                "coalitions_formed": len(self.coalitions),
                "proposals": self.proposals,  # All proposals with status
                "comments_history": self.comments_history,  # All speeches/comments
                "adjustments_history": self.adjustments_history,  # All proposal adjustments
                "success": True
            }
            
            return final_allocation, metadata
            
        except Exception as e:
            print(f"\n❌ Negotiation Failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_allocation(), {"error": str(e)}
    
    # ===== ROUND 1: Initial Proposals =====
    
    def _round1_initial_proposals(self):
        """Round 1: Each agent submits initial proposal"""
        print("\n📝 Each agent submits their initial allocation proposal...\n")
        
        for agent in self.agents:
            print(f"  {agent['family_name']} ({agent['value_type']}) proposing...")
            
            proposal = self._get_initial_proposal(agent)
            
            if proposal:
                proposal_id = f"P{agent['id']}_R1"
                self.proposals[proposal_id] = {
                    'id': proposal_id,
                    'proposer_id': agent['id'],
                    'proposer_name': agent['family_name'],
                    'proposer_value': agent['value_type'],
                    'allocation': proposal['allocation'],
                    'rationale': proposal['rationale'],
                    'supporters': [agent['id']],  # Self-support
                    'round_created': 1,
                    'round_last_modified': 1,
                    'status': 'active'
                }
                print(f"    ✓ Proposal {proposal_id} submitted")
            else:
                print(f"    ⚠️  Failed to generate proposal")
        
        print(f"\n✅ Round 1 Complete! {len(self.proposals)} proposals submitted")
        self._display_proposals_summary()
    
    def _get_initial_proposal(self, agent: Dict) -> Optional[Dict]:
        """Get agent's initial proposal
        
        KEY: This is the FIRST LLM call for this agent - no history yet
        """
        agent_survival = self.survival_needs[agent['id']]['grain']
        total_survival = sum(self.survival_needs[a['id']]['grain'] for a in self.agents)
        
        # Build family info
        family_info = self._build_family_info_text()
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}, {agent['value_type']} values, {agent['members']} people, {agent['labor_force']} laborers).

[Negotiation Context]
This is Round 1 of a 5-round progressive consensus negotiation. You will submit an initial allocation proposal.

[Community Resources]
- Total resources: {self.total_grain:.1f} units
- Total survival needs: {total_survival:.1f} units
- Your survival needs: {agent_survival:.1f} units

[Your Values: {agent['value_type']}]
- Egalitarian: Equal per capita distribution
- Needs-based: Prioritize vulnerable families
- Merit-based: Distribution by labor contribution
- Altruistic: Maximize community welfare
- Pragmatic: Balance efficiency and equity

{family_info}

[Your Task]
Propose a complete allocation plan that reflects your {agent['value_type']} values.

**IMPORTANT**: 
1. List ALL {len(self.agents)} families with specific amounts
2. Total MUST equal {self.total_grain:.1f} units
3. Provide 2-3 sentence rationale

**Format**:
RATIONALE: [Your explanation]

ALLOCATION:
{self.agents[0]['family_name']} = X.X
{self.agents[1]['family_name']} = X.X
[... all families ...]

Please propose:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family proposing a resource allocation plan."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse
            rationale_match = re.search(r'RATIONALE:\s*(.+?)(?=ALLOCATION:)', content, re.DOTALL)
            rationale = rationale_match.group(1).strip() if rationale_match else "No rationale"
            
            allocation_section = re.search(r'ALLOCATION:(.+)', content, re.DOTALL)
            if allocation_section:
                allocation = self._parse_allocation_text(allocation_section.group(1))
                if allocation and len(allocation) == len(self.agents):
                    allocation = self._normalize_allocation(allocation)
                    return {'allocation': allocation, 'rationale': rationale}
            
            return None
            
        except Exception as e:
            print(f"      ⚠️  LLM call failed: {e}")
            return None
    
    # ===== ROUNDS 2-4: Discuss-Feedback-Adjust =====
    
    def _negotiation_round(self, round_num: int):
        """Rounds 2-4: Limited Free Speech Discussion
        
        Process:
        1. Ask all agents which cycles they want to speak in
        2. Run 3 cycles of discussion
        3. In each cycle, agents speak sequentially (max 5 per cycle)
        4. After all cycles, collect proposal adjustments
        """
        print(f"\n🔄 Negotiation Round {round_num}: Limited Free Speech Discussion\n")
        
        # Step 1: Ask all agents their speaking intentions (1 LLM call per agent)
        print(f"  📋 Phase 1: Collecting speaking intentions...\n")
        speaking_plans = {}
        for agent in self.agents:
            plan = self._get_speaking_plan(agent, round_num)
            speaking_plans[agent['id']] = plan
            if plan['cycles']:
                print(f"    {agent['family_name']}: wants to speak in cycle {plan['cycles']}")
            else:
                print(f"    {agent['family_name']}: will observe silently")
        
        # Step 2: Run 3 cycles of discussion
        print(f"\n  💬 Phase 2: Multi-cycle Discussion...\n")
        round_speeches = []
        
        for cycle in range(1, 4):  # Cycles 1, 2, 3
            print(f"\n  {'='*60}")
            print(f"  Cycle {cycle}/3")
            print(f"  {'='*60}\n")
            
            # Get agents who want to speak in this cycle
            cycle_speakers = [
                agent for agent in self.agents 
                if cycle in speaking_plans[agent['id']]['cycles']
            ]
            
            if not cycle_speakers:
                print(f"    [Silence] No one speaks in this cycle\n")
                continue
            
            # Limit to 5 speakers per cycle (first come first serve by original order)
            if len(cycle_speakers) > 5:
                cycle_speakers = cycle_speakers[:5]
                print(f"    ⚠️  Limiting to first 5 speakers (capacity reached)\n")
            
            print(f"    Speakers this cycle: {len(cycle_speakers)}")
            
            # Sequential speaking within this cycle
            for i, agent in enumerate(cycle_speakers, 1):
                print(f"    [{i}/{len(cycle_speakers)}] {agent['family_name']} speaking...")
                
                speech = self._get_cycle_speech(
                    agent, 
                    round_num, 
                    cycle,
                    round_speeches  # All speeches in this round so far
                )
                
                if speech:
                    round_speeches.append(speech)
                    self.comments_history.append(speech)
                    print(f"        ✓ Speech recorded ({len(speech['content'])} chars)")
        
        print(f"\n  📊 Round {round_num} Discussion Summary:")
        print(f"    Total speeches: {len(round_speeches)}")
        print(f"    Participating agents: {len(set(s['agent_id'] for s in round_speeches))}/{len(self.agents)}")
        
        # Step 3: Proposal adjustments (after seeing all discussion)
        print(f"\n  🔧 Phase 3: Proposal Adjustments...\n")
        round_adjustments = []
        for agent in self.agents:
            agent_proposal_id = self._find_agent_proposal(agent['id'])
            if agent_proposal_id:
                print(f"    {agent['family_name']} considering adjustment...")
                adjustment = self._get_agent_adjustment(agent, round_num)
                if adjustment and adjustment['action'] != 'maintain':
                    round_adjustments.append(adjustment)
                    self.adjustments_history.append(adjustment)
                    print(f"      ✓ {adjustment['action']}")
        
        # Step 4: Apply adjustments
        self._apply_adjustments(round_adjustments, round_num)
        
        print(f"\n✅ Round {round_num} Complete!")
        self._display_proposals_summary()
        
        # Check for early consensus
        if self._check_consensus():
            print(f"\n🎯 Early consensus reached! Skipping remaining rounds...")
            return True
        
        return False
    
    def _get_speaking_plan(self, agent: Dict, round_num: int) -> Dict:
        """Ask agent which cycles they want to speak in (1 LLM call per agent per round)
        
        KEY: Provide complete history so agent can plan strategically
        """
        history_text = self._build_negotiation_history_text(agent['id'], round_num)
        proposals_text = self._build_proposals_text()
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}, {agent['value_type']} values).

[Negotiation Status]Round {round_num}/5

[Complete History]
{history_text}

[Current Active Proposals]
{proposals_text}

[This Round Structure]
This round has 3 discussion cycles. You must decide which cycles to speak in:
- Cycle 1: Early discussion (speak first to lead direction)
- Cycle 2: Mid discussion (respond to Cycle 1, propose compromises)  
- Cycle 3: Late discussion (final arguments before adjustment phase)

Each cycle limited to 5 speakers (first-come-first-served).

[Your Decision]
Choose which cycle(s) to speak in based on your strategy:
- Speak early (Cycle 1) to propose ideas
- Speak mid (Cycle 2) to respond and negotiate
- Speak late (Cycle 3) for final push
- Or observe silently if you're satisfied

Reply with cycle numbers (comma-separated) or "NONE":
Examples: "1,3" or "2" or "NONE"
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family planning when to speak. Reply with cycle numbers like '1,2' or 'NONE'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=20
            )
            
            answer = response.choices[0].message.content.strip().upper()
            
            # Parse cycles
            cycles = []
            if 'NONE' not in answer:
                for num in ['1', '2', '3']:
                    if num in answer:
                        cycles.append(int(num))
            
            return {'cycles': cycles}
            
        except Exception as e:
            print(f"      ⚠️  Speaking plan failed: {e}")
            return {'cycles': []}
    
    def _get_cycle_speech(self, agent: Dict, round_num: int, cycle: int, 
                          round_speeches: List[Dict]) -> Optional[Dict]:
        """Get agent's speech in a specific cycle
        
        KEY: Agent can see ALL previous speeches in THIS round (true interaction!)
        """
        # Build complete history including THIS round's speeches so far
        history_text = self._build_negotiation_history_text(agent['id'], round_num)
        
        # Build THIS round's discussion so far (KEY for interaction)
        current_round_discussion = ""
        if round_speeches:
            current_round_discussion = f"\n[THIS ROUND - Live Discussion]\n"
            current_round_discussion += f"Speeches so far ({len(round_speeches)} total):\n\n"
            
            for i, speech in enumerate(round_speeches, 1):
                cycle_num = speech.get('cycle', 0)
                current_round_discussion += f"[{i}] Cycle {cycle_num} - {speech['agent_name']}:\n"
                current_round_discussion += f"    {speech['content'][:150]}...\n\n"
        else:
            current_round_discussion = "\n[THIS ROUND - Live Discussion]\nNo one has spoken yet. You are first!\n"
        
        proposals_text = self._build_proposals_text()
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}, {agent['value_type']} values).

[Negotiation Status]Round {round_num}/5, Cycle {cycle}/3

[Previous Rounds History]
{history_text}
{current_round_discussion}

[Current Active Proposals]
{proposals_text}

[Your Turn to Speak - Cycle {cycle}]
You chose to speak in this cycle. Now it's your turn.

You can:
- Propose new ideas or modifications
- Respond to what others just said
- Form alliances ("I support X's proposal if...")
- Defend your position
- Suggest compromises

Consider:
- What have others said in THIS round? Can you respond?
- Does your {agent['value_type']} position need defending?
- Is there room for strategic compromise?

Please speak (within 150 words):
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family speaking in cycle {cycle}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            speech_text = response.choices[0].message.content.strip()
            
            return {
                'round': round_num,
                'cycle': cycle,
                'agent_id': agent['id'],
                'agent_name': agent['family_name'],
                'content': speech_text,
                'action': self._analyze_comment_action(speech_text)
            }
            
        except Exception as e:
            print(f"        ⚠️  Speech failed: {e}")
            return None
    
    def _get_agent_adjustment(self, agent: Dict, round_num: int) -> Optional[Dict]:
        """Get agent's decision on adjusting their proposal
        
        KEY: Provide complete history + all speeches from this round
        """
        agent_proposal_id = self._find_agent_proposal(agent['id'])
        if not agent_proposal_id:
            return None
        
        current_proposal = self.proposals[agent_proposal_id]
        
        # Build history including THIS round's speeches
        history_text = self._build_negotiation_history_text(agent['id'], round_num, include_current_round=True)
        
        # Show feedback on your proposal from this round's discussion
        feedback_text = self._build_feedback_on_proposal_text(agent_proposal_id, round_num)
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}, {agent['value_type']} values).

[Negotiation Status]Round {round_num}/5

[Your Current Proposal]
{self._format_single_proposal(current_proposal)}

[Feedback on Your Proposal]
{feedback_text}

[Complete Negotiation History]
{history_text}

[Your Decision]
Based on feedback and ongoing negotiation, you must decide:

Option A: ADJUST - Modify your proposal to address concerns
Option B: WITHDRAW - Withdraw and support another proposal
Option C: MAINTAIN - Keep your proposal unchanged

**If ADJUST**: Provide new allocation and reason
**If WITHDRAW**: Specify which proposal you'll support
**If MAINTAIN**: Explain why

Format:
DECISION: [ADJUST/WITHDRAW/MAINTAIN]
REASON: [Brief explanation]
[If ADJUST, include NEW_ALLOCATION section like Round 1]

Please decide:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family deciding whether to adjust your proposal."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse decision
            decision_match = re.search(r'DECISION:\s*(ADJUST|WITHDRAW|MAINTAIN)', content, re.IGNORECASE)
            if not decision_match:
                return {'action': 'maintain', 'reason': 'No clear decision'}
            
            decision = decision_match.group(1).upper()
            
            reason_match = re.search(r'REASON:\s*(.+?)(?=NEW_ALLOCATION:|$)', content, re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else "No reason given"
            
            adjustment = {
                'round': round_num,
                'agent_id': agent['id'],
                'agent_name': agent['family_name'],
                'action': decision.lower(),
                'reason': reason,
                'old_proposal_id': agent_proposal_id
            }
            
            if decision == 'ADJUST':
                # Parse new allocation
                new_alloc_match = re.search(r'NEW_ALLOCATION:(.+)', content, re.DOTALL)
                if new_alloc_match:
                    new_allocation = self._parse_allocation_text(new_alloc_match.group(1))
                    if new_allocation and len(new_allocation) == len(self.agents):
                        adjustment['new_allocation'] = self._normalize_allocation(new_allocation)
                    else:
                        adjustment['action'] = 'maintain'
                        adjustment['reason'] = 'Invalid allocation format'
            
            elif decision == 'WITHDRAW':
                # Parse which proposal to support
                support_match = re.search(r'support\s+(P\d+_R\d+)', content, re.IGNORECASE)
                if support_match:
                    adjustment['support_proposal'] = support_match.group(1)
            
            return adjustment
            
        except Exception as e:
            print(f"      ⚠️  Adjustment call failed: {e}")
            return None
    
    def _apply_adjustments(self, adjustments: List[Dict], round_num: int):
        """Apply all adjustments from this round"""
        for adj in adjustments:
            if adj['action'] == 'adjust' and 'new_allocation' in adj:
                # Update proposal with new allocation
                old_id = adj['old_proposal_id']
                new_id = f"P{adj['agent_id']}_R{round_num}"
                
                self.proposals[old_id]['status'] = 'superseded'
                self.proposals[new_id] = {
                    'id': new_id,
                    'proposer_id': adj['agent_id'],
                    'proposer_name': adj['agent_name'],
                    'proposer_value': next(a['value_type'] for a in self.agents if a['id'] == adj['agent_id']),
                    'allocation': adj['new_allocation'],
                    'rationale': f"Adjusted based on feedback: {adj['reason'][:100]}",
                    'supporters': [adj['agent_id']],
                    'round_created': round_num,
                    'round_last_modified': round_num,
                    'status': 'active',
                    'previous_version': old_id
                }
                print(f"    📝 {adj['agent_name']}: Proposal updated {old_id} → {new_id}")
            
            elif adj['action'] == 'withdraw' and 'support_proposal' in adj:
                # Mark as withdrawn and add support to target
                old_id = adj['old_proposal_id']
                self.proposals[old_id]['status'] = 'withdrawn'
                
                target_id = adj['support_proposal']
                if target_id in self.proposals and adj['agent_id'] not in self.proposals[target_id]['supporters']:
                    self.proposals[target_id]['supporters'].append(adj['agent_id'])
                    print(f"    🤝 {adj['agent_name']}: Withdrew, supporting {target_id}")
    
    # ===== ROUND 5: Final Vote =====
    
    def _round5_final_vote(self):
        """Round 5: Final consensus vote on active proposals"""
        print("\n🗳️  Final Vote: All agents vote on surviving proposals...\n")
        
        # Get active proposals
        active_proposals = {pid: p for pid, p in self.proposals.items() if p['status'] == 'active'}
        
        print(f"  Active proposals: {len(active_proposals)}")
        for pid, prop in active_proposals.items():
            supporters = len(prop['supporters'])
            print(f"    {pid} by {prop['proposer_name']}: {supporters} supporters")
        
        if len(active_proposals) == 0:
            print("  ⚠️  No active proposals! Using fallback...")
            return self._fallback_allocation()
        
        if len(active_proposals) == 1:
            winner_id = list(active_proposals.keys())[0]
            print(f"\n  🎯 Only one proposal remaining: {winner_id}")
            return active_proposals[winner_id]['allocation']
        
        # Conduct final vote
        votes = self._conduct_final_vote(active_proposals)
        
        # Determine winner
        winner_id = max(votes, key=votes.get)
        winner_score = votes[winner_id]
        
        print(f"\n📊 Final Vote Results:")
        for pid in sorted(votes, key=votes.get, reverse=True):
            print(f"  {pid}: {votes[pid]:.2f}/5.0 average")
        
        print(f"\n🏆 Winner: {winner_id} (score: {winner_score:.2f})")
        
        self._display_final_allocation(active_proposals[winner_id]['allocation'])
        
        return active_proposals[winner_id]['allocation']
    
    def _conduct_final_vote(self, active_proposals: Dict) -> Dict[str, float]:
        """Each agent votes on all active proposals"""
        all_scores = {pid: [] for pid in active_proposals}
        
        for agent in self.agents:
            for prop_id, prop in active_proposals.items():
                score = self._score_proposal(agent, prop_id, prop, round_num=5)
                all_scores[prop_id].append(score)
        
        # Calculate averages
        avg_scores = {}
        for pid, scores in all_scores.items():
            avg_scores[pid] = sum(scores) / len(scores) if scores else 0.0
        
        return avg_scores
    
    def _score_proposal(self, agent: Dict, prop_id: str, prop: Dict, round_num: int) -> float:
        """Agent scores a proposal (1-5)
        
        KEY: Provide complete history so agent can make informed decision
        """
        my_allocation = prop['allocation'][agent['id']]['grain']
        my_survival = self.survival_needs[agent['id']]['grain']
        
        # Complete history
        history_text = self._build_negotiation_history_text(agent['id'], round_num)
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}, {agent['value_type']} values).

[Final Vote - Round 5]

[Complete Negotiation History]
{history_text}

[Proposal to Evaluate]
Proposal ID: {prop_id}
Proposer: {prop['proposer_name']} ({prop['proposer_value']})
Rationale: {prop['rationale']}

Your allocation: {my_allocation:.1f} units ({my_allocation/agent['members']:.2f} per person)
Your survival needs: {my_survival:.1f} units

[Your Task]
Rate this proposal 1-5 based on:
- Alignment with your {agent['value_type']} values
- Meeting your family's needs
- Fairness of the negotiation process

Reply with ONLY a number 1-5:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} family voting. Reply with only a number 1-5."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            score_match = re.search(r'[1-5]', score_text)
            if score_match:
                return float(score_match.group())
            return 3.0
            
        except:
            # Fallback heuristic
            return 3.0 if my_allocation >= my_survival else 2.0
    
    # ===== Helper Methods =====
    
    def _build_family_info_text(self) -> str:
        """Build text listing all families"""
        text = "[All Families]\n"
        for a in self.agents:
            survival = self.survival_needs[a['id']]['grain']
            text += f"- {a['family_name']}: {a['members']} people, {a['labor_force']} laborers, "
            text += f"survival needs {survival:.1f} ({a['value_type']})\n"
        return text
    
    def _build_negotiation_history_text(self, agent_id: int, current_round: int, include_current_round: bool = False) -> str:
        """Build complete negotiation history for an agent
        
        KEY: This is critical - must include ALL relevant history
        """
        if current_round == 1:
            return "This is Round 1 - no history yet.\n"
        
        text = ""
        
        # Round 1 summary
        text += "[Round 1: Initial Proposals]\n"
        round1_proposals = {pid: p for pid, p in self.proposals.items() if p['round_created'] == 1}
        text += f"{len(round1_proposals)} proposals submitted.\n\n"
        
        # Rounds 2 to current
        max_round = current_round if include_current_round else current_round - 1
        for r in range(2, max_round + 1):
            text += f"[Round {r}: Discussion (3 Cycles)]\n"
            
            # Speeches in this round (organized by cycle)
            round_speeches = [s for s in self.comments_history if s['round'] == r]
            if round_speeches:
                # Group by cycle
                for cycle in [1, 2, 3]:
                    cycle_speeches = [s for s in round_speeches if s.get('cycle') == cycle]
                    if cycle_speeches:
                        text += f"  Cycle {cycle} ({len(cycle_speeches)} speakers):\n"
                        for s in cycle_speeches[:3]:  # Show first 3
                            text += f"    - {s['agent_name']}: {s.get('content', s.get('comment', ''))[:80]}...\n"
                        if len(cycle_speeches) > 3:
                            text += f"    ... and {len(cycle_speeches)-3} more\n"
            
            # Adjustments in this round
            round_adjustments = [a for a in self.adjustments_history if a['round'] == r]
            if round_adjustments:
                text += f"  Adjustments after discussion:\n"
                for a in round_adjustments:
                    text += f"    - {a['agent_name']}: {a['action']} - {a['reason'][:60]}...\n"
            
            text += "\n"
        
        return text
    
    def _build_proposals_text(self) -> str:
        """Build text showing all active proposals"""
        active = {pid: p for pid, p in self.proposals.items() if p['status'] == 'active'}
        
        if not active:
            return "No active proposals.\n"
        
        text = ""
        for pid, prop in active.items():
            text += f"\n{pid} by {prop['proposer_name']} ({prop['proposer_value']}):\n"
            text += f"Rationale: {prop['rationale'][:100]}...\n"
            text += f"Supporters: {len(prop['supporters'])} agents\n"
            
            # Show allocation summary
            allocations = [prop['allocation'][aid]['grain'] for aid in sorted(prop['allocation'].keys())]
            text += f"Allocation range: {min(allocations):.1f} - {max(allocations):.1f} units\n"
        
        return text
    
    def _build_feedback_on_proposal_text(self, proposal_id: str, current_round: int) -> str:
        """Build text showing feedback on a specific proposal"""
        # Get speeches/comments that mention this proposal
        proposal_name = self.proposals[proposal_id]['proposer_name']
        
        feedback = []
        for speech in self.comments_history:
            speech_content = speech.get('content', speech.get('comment', ''))
            # Check if this speech mentions the proposal
            if proposal_id in speech_content or proposal_name in speech_content:
                feedback.append(speech)
        
        if not feedback:
            return "No direct feedback on your proposal in discussions.\n"
        
        text = ""
        for f in feedback[-3:]:  # Last 3 feedbacks
            cycle_info = f" Cycle {f['cycle']}" if 'cycle' in f else ""
            content = f.get('content', f.get('comment', ''))
            text += f"Round {f['round']}{cycle_info} - {f['agent_name']}: {content[:100]}...\n"
        
        return text
    
    def _format_single_proposal(self, prop: Dict) -> str:
        """Format a single proposal for display"""
        text = f"Proposal {prop['id']}:\n"
        text += f"Proposer: {prop['proposer_name']} ({prop['proposer_value']})\n"
        text += f"Rationale: {prop['rationale']}\n"
        text += f"Supporters: {len(prop['supporters'])} agents\n"
        return text
    
    def _find_agent_proposal(self, agent_id: int) -> Optional[str]:
        """Find agent's most recent active proposal"""
        for pid, prop in reversed(self.proposals.items()):
            if prop['proposer_id'] == agent_id and prop['status'] == 'active':
                return pid
        return None
    
    def _analyze_comment_action(self, comment_text: str) -> str:
        """Analyze comment to determine action (support/oppose/suggest)"""
        text_lower = comment_text.lower()
        if 'support' in text_lower or 'agree' in text_lower:
            return 'support'
        elif 'oppose' in text_lower or 'disagree' in text_lower:
            return 'oppose'
        elif 'suggest' in text_lower or 'modify' in text_lower:
            return 'suggest_change'
        return 'neutral'
    
    def _display_proposals_summary(self):
        """Display current proposals summary"""
        active = {pid: p for pid, p in self.proposals.items() if p['status'] == 'active'}
        print(f"\n  📋 Current Status: {len(active)} active proposals")
        for pid, prop in active.items():
            print(f"    {pid}: {prop['proposer_name']}, {len(prop['supporters'])} supporters")
    
    def _display_final_allocation(self, allocation: Dict[int, Dict[str, float]]):
        """Display final allocation"""
        print(f"\n  📋 Final Allocation:")
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
    
    def _check_consensus(self) -> bool:
        """Check if consensus reached (one proposal has >70% support)"""
        for prop in self.proposals.values():
            if prop['status'] == 'active' and len(prop['supporters']) >= len(self.agents) * 0.7:
                return True
        return False
    
    def _parse_allocation_text(self, text: str) -> Optional[Dict[int, Dict[str, float]]]:
        """Parse allocation from text"""
        allocation = {}
        for agent in self.agents:
            pattern = rf"{re.escape(agent['family_name'])}\s*=\s*([\d.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                allocation[agent['id']] = {'grain': amount}
        return allocation if len(allocation) == len(self.agents) else None
    
    def _normalize_allocation(self, allocation: Dict[int, Dict[str, float]]) -> Dict[int, Dict[str, float]]:
        """Normalize allocation to exact total"""
        current_total = sum(allocation[aid]['grain'] for aid in allocation)
        if current_total == 0:
            per_family = self.total_grain / len(allocation)
            return {aid: {'grain': per_family} for aid in allocation}
        
        ratio = self.total_grain / current_total
        normalized = {aid: {'grain': allocation[aid]['grain'] * ratio} for aid in allocation}
        
        # Fix rounding
        actual_total = sum(normalized[aid]['grain'] for aid in normalized)
        diff = self.total_grain - actual_total
        last_id = list(normalized.keys())[-1]
        normalized[last_id]['grain'] += diff
        
        return normalized
    
    def _validate_allocation(self, allocation: Dict[int, Dict[str, float]]):
        """Validate allocation"""
        total = sum(allocation[a['id']]['grain'] for a in self.agents)
        print(f"\n🔍 Validation: Total allocated = {total:.1f} / {self.total_grain:.1f}")
    
    def _fallback_allocation(self) -> Dict[int, Dict[str, float]]:
        """Fallback to equal distribution"""
        print("\n⚠️  Using fallback: equal distribution")
        per_family = self.total_grain / len(self.agents)
        return {agent['id']: {'grain': per_family} for agent in self.agents}


# ===== Wrapper Function =====

def discussion_based_distribution(
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1
) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
    """Wrapper function for progressive consensus negotiation"""
    negotiator = ProgressiveConsensusNegotiation(
        agents=agents,
        total_resources=total_resources,
        survival_needs=survival_needs,
        round_number=round_number
    )
    
    allocation, metadata = negotiator.negotiate()
    
    return allocation, metadata

