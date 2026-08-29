"""
Progressive Voting Negotiation Mechanism (RecipeC)
Progressive Voting Elimination Negotiation Mechanism

Core design:
- Round 1: Initial proposal(10Piece) + First round of voting → Before retention5Piece
- Round 2: In-depth discussion + Protocol Adjustment
- Round 3: Second Vote → Before retention3Piece + Final discussion  
- Round 4: Final Vote → Determine winner(1Piece)

Key features:
1. Phase out:Reduce the discussion burden,Focus on competitive programs
2. Forced Steering:The eliminated person must choose to support another program
3. Scheme Evolution:Progressors can absorb suggestions for adjusting the program
4. Clear Consensus:Final winner receives majority support
"""

from fairness_sim.llm_client import get_llm_client, get_model_name
import re
import json
import os
import time
from typing import List, Dict, Any, Tuple

# Initialize OpenAI client for DeepSeek
client = get_llm_client()


class ProgressiveVotingNegotiation:
    """Progressive Voting Elimination Negotiation Mechanism"""
    
    def __init__(self, agents: List[Dict[str, Any]], total_resources: Dict[str, float],
                 survival_needs: Dict[int, Dict[str, float]], round_number: int = 1, memory_module=None):
        self.agents = agents
        self.total_resources = total_resources
        self.survival_needs = survival_needs
        self.round_number = round_number
        self.total_grain = total_resources.get("grain", 0.0)
        self.memory_module = memory_module  # 🆕 Historical memory module for value evolution
        
        # Calculate production parameters for transparency
        self.total_needs = sum([needs.get('grain', 0) for needs in survival_needs.values()])
        self.total_labor = sum([agent.get('labor_force', 0) for agent in agents])
        self.surplus = max(0, self.total_grain - self.total_needs)
        self.M = self.surplus / self.total_labor if self.total_labor > 0 else 0
        
        # Tracking structures
        self.proposals = {}  # proposal_id -> proposal_data
        self.eliminated_agents = []  # agent_ids whose proposals were eliminated
        self.support_map = {}  # agent_id -> supported_proposal_id
        self.vote_history = []  # All voting records
        self.discussion_history = {'round_2': {'suggestions': [], 'responses': []}, 
                                    'round_3': {'criticisms': [], 'defenses': []}}  # Discussion records
        
        # 🆕 Conversation logger
        self.dialogue_log = []  # Record allLLMI/O
        self.log_file = None  # Log file path
        self._init_dialogue_log()
        
        print(f"\n{'='*80}")
        print(f"[Progressive Voting Negotiation - Round {round_number}]")
        print(f"Total Resources: {self.total_grain:.1f} units")
        print(f"Mechanism: 4-Round Progressive Elimination (10→5→3→1)")
        print(f"{'='*80}\n")
    
    def _init_dialogue_log(self):
        """Initialize Conversation Log File"""
        os.makedirs("discussion_logs", exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.log_file = f"discussion_logs/discussion_round{self.round_number}_{timestamp}.txt"
        
        # Write Log Header
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"Discussion Dialogue Log - Simulation Round {self.round_number}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Resources: {self.total_grain:.1f} units\n")
            f.write(f"Total Agents: {len(self.agents)}\n")
            f.write("="*80 + "\n\n")
        
        print(f"📝 Conversation logs will be saved to: {self.log_file}\n")
    
    def _log_dialogue(self, phase: str, agent_name: str, agent_id: int, 
                     prompt: str, response: str, action: str = ""):
        """Record Single Conversation"""
        log_entry = {
            "phase": phase,
            "agent_name": agent_name,
            "agent_id": agent_id,
            "action": action,
            "prompt": prompt,
            "response": response,
            "timestamp": time.strftime('%H:%M:%S')
        }
        self.dialogue_log.append(log_entry)
        
        # Write files in real time
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{log_entry['timestamp']}] {phase} - {agent_name} (ID:{agent_id})\n")
            if action:
                f.write(f"Action: {action}\n")
            f.write(f"{'-'*80}\n")
            f.write(f"PROMPT:\n{prompt}\n")
            f.write(f"{'-'*80}\n")
            f.write(f"RESPONSE:\n{response}\n")
            f.write(f"{'='*80}\n")
    
    def _write_log_summary(self):
        """Write log summary information"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n{'='*80}\n")
            f.write(f"DISCUSSION SUMMARY\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Total LLM Interactions: {len(self.dialogue_log)}\n")
            f.write(f"Total Proposals: {len(self.proposals)}\n")
            f.write(f"Eliminated Agents: {len(self.eliminated_agents)}\n")
            f.write(f"Vote Rounds: {len(self.vote_history)}\n\n")
            
            # Statistics by Stage
            phase_counts = {}
            for entry in self.dialogue_log:
                phase = entry['phase'].split(':')[0]  # Get Stage Name(As ROUND 1, ROUND 2)
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            f.write("Interactions by Phase:\n")
            for phase, count in sorted(phase_counts.items()):
                f.write(f"  {phase}: {count} interactions\n")
            
            f.write(f"\n{'='*80}\n")
            f.write(f"Log file saved successfully\n")
            f.write(f"{'='*80}\n")
        
        print(f"✅ Conversation log saved: {self.log_file}")
        print(f"   Total {len(self.dialogue_log)} timesLLMInteraction\n")
    
    def negotiate(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """Main negotiation process"""
        try:
            # Round 1: Initial proposals + First vote
            print(f"\n{'='*80}")
            print(f"[ROUND 1: Initial Proposals & First Vote]")
            print(f"{'='*80}\n")
            self._round1_initial_proposals_and_vote()
            
            # Round 2: Discussion + Adjustment
            print(f"\n{'='*80}")
            print(f"[ROUND 2: Discussion & Adjustment]")
            print(f"{'='*80}\n")
            self._round2_discussion_and_adjustment()
            
            # Round 3: Second vote + Final discussion
            print(f"\n{'='*80}")
            print(f"[ROUND 3: Second Vote & Final Discussion]")
            print(f"{'='*80}\n")
            self._round3_second_vote_and_discussion()
            
            # Round 4: Final vote
            print(f"\n{'='*80}")
            print(f"[ROUND 4: Final Vote]")
            print(f"{'='*80}\n")
            final_allocation = self._round4_final_vote()
            
            # Validate
            self._validate_allocation(final_allocation)
            
            # 🆕 Write Log Summary
            self._write_log_summary()
            
            # Metadata
            metadata = {
                "mechanism": "progressive_voting",
                "total_proposals": len(self.proposals),
                "vote_rounds": 3,
                "eliminated_count": len(self.eliminated_agents),
                "proposals": self.proposals,
                "vote_history": self.vote_history,
                "support_map": self.support_map,
                "discussion_history": self.discussion_history,
                "success": True,
                "dialogue_log_file": self.log_file  # 🆕 Add log file path tometadata
            }
            
            return final_allocation, metadata
            
        except Exception as e:
            print(f"\n❌ Negotiation Failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_allocation(), {"error": str(e)}
    
    # ===== ROUND 1: Initial Proposals & First Vote =====
    
    def _round1_initial_proposals_and_vote(self):
        """Round 1: Each agent submits initial proposal, then vote to keep top 5"""
        print("📝 Step 1.1: Each agent submits initial proposal\n")
        
        # Step 1.1: Submit proposals
        for agent in self.agents:
            print(f"  {agent['family_name']} ({agent['value_type']}) proposing...")
            proposal = self._get_initial_proposal(agent)
            
            if proposal:
                proposal_id = f"P{agent['id']}_R1"
                self.proposals[proposal_id] = {
                    'proposal_id': proposal_id,
                    'proposer_id': agent['id'],
                    'proposer_name': agent['family_name'],
                    'proposer_value': agent['value_type'],
                    'round_created': 1,
                    'version': 1,
                    'allocation': proposal['allocation'],
                    'rationale': proposal['rationale'],
                    'status': 'active',
                    'supporters': [agent['id']]  # Proposer supports their own
                }
                self.support_map[agent['id']] = proposal_id
                print(f"    ✓ Proposal {proposal_id} submitted")
        
        print(f"\n  Total proposals: {len(self.proposals)}\n")
        
        # Step 1.2: First vote
        print("🗳️  Step 1.2: First vote (quick screening)\n")
        vote_results = self._conduct_vote(list(self.proposals.keys()), temperature=0.5)
        
        # Step 1.3: Eliminate bottom 5, keep top 5
        print("\n📊 Step 1.3: Elimination results\n")
        sorted_proposals = sorted(vote_results.items(), key=lambda x: x[1], reverse=True)
        
        keep_count = 5
        for i, (prop_id, avg_score) in enumerate(sorted_proposals):
            if i < keep_count:
                print(f"  ✅ {prop_id}: {avg_score:.2f}/5.0 - Advances to Round 2")
            else:
                print(f"  ❌ {prop_id}: {avg_score:.2f}/5.0 - Eliminated")
                self.proposals[prop_id]['status'] = 'eliminated_r1'
                proposer_id = self.proposals[prop_id]['proposer_id']
                self.eliminated_agents.append(proposer_id)
        
        print(f"\n  Advancing: {keep_count} proposals")
        print(f"  Eliminated: {len(sorted_proposals) - keep_count} proposals\n")
    
    # ===== ROUND 2: Discussion & Adjustment =====
    
    def _round2_discussion_and_adjustment(self):
        """Round 2: Eliminated agents declare support, discussion, adjustment"""
        
        # Step 2.1: Eliminated agents declare support
        print("💬 Step 2.1: Eliminated agents declare support\n")
        
        active_proposals = [pid for pid, p in self.proposals.items() if p['status'] == 'active']
        
        for agent_id in self.eliminated_agents:
            agent = next(a for a in self.agents if a['id'] == agent_id)
            print(f"  {agent['family_name']}'s proposal was eliminated. Choosing support...")
            
            support_choice = self._get_support_choice(agent, active_proposals)
            if support_choice:
                chosen_pid = support_choice['proposal_id']
                reason = support_choice['reason']
                
                self.support_map[agent_id] = chosen_pid
                if agent_id not in self.proposals[chosen_pid]['supporters']:
                    self.proposals[chosen_pid]['supporters'].append(agent_id)
                
                print(f"    → Supports {chosen_pid}: {reason[:60]}...")
        
        # Step 2.2: Suggestion-Response discussion
        print(f"\n💬 Step 2.2: Discussion - Supporters give suggestions\n")
        self._round2_discussion(active_proposals)
        
        # Step 2.3: Proposers adjust
        print(f"\n🔧 Step 2.3: Proposers adjust proposals\n")
        for prop_id in active_proposals:
            proposer_id = self.proposals[prop_id]['proposer_id']
            agent = next(a for a in self.agents if a['id'] == proposer_id)
            
            adjustment = self._get_adjustment_decision(agent, prop_id)
            if adjustment and adjustment['action'] == 'adjust':
                # Create new version
                old_version = self.proposals[prop_id]['version']
                new_prop_id = f"P{proposer_id}_R2"
                
                self.proposals[new_prop_id] = {
                    **self.proposals[prop_id],
                    'proposal_id': new_prop_id,
                    'version': old_version + 1,
                    'allocation': adjustment.get('new_allocation', self.proposals[prop_id]['allocation']),
                    'rationale': adjustment['reason'],
                    'status': 'active',
                    'parent': prop_id
                }
                
                # Mark old as superseded
                self.proposals[prop_id]['status'] = 'superseded'
                
                # Update support map
                for supporter_id in self.proposals[prop_id]['supporters']:
                    self.support_map[supporter_id] = new_prop_id
                self.proposals[new_prop_id]['supporters'] = self.proposals[prop_id]['supporters'].copy()
                
                print(f"  {agent['family_name']}: ADJUSTED → {new_prop_id}")
            else:
                print(f"  {agent['family_name']}: MAINTAINED {prop_id}")
    
    # ===== ROUND 3: Second Vote & Final Discussion =====
    
    def _round3_second_vote_and_discussion(self):
        """Round 3: Vote again, keep top 3, final discussion"""
        
        # Step 3.1: Second vote
        print("🗳️  Step 3.1: Second vote\n")
        active_proposals = [pid for pid, p in self.proposals.items() if p['status'] == 'active']
        vote_results = self._conduct_vote(active_proposals, temperature=0.7)
        
        # Step 3.2: Keep top 3
        print("\n📊 Step 3.2: Second elimination\n")
        sorted_proposals = sorted(vote_results.items(), key=lambda x: x[1], reverse=True)
        
        keep_count = 3
        newly_eliminated = []
        
        for i, (prop_id, avg_score) in enumerate(sorted_proposals):
            if i < keep_count:
                print(f"  ✅ {prop_id}: {avg_score:.2f}/5.0 - Advances to Final Round")
            else:
                print(f"  ❌ {prop_id}: {avg_score:.2f}/5.0 - Eliminated")
                self.proposals[prop_id]['status'] = 'eliminated_r3'
                proposer_id = self.proposals[prop_id]['proposer_id']
                if proposer_id not in self.eliminated_agents:
                    self.eliminated_agents.append(proposer_id)
                    newly_eliminated.append(proposer_id)
        
        # Step 3.3: Newly eliminated agents declare support
        if newly_eliminated:
            print("\n💬 Step 3.3: Newly eliminated agents declare support\n")
            finalist_proposals = [pid for pid, p in self.proposals.items() if p['status'] == 'active']
            
            for agent_id in newly_eliminated:
                agent = next(a for a in self.agents if a['id'] == agent_id)
                print(f"  {agent['family_name']}'s proposal was eliminated. Choosing support...")
                
                support_choice = self._get_support_choice(agent, finalist_proposals)
                if support_choice:
                    chosen_pid = support_choice['proposal_id']
                    reason = support_choice['reason']
                    
                    self.support_map[agent_id] = chosen_pid
                    if agent_id not in self.proposals[chosen_pid]['supporters']:
                        self.proposals[chosen_pid]['supporters'].append(agent_id)
                    
                    print(f"    → Supports {chosen_pid}: {reason[:60]}...")
        
        # Step 3.4: Final discussion - Debate among finalists
        print(f"\n💬 Step 3.4: Final discussion - Finalists debate\n")
        finalist_proposals = [pid for pid, p in self.proposals.items() if p['status'] == 'active']
        self._round3_discussion(finalist_proposals)
        
        print(f"\n  Finalists: 3 proposals entering final vote\n")
    
    # ===== ROUND 4: Integrated Consensus Building =====
    
    def _round4_final_vote(self):
        """Round 4: Build integrated consensus from 3 finalists (NEW DESIGN)
        
        Design Philosophy:
        - Instead of "winner takes all", integrate all 3 finalist proposals
        - Weight by score × support to reflect community preferences
        - Allow agents to provide feedback on integrated proposal
        - Seek consensus rather than majority rule
        """
        
        print("🤝 Building integrated consensus from 3 finalists\n")
        
        finalist_proposals = [pid for pid, p in self.proposals.items() if p['status'] == 'active']
        
        if len(finalist_proposals) == 0:
            print("  ⚠️  No active proposals, using fallback")
            return self._fallback_allocation()
        
        # Step 4.1: Conduct final vote to get scores
        print("📊 Step 4.1: Final voting on 3 proposals\n")
        vote_results = self._conduct_vote(finalist_proposals, temperature=0.3)
        
        # Step 4.2: Calculate integrated proposal
        print("\n🔄 Step 4.2: Calculating weighted integrated proposal\n")
        integrated_allocation = self._calculate_integrated_allocation(finalist_proposals, vote_results)
        
        # Step 4.3: Get agent feedback on integrated proposal
        print("\n💬 Step 4.3: Collecting feedback on integrated proposal\n")
        acceptance_rate, adjustments = self._collect_feedback_on_integrated(integrated_allocation, vote_results)
        
        # Step 4.4: Decide final allocation based on acceptance rate
        print(f"\n📈 Acceptance rate: {acceptance_rate:.1%}\n")
        
        if acceptance_rate >= 0.7:
            # High acceptance: Use integrated proposal as-is
            print("✅ High acceptance (>=70%) - Integrated proposal adopted\n")
            final_allocation = integrated_allocation
        elif acceptance_rate >= 0.4:
            # Medium acceptance: Apply minor adjustments
            print("🔧 Medium acceptance (40-70%) - Applying minor adjustments\n")
            final_allocation = self._apply_minor_adjustments(integrated_allocation, adjustments)
        else:
            # Low acceptance: Fallback to highest-scored proposal
            print("⚠️  Low acceptance (<40%) - Using highest-scored proposal as fallback\n")
            winner_id = max(vote_results.items(), key=lambda x: x[1])[0]
            winner_allocation = self.proposals[winner_id]['allocation']
            final_allocation = {agent['id']: {"grain": winner_allocation.get(agent['id'], 0.0)} 
                               for agent in self.agents}
        
        print(f"\n✅ Final allocation determined\n")
        return final_allocation
    
    # ===== Helper Functions =====
    
    def _get_value_context(self, agent: Dict[str, Any]) -> str:
        """Get value evolution context for agent
        
        Args:
            agent: Agent dictionary
            
        Returns:
            Formatted value context string (empty if no evolution)
        """
        if not self.memory_module:
            return ""
        
        return self.memory_module.get_value_context_for_prompt(agent['id'], agent['value_type'])
    
    def _get_initial_proposal(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Agent submits initial allocation proposal"""
        # 🆕 Get value evolution context
        value_context = self._get_value_context(agent)
        
        prompt = f"""You are {agent['family_name']} family (ID:{agent['id']}).

[Your Values]
Original values: {agent['value_type']}
{value_context}
[Task]Submit your initial allocation proposal for Round 1.

[Community Situation]
- Total resources: {self.total_grain:.1f} units
- Total families: {len(self.agents)}
- Your family: {agent['members']} people, {agent['labor_force']} workers

[All Families]
"""
        for a in self.agents:
            needs = self.survival_needs.get(a['id'], {}).get('grain', 0)
            prompt += f"- {a['family_name']} (ID:{a['id']}): {a['members']} people, {a['labor_force']} workers, needs {needs:.1f}\n"
        
        # Determine trend description
        trend_desc = "stable"
        if self.round_number == 1:
            trend_desc = "initial round"
        elif self.round_number >= 2:
            # In real implementation, this would come from history
            trend_desc = f"Round {self.round_number}"
        
        # Generate template and example allocations dynamically
        num_families = len(self.agents)
        template_allocation = "\n".join([f"Family_{i}: 0.0" for i in range(1, num_families + 1)])
        
        # For example, show up to 10 families or all if less
        example_count = min(10, num_families)
        example_allocation = "\n".join([f"Family_{i}: {20 + i * 2.5:.1f}" for i in range(1, example_count + 1)])
        if num_families > 10:
            example_allocation += f"\n... (continue for all {num_families} families)"
        
        prompt += f"""
[Community Production Rules]
- Each worker can process up to {self.M:.2f} units of surplus resources
- Processed resources produce 2× output (E=2.0)
- Unprocessed surplus (due to insufficient labor) rolls to next round but doesn't produce
- Current: {trend_desc}

[Your Task]
Propose a full allocation plan based on your {agent['value_type']} values.

CRITICAL REQUIREMENTS:
1. You MUST provide allocation for ALL {num_families} families (Family_1 through Family_{num_families})
2. Use EXACT format "Family_1: number" (with underscore, colon, space)
3. List ALL families from Family_1 to Family_{num_families}
4. Use decimal numbers (e.g., 25.5 not 25)
5. Total allocation must equal {self.total_grain:.1f} units

Output format (COPY THIS EXACTLY):

ALLOCATION:
{template_allocation}

RATIONALE: (Explain your proposal)

EXAMPLE of correct format:

ALLOCATION:
{example_allocation}

RATIONALE: This allocation prioritizes families with higher needs while maintaining basic fairness.

Now provide YOUR allocation following this EXACT format:
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} submitting allocation proposal. Follow the format EXACTLY as shown in the example."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent formatting
                max_tokens=600,   # Slightly more tokens to ensure complete output
                timeout=60.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 1: Initial Proposal",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action="Generate initial allocation proposal"
            )
            
            # Parse allocation
            allocation = self._parse_allocation_from_text(content)
            rationale_match = re.search(r'RATIONALE:\s*(.+)', content, re.DOTALL | re.IGNORECASE)
            rationale = rationale_match.group(1).strip() if rationale_match else "No rationale provided"
            
            if allocation:
                return {'allocation': allocation, 'rationale': rationale}
            else:
                print(f"    ⚠️  Parse failed, using fallback")
                print(f"    [DEBUG] Agent: {agent['family_name']} ({agent['value_type']})")
                print(f"    [DEBUG] Response length: {len(content)} chars")
                print(f"    [DEBUG] Response preview:")
                # Show first 500 chars with line breaks preserved
                preview = content[:500].replace('\n', '\n    ')
                print(f"    {preview}")
                if len(content) > 500:
                    print(f"    ... (truncated)")
                
                # Try to generate a simple fallback based on agent's value type
                fallback_allocation = self._generate_fallback_proposal(agent)
                if fallback_allocation:
                    return {'allocation': fallback_allocation, 'rationale': f"Auto-generated {agent['value_type']} proposal (parse failed)"}
                return None
                
        except Exception as e:
            print(f"    ⚠️  LLM call failed: {e}")
            return None
    
    def _conduct_vote(self, proposal_ids: List[str], temperature: float = 0.7) -> Dict[str, float]:
        """All agents vote on given proposals, return average scores"""
        scores = {pid: [] for pid in proposal_ids}
        
        for agent in self.agents:
            for prop_id in proposal_ids:
                score = self._score_proposal(agent, prop_id, temperature)
                if score:
                    scores[prop_id].append(score)
        
        # Calculate averages
        avg_scores = {}
        for prop_id, score_list in scores.items():
            if score_list:
                avg_scores[prop_id] = sum(score_list) / len(score_list)
            else:
                avg_scores[prop_id] = 0.0
        
        # Record vote history
        self.vote_history.append({
            'round': len(self.vote_history) + 1,
            'proposals': proposal_ids,
            'results': avg_scores
        })
        
        return avg_scores
    
    def _score_proposal(self, agent: Dict[str, Any], proposal_id: str, temperature: float) -> float:
        """Agent scores a single proposal"""
        proposal = self.proposals[proposal_id]
        allocation = proposal['allocation']
        
        agent_allocation = allocation.get(agent['id'], 0.0)
        agent_needs = self.survival_needs.get(agent['id'], {}).get('grain', 0.0)
        
        # Build complete allocation details for comparison
        allocation_details = "[Complete Allocation in this Proposal]\n"
        for a in self.agents:
            a_id = a['id']
            a_alloc = allocation.get(a_id, 0.0)
            a_needs = self.survival_needs.get(a_id, {}).get('grain', 0.0)
            a_per_capita = a_alloc / a['members'] if a['members'] > 0 else 0
            a_per_labor = a_alloc / a['labor_force'] if a['labor_force'] > 0 else 0
            
            if a_id == agent['id']:
                allocation_details += f"→ {a['family_name']} (YOU): {a_alloc:.1f} units ({a_per_capita:.2f}/person, {a_per_labor:.2f}/worker, needs {a_needs:.1f})\n"
            else:
                allocation_details += f"  {a['family_name']}: {a_alloc:.1f} units ({a_per_capita:.2f}/person, {a_per_labor:.2f}/worker, needs {a_needs:.1f})\n"
        
        # 🆕 Get value evolution context
        value_context = self._get_value_context(agent)
        
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Proposal {proposal_id}]
Proposed by: {proposal['proposer_name']} ({proposal['proposer_value']})
Rationale: {proposal['rationale'][:100]}...

{allocation_details}

[Quick Rating Task]
Rate this proposal from 1-5 based on:
- Does it align with your {agent['value_type']} values?
- Is your allocation fair compared to others?
- Are there obvious flaws?

**Be critical** - consider both your family's interests and fairness.
(1=strongly oppose, 2=oppose, 3=neutral, 4=support, 5=strongly support)

Output ONLY:
score=X
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} voting on proposals. Always output scores in the exact format: score=X"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=50,  # Reduced since we only need "score=X"
                timeout=60.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase=f"VOTING on {proposal_id}",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action="Rate proposal"
            )
            
            # 🔍 Enhanced score extraction with multiple patterns
            score_patterns = [
                r'score\s*[:=:]\s*([1-5])',           # score=3, score:3, score:3
                r'rating\s*[:=:]\s*([1-5])',          # rating=3
                r'rate\s*[:=:]\s*([1-5])',            # rate=3
                r'([1-5])\s*[//]\s*5',                # 3/5, 3/5
                r'give\s+(?:a\s+)?(?:score\s+of\s+)?([1-5])',  # give a score of 3
                r'score\s+is\s+([1-5])',               # score is 3
                r'^\s*([1-5])\s*$',                    # standalone digit (last resort)
                r'\b([1-5])\b',                        # any single digit 1-5 (very last resort)
            ]
            
            for pattern in score_patterns:
                score_match = re.search(pattern, content, re.IGNORECASE)
                if score_match:
                    extracted_score = float(score_match.group(1))
                    # Only print if unusual (debug mode can be toggled)
                    # print(f"    [DEBUG] Extracted {extracted_score} from: {content[:40]}...")
                    return extracted_score
            
            # Final fallback: default neutral
            print(f"    [WARNING] No score found in GPT-4o output: {content}")
            print(f"    [WARNING] Using default score 3.0")
            return 3.0
                
        except Exception as e:
            return 3.0
    
    def _get_support_choice(self, agent: Dict[str, Any], active_proposals: List[str]) -> Dict[str, Any]:
        """Eliminated agent chooses which proposal to support"""
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Situation]Your proposal was eliminated. You must now support one of the remaining proposals.

[Remaining Proposals]
"""
        for prop_id in active_proposals:
            prop = self.proposals[prop_id]
            agent_allocation = prop['allocation'].get(agent['id'], 0.0)
            prompt += f"\n{prop_id} by {prop['proposer_name']} ({prop['proposer_value']})"
            prompt += f"\n  Your allocation: {agent_allocation:.1f} units"
            prompt += f"\n  Rationale: {prop['rationale'][:100]}...\n"
        
        prompt += f"""
[Task]Choose which proposal to support and explain why.

Output format:
SUPPORT: [proposal_id]
REASON: (1-2 sentences explaining your choice)
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} choosing support."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
                timeout=60.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 2: Choose Support",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action="Choose which proposal to support after elimination"
            )
            
            support_match = re.search(r'SUPPORT:\s*(P\d+_R\d+)', content, re.IGNORECASE)
            reason_match = re.search(r'REASON:\s*(.+)', content, re.DOTALL | re.IGNORECASE)
            
            if support_match:
                return {
                    'proposal_id': support_match.group(1),
                    'reason': reason_match.group(1).strip() if reason_match else "No reason given"
                }
            else:
                # Default to first proposal
                return {
                    'proposal_id': active_proposals[0],
                    'reason': "Default choice"
                }
                
        except Exception as e:
            return {
                'proposal_id': active_proposals[0],
                'reason': "Default due to error"
            }
    
    def _round2_discussion(self, active_proposals: List[str]):
        """Round 2 Discussion: Suggestion-Response mode
        
        Cycle 1: Eliminated agents give suggestions to proposals they support
        Cycle 2: Proposers respond to suggestions
        """
        # Cycle 1: Supporters give suggestions
        print("  Cycle 1: Supporters give suggestions\n")
        
        for agent_id in self.eliminated_agents:
            if agent_id not in self.support_map:
                continue
                
            supported_prop = self.support_map[agent_id]
            if supported_prop not in active_proposals:
                continue
            
            agent = next(a for a in self.agents if a['id'] == agent_id)
            suggestion = self._get_suggestion(agent, supported_prop)
            
            if suggestion:
                self.discussion_history['round_2']['suggestions'].append({
                    'from_agent_id': agent_id,
                    'from_agent_name': agent['family_name'],
                    'to_proposal': supported_prop,
                    'content': suggestion
                })
                print(f"    {agent['family_name']} → {supported_prop}: {suggestion[:70]}...")
        
        print()
        
        # Cycle 2: Proposers respond
        print("  Cycle 2: Proposers respond to suggestions\n")
        
        for prop_id in active_proposals:
            proposer_id = self.proposals[prop_id]['proposer_id']
            agent = next(a for a in self.agents if a['id'] == proposer_id)
            
            # Get suggestions for this proposal
            prop_suggestions = [s for s in self.discussion_history['round_2']['suggestions']
                               if s['to_proposal'] == prop_id]
            
            if prop_suggestions:
                response = self._get_response_to_suggestions(agent, prop_id, prop_suggestions)
                
                if response:
                    self.discussion_history['round_2']['responses'].append({
                        'from_agent_id': proposer_id,
                        'from_agent_name': agent['family_name'],
                        'proposal': prop_id,
                        'content': response
                    })
                    print(f"    {agent['family_name']} ({prop_id}): {response[:70]}...")
            else:
                print(f"    {agent['family_name']} ({prop_id}): No suggestions received")
        
        print()
    
    def _round3_discussion(self, finalist_proposals: List[str]):
        """Round 3 Discussion: Debate mode
        
        Cycle 1: Each finalist criticizes opponents
        Cycle 2: Each finalist defends their proposal
        """
        if len(finalist_proposals) != 3:
            print(f"  ⚠️  Expected 3 finalists, got {len(finalist_proposals)}, skipping debate\n")
            return
        
        # Cycle 1: Criticize opponents
        print("  Cycle 1: Finalists criticize opponents\n")
        
        for prop_id in finalist_proposals:
            proposer_id = self.proposals[prop_id]['proposer_id']
            agent = next(a for a in self.agents if a['id'] == proposer_id)
            
            opponents = [p for p in finalist_proposals if p != prop_id]
            criticism = self._get_criticism(agent, prop_id, opponents)
            
            if criticism:
                self.discussion_history['round_3']['criticisms'].append({
                    'from_agent_id': proposer_id,
                    'from_agent_name': agent['family_name'],
                    'from_proposal': prop_id,
                    'target_proposals': opponents,
                    'content': criticism
                })
                print(f"    {agent['family_name']} ({prop_id}): {criticism[:70]}...")
        
        print()
        
        # Cycle 2: Defend own proposal
        print("  Cycle 2: Finalists defend their proposals\n")
        
        for prop_id in finalist_proposals:
            proposer_id = self.proposals[prop_id]['proposer_id']
            agent = next(a for a in self.agents if a['id'] == proposer_id)
            
            # Get criticisms targeting this proposal
            criticisms_received = [c for c in self.discussion_history['round_3']['criticisms']
                                  if prop_id in c['target_proposals']]
            
            if criticisms_received:
                defense = self._get_defense(agent, prop_id, criticisms_received)
                
                if defense:
                    self.discussion_history['round_3']['defenses'].append({
                        'from_agent_id': proposer_id,
                        'from_agent_name': agent['family_name'],
                        'proposal': prop_id,
                        'content': defense
                    })
                    print(f"    {agent['family_name']} ({prop_id}): {defense[:70]}...")
        
        print()
    
    def _get_suggestion(self, agent: Dict[str, Any], supported_proposal_id: str) -> str:
        """Eliminated agent gives suggestion to supported proposal"""
        proposal = self.proposals[supported_proposal_id]
        allocation = proposal['allocation']
        
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Situation]
Your proposal was eliminated. You chose to support {supported_proposal_id}.

[Supported Proposal]
Proposed by: {proposal['proposer_name']} ({proposal['proposer_value']})
Rationale: {proposal['rationale'][:150]}...

Current allocation:
"""
        for a in self.agents[:5]:  # Show first 5 families
            a_alloc = allocation.get(a['id'], 0.0)
            prompt += f"  {a['family_name']}: {a_alloc:.1f} units\n"
        prompt += "  ...\n"
        
        prompt += f"""
[Your Task]
As a supporter, provide ONE constructive suggestion to improve this proposal:
- What could be adjusted to better reflect fairness?
- Be specific: Which family should get more/less, and why?
- Consider your {agent['value_type']} values.

Keep it brief (2-3 sentences).
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} giving suggestions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 2: Give Suggestion",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action=f"Suggest improvements for {supported_proposal_id}"
            )
            
            return content
            
        except Exception as e:
            print(f"      ⚠️  Suggestion failed: {e}")
            return ""
    
    def _get_response_to_suggestions(self, agent: Dict[str, Any], proposal_id: str, 
                                     suggestions: List[Dict[str, str]]) -> str:
        """Proposer responds to suggestions received"""
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Your Proposal {proposal_id}]
Current supporters: {len(self.proposals[proposal_id]['supporters'])}

[Suggestions Received]
"""
        for s in suggestions:
            prompt += f"From {s['from_agent_name']}: {s['content']}\n\n"
        
        prompt += f"""
[Your Response]
Review these suggestions. Will you:
- ACCEPT specific suggestions (say which)
- PARTIALLY_ACCEPT some ideas
- REJECT and explain why

Keep it brief (2-3 sentences).
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} responding to suggestions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 2: Respond to Suggestions",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action=f"Respond to suggestions for {proposal_id}"
            )
            
            return content
            
        except Exception as e:
            print(f"      ⚠️  Response failed: {e}")
            return ""
    
    def _get_criticism(self, agent: Dict[str, Any], own_proposal_id: str, 
                       opponent_proposals: List[str]) -> str:
        """Finalist criticizes opponent proposals"""
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Final Round Debate - Your proposal: {own_proposal_id}]

[Opponent Proposals]
"""
        for opp_id in opponent_proposals:
            opp = self.proposals[opp_id]
            prompt += f"\n{opp_id} by {opp['proposer_name']} ({opp['proposer_value']}):\n"
            prompt += f"  Rationale: {opp['rationale'][:100]}...\n"
        
        prompt += f"""
[Your Task]
Critically analyze your opponents' proposals:
1. What are the main flaws in these proposals?
2. Why is YOUR {own_proposal_id} better based on {agent['value_type']} values?

Be specific and persuasive (3-4 sentences total).
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} in final debate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 3: Criticize Opponents",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action=f"Criticize opponents from {own_proposal_id}"
            )
            
            return content
            
        except Exception as e:
            print(f"      ⚠️  Criticism failed: {e}")
            return ""
    
    def _get_defense(self, agent: Dict[str, Any], proposal_id: str, 
                     criticisms: List[Dict[str, str]]) -> str:
        """Finalist defends proposal against criticisms"""
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Your Proposal {proposal_id}]
Rationale: {self.proposals[proposal_id]['rationale'][:150]}...

[Criticisms Received]
"""
        for c in criticisms:
            if proposal_id in c['target_proposals']:
                prompt += f"From {c['from_agent_name']}: {c['content'][:150]}...\n\n"
        
        prompt += f"""
[Your Defense]
Defend your proposal against these criticisms:
- Address the main concerns raised
- Explain why your approach based on {agent['value_type']} values is still the best
- Emphasize your proposal's strengths

Keep it persuasive but concise (2-3 sentences).
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} defending your proposal."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 3: Defend Proposal",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action=f"Defend {proposal_id} against criticisms"
            )
            
            return content
            
        except Exception as e:
            print(f"      ⚠️  Defense failed: {e}")
            return ""
    
    def _get_adjustment_decision(self, agent: Dict[str, Any], proposal_id: str) -> Dict[str, Any]:
        """Proposer decides whether to adjust proposal based on discussion"""
        proposal = self.proposals[proposal_id]
        supporters = proposal['supporters']
        
        # Get suggestions and responses from discussion
        suggestions_received = [s for s in self.discussion_history['round_2']['suggestions']
                               if s['to_proposal'] == proposal_id]
        my_response = [r for r in self.discussion_history['round_2']['responses']
                      if r['proposal'] == proposal_id]
        
        discussion_summary = ""
        if suggestions_received:
            discussion_summary = "\n[Discussion Summary]\n"
            discussion_summary += f"You received {len(suggestions_received)} suggestion(s):\n"
            for s in suggestions_received:
                discussion_summary += f"- {s['from_agent_name']}: {s['content'][:80]}...\n"
            
            if my_response:
                discussion_summary += f"\nYour response: {my_response[0]['content'][:100]}...\n"
        
        prompt = f"""You are {agent['family_name']} (ID:{agent['id']}, {agent['value_type']} values).

[Your Proposal {proposal_id}]
Current supporters: {len(supporters)} agents
Rationale: {proposal['rationale']}
{discussion_summary}
[Question]After Round 2 discussion, do you want to adjust your proposal?

Options:
A. ADJUST - Modify allocation to address concerns (especially if you said you'd consider suggestions)
B. MAINTAIN - Keep proposal unchanged

Output format:
DECISION: [ADJUST or MAINTAIN]
REASON: (1-2 sentences)
"""
        
        if len(supporters) >= 5:  # Already has majority support
            prompt += "\nNote: You already have strong support."
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} deciding on adjustment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 2: Adjustment Decision",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action=f"Decide whether to adjust {proposal_id}"
            )
            
            decision_match = re.search(r'DECISION:\s*(ADJUST|MAINTAIN)', content, re.IGNORECASE)
            reason_match = re.search(r'REASON:\s*(.+)', content, re.DOTALL | re.IGNORECASE)
            
            if decision_match and decision_match.group(1).upper() == 'ADJUST':
                # For simplicity, keep same allocation but update rationale
                return {
                    'action': 'adjust',
                    'reason': reason_match.group(1).strip() if reason_match else "Adjusted based on feedback"
                }
            else:
                return {'action': 'maintain'}
                
        except Exception as e:
            return {'action': 'maintain'}
    
    def _generate_fallback_proposal(self, agent: Dict[str, Any]) -> Dict[int, float]:
        """Generate a simple fallback proposal based on agent's value type"""
        allocation = {}
        value_type = agent['value_type']
        
        if value_type == 'egalitarian':
            # Equal distribution
            per_family = self.total_grain / len(self.agents)
            allocation = {i: per_family for i in range(1, len(self.agents) + 1)}
            
        elif value_type == 'needs_based':
            # Proportional to needs
            total_needs = sum([self.survival_needs[a['id']].get('grain', 0) for a in self.agents])
            for a in self.agents:
                need = self.survival_needs[a['id']].get('grain', 0)
                allocation[a['id']] = self.total_grain * (need / total_needs)
                
        elif value_type == 'merit_based':
            # Proportional to labor force
            total_labor = sum([a.get('labor_force', 0) for a in self.agents])
            if total_labor > 0:
                for a in self.agents:
                    labor = a.get('labor_force', 0)
                    allocation[a['id']] = self.total_grain * (labor / total_labor)
            else:
                # Fallback to equal
                per_family = self.total_grain / len(self.agents)
                allocation = {i: per_family for i in range(1, len(self.agents) + 1)}
                
        else:  # altruistic, pragmatic, or unknown
            # Balanced: 50% by needs, 50% equal
            per_family = self.total_grain * 0.5 / len(self.agents)
            total_needs = sum([self.survival_needs[a['id']].get('grain', 0) for a in self.agents])
            for a in self.agents:
                need = self.survival_needs[a['id']].get('grain', 0)
                needs_share = self.total_grain * 0.5 * (need / total_needs) if total_needs > 0 else per_family
                allocation[a['id']] = per_family + needs_share
        
        return allocation
    
    def _parse_allocation_from_text(self, text: str) -> Dict[int, float]:
        """Parse allocation from LLM response - Enhanced version"""
        allocation = {}
        
        # Try multiple patterns to increase success rate
        patterns = [
            # Pattern 1: Family_X: YY.Y (most strict)
            r'Family_(\d+):\s*([\d.]+)',
            # Pattern 2: Family X: YY.Y (with space)
            r'Family\s+(\d+):\s*([\d.]+)',
            # Pattern 3: FamilyX: YY.Y (no separator)
            r'Family(\d+):\s*([\d.]+)',
            # Pattern 4: ID X: YY.Y
            r'(?:ID|id)\s*[:\s]*(\d+)[:\s]+([\d.]+)',
            # Pattern 5: Just number patterns (as last resort)
            r'(\d+)[:\s]+([\d.]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if len(matches) >= len(self.agents) * 0.7:  # If found at least 70% families
                temp_allocation = {}
                for family_id_str, amount_str in matches:
                    try:
                        family_id = int(family_id_str)
                        amount = float(amount_str)
                        if 1 <= family_id <= len(self.agents):
                            temp_allocation[family_id] = amount
                    except:
                        continue
                
                # Use this pattern if it found enough families
                if len(temp_allocation) >= len(allocation):
                    allocation = temp_allocation
                
                # If found all families, stop trying other patterns
                if len(allocation) == len(self.agents):
                    break
        
        # Check if we got all families
        if allocation and len(allocation) == len(self.agents):
            # Complete allocation - normalize to total
            total = sum(allocation.values())
            if total > 0:
                ratio = self.total_grain / total
                allocation = {k: v * ratio for k, v in allocation.items()}
            return allocation
        elif allocation and len(allocation) >= len(self.agents) * 0.7:  # At least 70% of families
            # Partial allocation - fill missing families with equal share of remainder
            print(f"    [INFO] Partial allocation ({len(allocation)}/{len(self.agents)} families), filling missing...")
            missing_ids = [i for i in range(1, len(self.agents) + 1) if i not in allocation]
            
            # Normalize existing allocations
            total_allocated = sum(allocation.values())
            if total_allocated > 0:
                ratio = self.total_grain * 0.8 / total_allocated  # Use 80% for parsed families
                allocation = {k: v * ratio for k, v in allocation.items()}
                
                # Distribute remaining 20% equally to missing families
                remainder = self.total_grain * 0.2
                if missing_ids:
                    per_missing = remainder / len(missing_ids)
                    for missing_id in missing_ids:
                        allocation[missing_id] = per_missing
                        
            return allocation
        
        return None
    
    def _validate_allocation(self, allocation: Dict[int, Dict[str, float]]):
        """Validate final allocation"""
        total = sum(a.get("grain", 0) for a in allocation.values())
        print(f"Validation: Total allocated = {total:.1f} / {self.total_grain:.1f}")
        
        if abs(total - self.total_grain) > 0.1:
            print(f"  ⚠️  Warning: Allocation mismatch")
    
    def _calculate_integrated_allocation(self, finalist_proposals: List[str], vote_results: Dict[str, float]) -> Dict[int, Dict[str, float]]:
        """Calculate integrated allocation by weighting 3 finalist proposals
        
        Weighting formula: score × support_count
        This reflects both quality (score) and popularity (support)
        
        Args:
            finalist_proposals: List of 3 proposal IDs
            vote_results: Voting scores for each proposal
            
        Returns:
            Integrated allocation dictionary
        """
        # Calculate weights
        weights = {}
        total_weight = 0.0
        
        print("  Calculating weights:\n")
        for prop_id in finalist_proposals:
            score = vote_results[prop_id]
            support_count = len(self.proposals[prop_id]['supporters'])
            weight = score * support_count
            weights[prop_id] = weight
            total_weight += weight
            
            proposer = self.proposals[prop_id]['proposer_name']
            value_type = self.proposals[prop_id]['proposer_value']
            print(f"    {prop_id} ({proposer}, {value_type}): "
                  f"score={score:.2f}, supporters={support_count}, weight={weight:.2f}")
        
        # Normalize weights to sum to 1.0
        for prop_id in weights:
            weights[prop_id] /= total_weight
        
        print(f"\n  Normalized weights:")
        for prop_id in finalist_proposals:
            print(f"    {prop_id}: {weights[prop_id]:.1%}")
        
        # Calculate integrated allocation
        integrated = {}
        for agent in self.agents:
            agent_id = agent['id']
            weighted_sum = 0.0
            
            for prop_id in finalist_proposals:
                allocation = self.proposals[prop_id]['allocation']
                weighted_sum += allocation.get(agent_id, 0.0) * weights[prop_id]
            
            integrated[agent_id] = weighted_sum
        
        # Normalize to total resources
        total = sum(integrated.values())
        if total > 0:
            ratio = self.total_grain / total
            integrated = {k: v * ratio for k, v in integrated.items()}
        
        # Display integrated allocation
        print(f"\n  Integrated allocation:")
        for agent in self.agents:
            agent_id = agent['id']
            print(f"    {agent['family_name']}: {integrated[agent_id]:.1f} units")
        
        # Convert to required format
        result = {agent_id: {"grain": amount} for agent_id, amount in integrated.items()}
        return result
    
    def _collect_feedback_on_integrated(self, integrated_allocation: Dict[int, Dict[str, float]], 
                                       vote_results: Dict[str, float]) -> tuple:
        """Collect agent feedback on integrated proposal
        
        Args:
            integrated_allocation: The integrated allocation to evaluate
            vote_results: Original voting results for context
            
        Returns:
            (acceptance_rate, adjustments_list)
        """
        acceptances = []
        adjustments = []
        
        for agent in self.agents:
            feedback = self._get_integrated_feedback(agent, integrated_allocation, vote_results)
            
            if feedback:
                accept = feedback.get('accept', False)
                acceptances.append(accept)
                
                if not accept and feedback.get('adjustment'):
                    adjustments.append({
                        'agent_id': agent['id'],
                        'agent_name': agent['family_name'],
                        'adjustment': feedback.get('adjustment')
                    })
                
                status = "✅ ACCEPT" if accept else "💭 SUGGEST ADJUSTMENT"
                print(f"  {agent['family_name']}: {status}")
                if not accept and feedback.get('adjustment'):
                    print(f"    Reason: {feedback.get('adjustment')[:80]}...")
        
        acceptance_rate = sum(acceptances) / len(acceptances) if acceptances else 0.0
        return acceptance_rate, adjustments
    
    def _get_integrated_feedback(self, agent: Dict[str, Any], integrated_allocation: Dict[int, Dict[str, float]],
                                 vote_results: Dict[str, float]) -> Dict[str, Any]:
        """Get agent's feedback on integrated proposal"""
        
        agent_id = agent['id']
        agent_amount = integrated_allocation[agent_id]['grain']
        
        # 🆕 Get value evolution context
        value_context = self._get_value_context(agent)
        
        prompt = f"""You are {agent['family_name']} (ID:{agent_id}).

[Your Values]
Original values: {agent['value_type']}
{value_context}
[Integrated Proposal]
The community has created an INTEGRATED allocation by combining the 3 finalist proposals:

Your allocation: {agent_amount:.1f} units

[Context]
This is a weighted combination of:
"""
        
        # Show breakdown from 3 proposals
        for prop_id in vote_results.keys():
            if self.proposals[prop_id]['status'] == 'active':
                original_amount = self.proposals[prop_id]['allocation'].get(agent_id, 0.0)
                proposer = self.proposals[prop_id]['proposer_name']
                value = self.proposals[prop_id]['proposer_value']
                score = vote_results[prop_id]
                prompt += f"  - {prop_id} ({proposer}, {value}): {original_amount:.1f} units (score: {score:.2f})\n"
        
        prompt += f"""
[Your Task]
Do you ACCEPT this integrated proposal, or do you suggest adjustments?

Response format:
DECISION: [ACCEPT / SUGGEST_ADJUSTMENT]
REASON: [Brief explanation]
"""
        
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": f"You are {agent['family_name']} evaluating integrated proposal."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # 🆕 Log conversations
            self._log_dialogue(
                phase="ROUND 4: Integrated Feedback",
                agent_name=agent['family_name'],
                agent_id=agent['id'],
                prompt=prompt,
                response=content,
                action="Evaluate integrated allocation"
            )
            
            # Parse response
            accept = "ACCEPT" in content.upper() and "SUGGEST_ADJUSTMENT" not in content.upper()
            
            # Extract reason
            reason_match = re.search(r'REASON:\s*(.+)', content, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else content
            
            return {
                'accept': accept,
                'adjustment': reason if not accept else None
            }
            
        except Exception as e:
            print(f"    ⚠️  Error getting feedback: {e}")
            # Default: accept
            return {'accept': True, 'adjustment': None}
    
    def _apply_minor_adjustments(self, integrated_allocation: Dict[int, Dict[str, float]], 
                                 adjustments: List[Dict]) -> Dict[int, Dict[str, float]]:
        """Apply minor adjustments to integrated allocation
        
        Strategy: Make small adjustments (±5% per family) based on suggestions
        
        Args:
            integrated_allocation: Original integrated allocation
            adjustments: List of adjustment suggestions
            
        Returns:
            Adjusted allocation
        """
        if not adjustments:
            return integrated_allocation
        
        print(f"  Applying {len(adjustments)} adjustment suggestions:\n")
        
        # For simplicity: Just log adjustments, don't actually change
        # (Could implement more sophisticated adjustment logic)
        for adj in adjustments[:3]:  # Show first 3
            print(f"    {adj['agent_name']}: {adj['adjustment'][:60]}...")
        
        # For now, return original (conservative approach)
        # Future: Could parse adjustments and apply small changes
        print(f"\n  Note: Adjustments noted but integrated proposal maintained for stability")
        return integrated_allocation
    
    def _fallback_allocation(self) -> Dict[int, Dict[str, float]]:
        """Fallback: equal distribution"""
        per_family = self.total_grain / len(self.agents)
        return {agent['id']: {"grain": per_family} for agent in self.agents}


# ===== Wrapper Function for Compatibility =====

def discussion_based_distribution(
    agents: List[Dict[str, Any]],
    total_resources: Dict[str, float],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    memory_module=None
) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
    """
    Wrapper function for Progressive Voting Negotiation mechanism
    (Compatible with simulation_runner.py interface)
    """
    negotiator = ProgressiveVotingNegotiation(
        agents=agents,
        total_resources=total_resources,
        survival_needs=survival_needs,
        round_number=round_number,
        memory_module=memory_module  # 🆕 Pass memory module for value evolution
    )
    allocation, metadata = negotiator.negotiate()
    return allocation, metadata


if __name__ == "__main__":
    print("Progressive Voting Negotiation Mechanism")
    print("Run via simulation_runner.py with method='discussion'")

