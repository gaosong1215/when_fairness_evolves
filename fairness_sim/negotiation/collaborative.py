from fairness_sim.llm_client import get_llm_client, get_model_name
import json
import re
import copy
import time
from typing import Dict, List, Any, Tuple, Optional
import math
from fairness_sim.negotiation.logger import NegotiationLogger
from fairness_sim.logging.llm_interaction import get_logger

# SettingsDeepSeekClient
client = get_llm_client()

class CollaborativeNegotiation:
    """Collaborative Negotiation Allocation Mechanism"""
    
    def __init__(self, agents: List[Dict[str, Any]], total_resources: Dict[str, float], 
                 survival_needs: Dict[int, Dict[str, float]], round_number: int = 1,
                 enable_logging: bool = True, log_dir: str = "negotiation_logs",
                 experiment_id: str = None):
        """Initialize Negotiation Mechanism
        
        Parameter:
            agents: Proxy List
            total_resources: Total Resources Dictionary
            survival_needs: Survival Needs Dictionary
            round_number: Current number of rounds
            enable_logging: Whether logging is enabled
            experiment_id: ExperimentID,Log used to unify all rounds
        """
        self.agents = agents
        self.total_resources = total_resources
        self.survival_needs = survival_needs
        self.round_number = round_number
        
        # Negotiation Status
        self.current_proposal = self._initialize_empty_proposal()
        self.conversation_history = []
        self.consensus_items = []  # Assignments on which consensus has been reached
        self.disputed_items = []   # Items still in dispute
        
        # Negotiation phase
        self.current_stage = "principles"  # principles -> framework -> details -> finalization
        self.stage_results = {}
        
        # Statistics
        self.total_grain = total_resources.get("grain", 0)
        self.total_members = sum(agent["members"] for agent in agents)
        self.total_labor = sum(agent["labor_force"] for agent in agents)
        
        # Logging
        self.enable_logging = enable_logging
        if enable_logging:
            # 🆕 Useexperiment_idAssession_id,All rounds share the same log directory
            if experiment_id:
                session_id = experiment_id
            else:
                import time
                session_id = f"round_{round_number}_{int(time.time())}"
            
            self.logger = NegotiationLogger(session_id, output_dir=log_dir)
            self.logger.start_session(
                round_number=round_number,
                participants=agents,
                total_resources=total_resources,
                survival_needs=survival_needs
            )
        else:
            self.logger = None
    
    def _initialize_empty_proposal(self) -> Dict[int, Dict[str, float]]:
        """Initialize Empty Allocation Proposal"""
        return {agent["id"]: {"grain": 0.0} for agent in self.agents}
    
    def run_collaborative_negotiation(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """Run the full collaborative negotiation process(Refactoring Edition:Focus Allocation Negotiation,Remove Values Discussion)
        
        Back:
            (Final Allocation Result, Negotiation process data)
        """
        print("\n" + "="*70)
        print("🔄 Start Collaborative Negotiation Allocation Process(Refactoring Edition)")
        print("   Focus:Assignment Negotiation | Remove:Values Discussion")
        print("="*70)
        
        try:
            # ✅ Phase1:Collect Assignment Expectations(Values-based+Family situation)
            print("\n[Phase1/3:Collect Assignment Expectations]")
            allocation_requests = self._collect_allocation_requests_v2()
            self.stage_results["allocation_requests"] = allocation_requests
            
            # ✅ Phase2:3Round of iterative negotiation
            print("\n[Phase2/3:Iterative Negotiation(3Round)]")
            final_proposal = self._three_round_negotiation_v2(allocation_requests)
            self.stage_results["negotiation_rounds"] = self.negotiation_history
            
            # ✅ Phase3:Final confirmation
            print("\n[Phase3/3:Final confirmation]")
            confirmed_proposal = self._final_confirmation_v2(final_proposal, allocation_requests)
            
            # Generate Negotiation Data(Does not containdialogue_results)
            negotiation_data = self._create_negotiation_data(True, "allocation_focused_negotiation")
            negotiation_data["allocation_requests"] = allocation_requests
            negotiation_data["negotiation_history"] = getattr(self, 'negotiation_history', [])
            
            # Session Closeout Log
            if self.logger:
                avg_satisfaction = getattr(self, "final_average_satisfaction", 0.0)
                try:
                    self.logger.end_session(
                        final_allocation=confirmed_proposal,
                        success=True,
                        average_satisfaction=avg_satisfaction
                    )
                except Exception:
                    pass
            
            print("\n✅ Negotiation completed successfully!")
            return confirmed_proposal, negotiation_data
            
        except Exception as e:
            print(f"\n❌ Error during negotiation: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Fallback to Simple Allocation
            fallback_proposal = self._create_fallback_proposal()
            negotiation_data = self._create_negotiation_data(False, "error_fallback")
            
            # Session Closeout Log(Failed)
            if self.logger:
                try:
                    self.logger.end_session(
                        final_allocation=fallback_proposal,
                        success=False,
                        failure_reason=str(e),
                        average_satisfaction=0.0
                    )
                except Exception:
                    pass
            return fallback_proposal, negotiation_data
    
    # ========================================================================
    # 🗂️ Old version methodology(Deprecated,Keep Backup)
    # ========================================================================
    
    def run_collaborative_negotiation_OLD(self) -> Tuple[Dict[int, Dict[str, float]], Dict[str, Any]]:
        """[Deprecated]Legacy Negotiation Process(Include Values Dialogue)
        
        Keep this method as a backup,To resume, rename the above method
        """
        print("\n" + "="*70)
        print("Start Collaborative Negotiation Allocation Process(Legacy)")
        print("="*70)
        
        try:
            # 🆕 Phase1:Values Exchange and Fair Understanding Exploration
            print("\n📖 Phase1:Values Exchange and Fair Understanding Exploration")
            dialogue_results = self._value_dialogue_phase()
            self.stage_results["value_dialogue"] = dialogue_results
            
            # 🆕 Phase2:Based on the Dialogue History Consultation Framework
            print("\n📊 Phase2:Negotiated Allocation Framework")
            framework = self._negotiate_framework_with_dialogue(dialogue_results)
            self.stage_results["framework"] = framework
            
            # Phase3:Build detailed scenarios
            print("\n📋 Phase3:Build Detailed Allocation Scenario")
            detailed_proposal = self._build_detailed_proposal(framework)
            self.stage_results["detailed_proposal"] = detailed_proposal
            
            # Phase4:Final confirmation and adjustment
            print("\n✔️ Phase4:Final confirmation and fine-tuning")
            final_proposal = self._finalize_proposal(detailed_proposal)
            
            # Generate Negotiation Data
            negotiation_data = self._create_negotiation_data(True, "dialogue_driven_consensus")
            negotiation_data["dialogue_results"] = dialogue_results
            
            # Session Closeout Log
            if self.logger:
                avg_satisfaction = getattr(self, "final_average_satisfaction", 0.0)
                try:
                    self.logger.end_session(
                        final_allocation=final_proposal,
                        success=True,
                        average_satisfaction=avg_satisfaction
                    )
                except Exception:
                    pass
            
            print("\n✅ Negotiation completed successfully!")
            return final_proposal, negotiation_data
            
        except Exception as e:
            print(f"\n❌ Error during negotiation: {str(e)}")
            # Fallback to Simple Allocation
            fallback_proposal = self._create_fallback_proposal()
            negotiation_data = self._create_negotiation_data(False, "error_fallback")
            
            # Session Closeout Log(Failed)
            if self.logger:
                try:
                    self.logger.end_session(
                        final_allocation=fallback_proposal,
                        success=False,
                        failure_reason=str(e),
                        average_satisfaction=0.0
                    )
                except Exception:
                    pass
            return fallback_proposal, negotiation_data
    
    def _establish_principles(self) -> Dict[str, Any]:
        """Phase1:Determine distribution principles"""
        self.current_stage = "principles"
        
        # Start Logging
        if self.logger:
            self.logger.start_stage("establish_principles", [agent["id"] for agent in self.agents])
        
        # 1.1 Collect principled preferences of each family
        print("\n   Collect distribution principle preferences for each household...")
        principle_preferences = {}
        
        for agent in self.agents:
            preference = self._get_principle_preference(agent)
            principle_preferences[agent["id"]] = preference
            print(f"    {agent['family_name']}Home:{preference['summary']}")
            
            # Record Principle Preference
            if self.logger:
                self.logger.log_discussion_turn(
                    speaker_id=agent["id"],
                    speaker_name=agent["family_name"],
                    speaker_value_type=agent["value_type"],
                    content=preference["raw_response"],
                    speech_type="principle_preference",
                    target_topic="Allocation Principle Preference"
                )
        
        # 1.2 Identify common principles
        print("\n   Look for common principles...")
        common_principles = self._find_common_principles(principle_preferences)
        
        # Document common principles decisions
        if self.logger and common_principles:
            self.logger.log_decision(
                decision_type="common_principles_identified",
                decision_content=common_principles,
                supporters=list(range(1, len(self.agents) + 1)),  # Principles everyone supports
                opponents=[]
            )
        
        # 1.3 Discuss disputed principles
        print("\n   Discuss disputed principles...")
        discussed_principles = self._discuss_disputed_principles(principle_preferences, common_principles)
        
        # 1.4 Determine final principles
        final_principles = {**common_principles, **discussed_principles}
        
        print(f"\n   Determined Distribution Principle:")
        for key, value in final_principles.items():
            print(f"    - {key}: {value}")
        
        # End Stage Record
        if self.logger:
            consensus_level = len(final_principles) / max(len(principle_preferences), 1)
            self.logger.end_stage(
                stage_outcome=f"Confirmed{len(final_principles)}allocation principle",
                consensus_level=consensus_level
            )
        
        return final_principles
    
    def _get_principle_preference(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Get Principle Preferences for Agents"""
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

Family situation:
- Number of members:{agent['members']}People
- Workforce:{agent['labor_force']}People
- Core Beliefs:{agent['core_beliefs'][0]}

Community Situation:
- Total resources:{self.total_grain:.1f}Unit crop
- Total population:{self.total_members}People
- Total Workforce:{self.total_labor}People

Now the community needs to identify the basic principles of resource allocation.Please state what you think is most important3allocation principle,and briefly explain why.

Possible principles to consider include, but are not limited to,:
- Allocate as needed(Prioritize basic survival needs)
- Distribution according to work(Distribution based on workforce contribution)
- Equal distribution(Equal share for each person or household)
- Caring for the vulnerable(More support for families in need)
- Efficiency first(Ensuring the most efficient use of resources)
- Sustainability(Reserve resources for long-term development)

Please answer in the following format:
Principles1:[Principle Name] - [Brief reason]
Principles2:[Principle Name] - [Brief reason] 
Principles3:[Principle Name] - [Brief reason]
"""
        
        model_name = get_model_name()
        temperature = 0.7
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative involved in community consultation,Based on your values and family situation,Honestly express your preference for distribution principles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=400
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            principles = self._parse_principles(content)
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="principles",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={
                        "principles": principles,
                        "summary": f"Emphasis{principles[0] if principles else 'Balanced Development'}"
                    }
                )
            
            return {
                "raw_response": content,
                "principles": principles,
                "summary": f"Emphasis{principles[0] if principles else 'Balanced Development'}"
            }
            
        except Exception as e:
            print(f"Get{agent['family_name']}Home Principle Preference Failure: {str(e)}")
            
            # Record failedLLMCall
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="principles",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=f"Failed to fetch: {str(e)}",
                    model=model_name,
                    temperature=temperature,
                    duration=0.0,
                    success=False
                )
            
            return {
                "raw_response": "Failed to fetch",
                "principles": ["Allocate as needed", "Fair and reasonable", "Sustainability"],
                "summary": "Balanced Development"
            }
    
    def _parse_principles(self, content: str) -> List[str]:
        """Analytic Principle Response"""
        principles = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if re.match(r'Principles[123][::]', line):
                # Extraction Principle Name(Before the colon to the first"-"or"-"Part between)
                match = re.search(r'Principles[123][::]\s*([^--]+)', line)
                if match:
                    principle = match.group(1).strip()
                    principles.append(principle)
        
        # If parsing fails,Back to Default Principles
        if not principles:
            principles = ["Equitable distribution", "Satisfy basic needs", "Consider Contribution"]
        
        return principles[:3]  # Max.3principles
    
    def _find_common_principles(self, principle_preferences: Dict[int, Dict[str, Any]]) -> Dict[str, str]:
        """Look for common principles"""
        # Count all the principles mentioned
        principle_counts = {}
        
        for agent_id, pref in principle_preferences.items():
            for principle in pref["principles"]:
                # Normalization Principle Name
                normalized = self._normalize_principle_name(principle)
                principle_counts[normalized] = principle_counts.get(normalized, 0) + 1
        
        # Identify principles that are supported by the majority(More than half)
        threshold = len(self.agents) // 2 + 1
        common_principles = {}
        
        for principle, count in principle_counts.items():
            if count >= threshold:
                common_principles[principle] = f"Get{count}/{len(self.agents)}Family Support"
        
        return common_principles
    
    def _normalize_principle_name(self, principle: str) -> str:
        """Normalization Principle Name"""
        # Simple Keyword Match Normalization
        principle_lower = principle.lower()
        
        if any(word in principle_lower for word in ["On-demand", "Demand", "Basic needs"]):
            return "Allocate as needed"
        elif any(word in principle_lower for word in ["As per work", "Contribution", "Labor"]):
            return "Distribution according to work"
        elif any(word in principle_lower for word in ["Equality", "Equal", "Same"]):
            return "Equal distribution"
        elif any(word in principle_lower for word in ["Vulnerable", "Hard", "Care"]):
            return "Caring for the vulnerable"
        elif any(word in principle_lower for word in ["Efficiency", "Active"]):
            return "Efficiency first"
        elif any(word in principle_lower for word in ["Sustainable", "Long-term", "Development"]):
            return "Sustainability"
        else:
            return principle  # Keep original name
    
    def _discuss_disputed_principles(self, principle_preferences: Dict[int, Dict[str, Any]], 
                                   common_principles: Dict[str, str]) -> Dict[str, str]:
        """Discuss disputed principles"""
        
        # Identify principles where there is no consensus but there is support
        all_mentioned = {}
        for pref in principle_preferences.values():
            for principle in pref["principles"]:
                normalized = self._normalize_principle_name(principle)
                if normalized not in common_principles:
                    all_mentioned[normalized] = all_mentioned.get(normalized, 0) + 1
        
        # Choose the most controversial2principles for discussion.
        disputed = sorted(all_mentioned.items(), key=lambda x: x[1], reverse=True)[:2]
        
        discussed_results = {}
        
        for principle_name, support_count in disputed:
            print(f"\n     Discussion Principles:{principle_name} (Current Support:{support_count}/{len(self.agents)})")
            
            # Allow supporters and opponents to express their views
            discussion_result = self._moderate_principle_discussion(principle_name, principle_preferences)
            discussed_results[principle_name] = discussion_result
        
        return discussed_results
    
    def _moderate_principle_discussion(self, principle_name: str, 
                                     principle_preferences: Dict[int, Dict[str, Any]]) -> str:
        """Leading the Principles Discussion"""
        
        # Identify supporters and opponents
        supporters = []
        others = []
        
        for agent in self.agents:
            agent_principles = [self._normalize_principle_name(p) for p in 
                             principle_preferences[agent["id"]]["principles"]]
            if principle_name in agent_principles:
                supporters.append(agent)
            else:
                others.append(agent)
        
        # Document Disputes
        if self.logger and len(supporters) > 1 and len(others) > 0:
            self.logger.log_conflict(
                conflict_topic=f"Principles:{principle_name}",
                conflicting_parties=[agent["id"] for agent in others],
                conflict_description=f"{len(supporters)}Home Support,{len(others)}Home Opposition or Neutrality"
            )
        
        # If there are too few supporters,Discard Directly
        if len(supporters) <= 1:
            return f"Insufficient support,Not Adopted"
        
        # Convince a supporter
        if supporters:
            advocate = supporters[0]  # Choose your first supporter as an advocate
            persuasion = self._generate_principle_persuasion(advocate, principle_name)
            
            # Record Persuasive Speech
            if self.logger:
                self.logger.log_discussion_turn(
                    speaker_id=advocate["id"],
                    speaker_name=advocate["family_name"],
                    speaker_value_type=advocate["value_type"],
                    content=persuasion,
                    speech_type="persuasion",
                    target_topic=f"is the principle'{principle_name}'Persuasion"
                )
            
            # Evaluate Persuasion Effectiveness
            convinced_count = self._evaluate_persuasion_effect(persuasion, others, principle_name)
            
            total_support = len(supporters) + convinced_count
            result_msg = ""
            if total_support >= len(self.agents) // 2 + 1:
                result_msg = f"Obtained after discussion{total_support}/{len(self.agents)}Family Support,Adoption"
                # Record Decision
                if self.logger:
                    self.logger.log_decision(
                        decision_type="principle_adopted",
                        decision_content={principle_name: "Adoption"},
                        supporters=[agent["id"] for agent in supporters] + [others[i]["id"] for i in range(convinced_count)],
                        opponents=[agent["id"] for agent in others[convinced_count:]]
                    )
            else:
                result_msg = f"Discussion is still only{total_support}/{len(self.agents)}Family Support,Not Adopted"
                
            return result_msg
        
        return "Discussion No results"
    
    def _generate_principle_persuasion(self, advocate: Dict[str, Any], principle_name: str) -> str:
        """Generative Principle Persuasion Discourse"""
        prompt = f"""You are{advocate['family_name']}Representatives of the family,You support"{principle_name}"This distribution principle.

Now you need to explain to other families why this principle is good for the whole community,Try to convince them to support this principle.

Your family background:{advocate['background']}
Your core beliefs:{advocate['core_beliefs'][0]}

Community Situation:
- Total resources:{self.total_grain:.1f}Unit crop
- Total population:{self.total_members}People
- Total Workforce:{self.total_labor}People

Please use simple and powerful language(No more than100Words)Explain:
1. Why this principle is in the interest of the community as a whole
2. How this principle helps communities thrive in the long term
3. Call for additional family support

Request:Language sincerity,Reasonable arguments,Consider the interests of other families.
"""
        
        model_name = get_model_name()
        temperature = 0.6
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a communicative and persuasive ambassador,Please speak in a sincere and rational way."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=200
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="principles-persuasion",
                    agent=advocate,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={
                        "principle_name": principle_name,
                        "persuasion_type": "Convincing Other Families to Support Principles"
                    }
                )
            
            return content
            
        except Exception as e:
            fallback = f"I think{principle_name}It's important for the long-term development of our community,We hope you'll support us."
            
            # Record failedLLMCall
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="principles-persuasion",
                    agent=advocate,
                    input_prompt=prompt,
                    raw_output=f"Failed to fetch: {str(e)}",
                    model=model_name,
                    temperature=temperature,
                    duration=0.0,
                    success=False
                )
            
            return fallback
    
    def _evaluate_persuasion_effect(self, persuasion: str, others: List[Dict[str, Any]], 
                                   principle_name: str) -> int:
        """Evaluate Persuasion Effectiveness"""
        convinced_count = 0
        
        for agent in others:
            # Simplified Persuasion Assessment
            agent_value = agent["value_type"]
            
            # Judging whether to be persuaded based on value fit
            if principle_name == "Allocate as needed" and agent_value in ["needs_based", "altruistic"]:
                convinced_count += 1
            elif principle_name == "Distribution according to work" and agent_value in ["merit_based", "pragmatic"]:
                convinced_count += 1
            elif principle_name == "Equal distribution" and agent_value in ["egalitarian", "altruistic"]:
                convinced_count += 1
            elif principle_name == "Caring for the vulnerable" and agent_value in ["altruistic", "needs_based"]:
                convinced_count += 1
            elif principle_name == "Efficiency first" and agent_value in ["merit_based", "pragmatic"]:
                convinced_count += 1
            elif principle_name == "Sustainability" and agent_value == "pragmatic":
                convinced_count += 1
        
        return convinced_count
    
    def _negotiate_framework(self, principles: Dict[str, str]) -> Dict[str, Any]:
        """Phase2:Negotiated Allocation Framework(🆕 LLMDrive)"""
        self.current_stage = "framework"
        
        # Start Framework Negotiation Phase
        if self.logger:
            self.logger.start_stage("negotiate_framework", [agent["id"] for agent in self.agents])
        
        print("\n   🆕 Gather resource ratio suggestions for each household...")
        
        # 🔥 Add:Collect Initial Proposal(Use existing_collect_ratio_proposalsMethod)
        ratio_proposals = self._collect_ratio_proposals(principles)
        
        # 🔥 Add:Summarize and identify disputes
        aggregated = self._aggregate_ratio_proposals(ratio_proposals)
        disputes = self._identify_ratio_disputes_enhanced(ratio_proposals, aggregated)
        
        # 🔥 Add:Conditional Multi-Round Negotiation
        if not disputes:
            print("   ✅ No apparent disputes,Direct access to the initial proposal")
            final_proposals = ratio_proposals
            negotiation_data = {"method": "direct_acceptance", "rounds": 0}
        else:
            print(f"   🔥 Recognized{len(disputes)}disputed points,Start Multiple Negotiations...")
            final_proposals, negotiation_log = self._conduct_multi_round_negotiation(
                ratio_proposals, disputes, principles
            )
            negotiation_data = {
                "method": "multi_round",
                "rounds": len(negotiation_log),
                "log": negotiation_log
            }
        
        # 🔥 Add:Building a family-level proportional dictionary
        allocation_ratios = {
            aid: p.get("current_ratio", p.get("ideal_ratio", p.get("suggested_ratio")))
            for aid, p in final_proposals.items()
        }
        
        # 🔥 Add:Backllm_negotiatedIdentification
        framework = {
            "strategy": {
                "name": "LLMDrive Negotiated Allocation",
                "base_method": "llm_negotiated",  # ⬅️ Key Identification
                "description": f"Via{negotiation_data.get('rounds', 0)}Round of negotiation reached"
            },
            "ratios": allocation_ratios,
            "negotiated_ratios": allocation_ratios,
            "negotiation_data": negotiation_data,
            "based_on_principles": list(principles.keys())
        }
        
        print(f"\n   ✅ Negotiation complete:{framework['strategy']['name']}")
        
        # End Frame Phase
        if self.logger:
            self.logger.end_stage(
                stage_outcome=f"Negotiate to reach consensus" if negotiation_data.get("method") == "direct_acceptance" else f"Meridian{negotiation_data['rounds']}Round Negotiation",
                consensus_level=0.9
            )
        
        return framework
    
    def _determine_allocation_strategy(self, principles: Dict[str, str]) -> Dict[str, Any]:
        """Determine allocation strategy based on principles"""
        
        principle_names = list(principles.keys())
        
        # Identify strategies based on dominant principles
        if "Allocate as needed" in principle_names and "Caring for the vulnerable" in principle_names:
            return {
                "name": "Needs First Strategy",
                "description": "Prioritize basic needs,Special care for families in difficulty",
                "base_method": "needs_first"
            }
        elif "Distribution according to work" in principle_names and "Efficiency first" in principle_names:
            return {
                "name": "Contribution-oriented strategies", 
                "description": "Distribution based on labor contribution,Incentivize efficient production",
                "base_method": "contribution_based"
            }
        elif "Equal distribution" in principle_names:
            return {
                "name": "Equality Fundamentals Strategy",
                "description": "Distribute as equitably as possible while ensuring basic needs",
                "base_method": "equality_based"
            }
        else:
            return {
                "name": "Hybrid Balancing Strategies",
                "description": "Balanced distribution considering multiple factors",
                "base_method": "balanced_hybrid"
            }
    
    def _negotiate_allocation_ratios(self, principles: Dict[str, str], 
                                   strategy: Dict[str, Any]) -> Dict[str, float]:
        """Negotiated allocation ratio"""
        
        # Determine initial ratios based on strategy and principles
        base_ratios = self._get_base_ratios(strategy)
        
        # Let the agent discuss and adjust the ratio
        adjusted_ratios = self._discuss_ratio_adjustments(base_ratios, principles)
        
        return adjusted_ratios
    
    def _get_base_ratios(self, strategy: Dict[str, Any]) -> Dict[str, float]:
        """Get Base Allocation Ratio"""
        
        if strategy["base_method"] == "needs_first":
            return {
                "survival_guarantee": 0.6,  # 60%Used to ensure survival needs
                "additional_support": 0.25,  # 25%For additional support
                "community_reserve": 0.15   # 15%As a community reserve
            }
        elif strategy["base_method"] == "contribution_based":
            return {
                "survival_guarantee": 0.4,  # 40%Guaranteed basic survival
                "contribution_reward": 0.5,  # 50%Distribution by Contribution
                "community_reserve": 0.1    # 10%Community Reserve
            }
        elif strategy["base_method"] == "equality_based":
            return {
                "survival_guarantee": 0.5,  # 50%Survival Guaranteed
                "equal_distribution": 0.4,  # 40%Equal distribution
                "community_reserve": 0.1    # 10%Reserves
            }
        else:  # balanced_hybrid
            return {
                "survival_guarantee": 0.45,  # 45%Survival Guaranteed
                "merit_portion": 0.25,      # 25%By Contribution
                "equal_portion": 0.2,       # 20%Equal distribution
                "community_reserve": 0.1    # 10%Reserves
            }
    
    def _discuss_ratio_adjustments(self, base_ratios: Dict[str, float], 
                                 principles: Dict[str, str]) -> Dict[str, float]:
        """Discussion Ratio Ad"""
        
        print(f"    Initial Scale Scheme:{base_ratios}")
        
        # Seek advice from families on matching
        adjustment_suggestions = {}
        
        for agent in self.agents:
            suggestion = self._get_ratio_adjustment_suggestion(agent, base_ratios, principles)
            adjustment_suggestions[agent["id"]] = suggestion
            
            if suggestion["has_adjustment"]:
                print(f"    {agent['family_name']}Home Advice:{suggestion['suggestion']}")
                
                # Record Proportional Adjustment Sug
                if self.logger:
                    self.logger.log_discussion_turn(
                        speaker_id=agent["id"],
                        speaker_name=agent["family_name"],
                        speaker_value_type=agent["value_type"],
                        content=suggestion["suggestion"],
                        speech_type="ratio_adjustment_suggestion",
                        target_topic="Allocation Ratio Adjust"
                    )
        
        # Identify agreed-upon adjustments
        final_ratios = self._apply_consensus_adjustments(base_ratios, adjustment_suggestions)
        
        print(f"    Final Ratio Scheme:{final_ratios}")
        return final_ratios
    
    def _get_ratio_adjustment_suggestion(self, agent: Dict[str, Any], base_ratios: Dict[str, float],
                                       principles: Dict[str, str]) -> Dict[str, Any]:
        """Get proportional adjustment suggestions"""
        
        # Determine if adjustments are needed based on agency values
        value_type = agent["value_type"]
        has_adjustment = False
        suggestion = ""
        
        if value_type == "altruistic" and base_ratios.get("survival_guarantee", 0) < 0.5:
            has_adjustment = True
            suggestion = "It is recommended to increase the survival guarantee ratio to50%Above"
        elif value_type == "merit_based" and base_ratios.get("contribution_reward", 0) < 0.4:
            has_adjustment = True
            suggestion = "It is recommended to increase the proportion allocated by contribution"
        elif value_type == "egalitarian" and base_ratios.get("equal_distribution", 0) < 0.3:
            has_adjustment = True
            suggestion = "Suggest an increase in the proportion of equal distribution"
        
        return {
            "has_adjustment": has_adjustment,
            "suggestion": suggestion,
            "agent_id": agent["id"]
        }
    
    def _apply_consensus_adjustments(self, base_ratios: Dict[str, float], 
                                   suggestions: Dict[int, Dict[str, Any]]) -> Dict[str, float]:
        """Apply Consensus Adjustment"""
        
        # Simplified processing:If more than half of the agents recommend the same adjustment,then apply
        adjusted_ratios = base_ratios.copy()
        
        # Suggested statistical adjustments
        adjustment_counts = {}
        for suggestion in suggestions.values():
            if suggestion["has_adjustment"]:
                key = suggestion["suggestion"]
                adjustment_counts[key] = adjustment_counts.get(key, 0) + 1
        
        # Apply Consensus Adjustment(More than half supported)
        threshold = len(self.agents) // 2 + 1
        
        for adjustment, count in adjustment_counts.items():
            if count >= threshold:
                # Simplified Adjustment Logic
                if "Survival Guarantee" in adjustment and "50%" in adjustment:
                    if "survival_guarantee" in adjusted_ratios:
                        old_value = adjusted_ratios["survival_guarantee"]
                        adjusted_ratios["survival_guarantee"] = max(0.5, old_value)
                        # Adjust other proportions accordingly
                        self._rebalance_ratios(adjusted_ratios)
        
        return adjusted_ratios
    
    def _rebalance_ratios(self, ratios: Dict[str, float]) -> None:
        """Rebalance Ratio,Ensure the sum is1"""
        total = sum(ratios.values())
        if total != 1.0:
            # Scale all items
            for key in ratios:
                ratios[key] = ratios[key] / total
    
    def _establish_priority_order(self, principles: Dict[str, str]) -> List[str]:
        """Determine Assignment Priority"""
        
        priority_order = []
        
        # Prioritization based on principles
        if "Allocate as needed" in principles or "Caring for the vulnerable" in principles:
            priority_order.append("Satisfy basic survival needs")
        
        if "Distribution according to work" in principles:
            priority_order.append("Distribution by Labor Contribution")
        
        if "Equal distribution" in principles:
            priority_order.append("Ensure distribution fairness")
        
        if "Sustainability" in principles:
            priority_order.append("Reserve development resources")
        
        # Ensure there is at least a basic priority
        if not priority_order:
            priority_order = ["Satisfy basic survival needs", "Fair and equitable distribution"]
        
        return priority_order
    
    def _build_detailed_proposal(self, framework: Dict[str, Any]) -> Dict[int, Dict[str, float]]:
        """Phase3:Build Detailed Allocation Scenario(🆕 SupportLLMNegotiation)"""
        self.current_stage = "details"
        
        # Start phase log
        if self.logger:
            try:
                self.logger.start_stage("details", [agent["id"] for agent in self.agents])
            except Exception:
                pass
        
        # 🔥 Add:Check if yesLLMOutcome of the consultation
        strategy = framework.get("strategy", {})
        base_method = strategy.get("base_method", "")
        
        if base_method == "llm_negotiated" or base_method == "dialogue_negotiated":
            print("\n   🔥 UseLLMNegotiated proportions directly allocated...")
            initial_allocation = self._allocate_by_negotiated_ratios(framework["negotiated_ratios"])
        else:
            print("\n   Calculate Preliminary Allocation from Framework...")
            # 3.1 Calculate Preliminary Base Allocation
            initial_allocation = self._calculate_base_allocation(framework)
        initial_allocation = self._handle_special_cases(initial_allocation, framework)
        initial_allocation = self._validate_and_optimize(initial_allocation)
        
        print("\n   Preliminary Allocation:")
        for agent in self.agents:
            agent_id = agent["id"]
            allocation = initial_allocation.get(agent_id, {})
            total = sum(allocation.values())
            print(f"    {agent['family_name']}Home:{total:.2f}Unit")
        
        # Record Preliminary Allocation
        if self.logger:
            try:
                per_agent_totals = {aid: sum(res.values()) for aid, res in initial_allocation.items()}
                self.logger.log_decision(
                    decision_type="initial_allocation_proposed",
                    decision_content={
                        "strategy": framework.get("strategy", {}),
                        "ratios": framework.get("ratios", {}),
                        "per_agent_total": per_agent_totals
                    },
                    supporters=[agent["id"] for agent in self.agents],
                    opponents=[]
                )
            except Exception:
                pass
        
        # 🎯 3.2 Allow families to comment on preliminary plans and request adjustments
        print("\n   Seek the families' views on the initial plan...")
        allocation_opinions = self._collect_allocation_opinions(initial_allocation, framework)
        
        # 🎯 3.3 Identify and discuss disputed allocations
        print("\n   Handling Allocation Objections...")
        disputed_agents = [aid for aid, op in allocation_opinions.items() 
                          if op.get("has_objection", False)]
        
        if disputed_agents:
            print(f"    Discover {len(disputed_agents)} Home Disputed,Start negotiation...")
            negotiated_allocation = self._negotiate_disputed_allocations(
                initial_allocation, allocation_opinions, framework
            )
        else:
            print("    No major objections by family")
            negotiated_allocation = initial_allocation
        
        # 3.4 Final Validation
        print("\n   Final Allocation Scenario:")
        final_allocation = self._validate_and_optimize(negotiated_allocation)
        for agent in self.agents:
            agent_id = agent["id"]
            allocation = final_allocation.get(agent_id, {})
            total = sum(allocation.values())
            print(f"    {agent['family_name']}Home:{total:.2f}Unit")
        
        # End Phase Log
        if self.logger:
            try:
                satisfied = 0
                for agent in self.agents:
                    aid = agent["id"]
                    got = sum(final_allocation.get(aid, {}).values())
                    need = sum(self.survival_needs.get(aid, {}).values())
                    if need <= 0 or got >= need:
                        satisfied += 1
                consensus_level = satisfied / len(self.agents) if self.agents else 0.0
                self.logger.end_stage(
                    stage_outcome="Detailed Protocol Consultation Completed",
                    consensus_level=consensus_level
                )
            except Exception:
                pass
        
        return final_allocation
    
    def _calculate_base_allocation(self, framework: Dict[str, Any]) -> Dict[int, Dict[str, float]]:
        """Calculate Base Allocation"""
        
        strategy = framework["strategy"]["base_method"]
        ratios = framework["ratios"]
        
        if strategy == "needs_first":
            return self._calculate_needs_first_allocation(ratios)
        elif strategy == "contribution_based":
            return self._calculate_contribution_allocation(ratios)
        elif strategy == "equality_based":
            return self._calculate_equality_allocation(ratios)
        else:  # balanced_hybrid
            return self._calculate_hybrid_allocation(ratios)
    
    def _calculate_needs_first_allocation(self, ratios: Dict[str, float]) -> Dict[int, Dict[str, float]]:
        """Requirement Priority Allocation Calc"""
        allocation = self._initialize_empty_proposal()
        
        # Step 1:Guaranteed survival needs
        survival_budget = self.total_grain * ratios["survival_guarantee"]
        remaining_budget = self.total_grain - survival_budget
        
        # Meeting the basic survival needs of all families
        total_survival_needs = sum(
            sum(needs.values()) for needs in self.survival_needs.values()
        )
        
        for agent in self.agents:
            agent_id = agent["id"]
            agent_needs = sum(self.survival_needs.get(agent_id, {}).values())
            
            if total_survival_needs > 0:
                survival_share = (agent_needs / total_survival_needs) * survival_budget
                allocation[agent_id]["grain"] = survival_share
        
        # Step 2:Remaining resources are allocated according to the level of demand
        if remaining_budget > 0:
            # Calculate the intensity of demand for each household(Consider household size and dependency ratio)
            need_weights = {}
            total_weight = 0
            
            for agent in self.agents:
                agent_id = agent["id"]
                members = agent["members"]
                labor_force = agent["labor_force"]
                dependency_ratio = members / labor_force if labor_force > 0 else 2.0
                
                # Demand weight = Number of members * Dependency Ratio
                weight = members * dependency_ratio
                need_weights[agent_id] = weight
                total_weight += weight
            
            # Allocate remaining resources by weight
            for agent in self.agents:
                agent_id = agent["id"]
                if total_weight > 0:
                    additional_share = (need_weights[agent_id] / total_weight) * remaining_budget
                    allocation[agent_id]["grain"] += additional_share
        
        return allocation
    
    def _calculate_contribution_allocation(self, ratios: Dict[str, float]) -> Dict[int, Dict[str, float]]:
        """Contribution-oriented allocation calculation"""
        allocation = self._initialize_empty_proposal()
        
        # Step 1:Guaranteed basic survival
        survival_budget = self.total_grain * ratios["survival_guarantee"]
        contribution_budget = self.total_grain * ratios["contribution_reward"]
        
        # Allocate Survival Resources to Minimum Requirements
        for agent in self.agents:
            agent_id = agent["id"]
            min_survival = sum(self.survival_needs.get(agent_id, {}).values())
            allocation[agent_id]["grain"] = min_survival
        
        # Step 2:Allocate surplus resources based on labor contribution
        if self.total_labor > 0:
            for agent in self.agents:
                agent_id = agent["id"]
                labor_force = agent["labor_force"]
                contribution_share = (labor_force / self.total_labor) * contribution_budget
                allocation[agent_id]["grain"] += contribution_share
        
        return allocation
    
    def _calculate_equality_allocation(self, ratios: Dict[str, float]) -> Dict[int, Dict[str, float]]:
        """Equal Distribution Calculation"""
        allocation = self._initialize_empty_proposal()
        
        # Simple Equal Distribution
        per_family_share = self.total_grain / len(self.agents)
        
        for agent in self.agents:
            agent_id = agent["id"]
            allocation[agent_id]["grain"] = per_family_share
        
        return allocation
    
    def _calculate_hybrid_allocation(self, ratios: Dict[str, float]) -> Dict[int, Dict[str, float]]:
        """Hybrid Allocation Calculation"""
        allocation = self._initialize_empty_proposal()
        
        # Multi-layered allocation
        survival_budget = self.total_grain * ratios["survival_guarantee"]
        merit_budget = self.total_grain * ratios["merit_portion"]
        equal_budget = self.total_grain * ratios["equal_portion"]
        
        # Layer1:Survival Guarantee
        for agent in self.agents:
            agent_id = agent["id"]
            min_survival = sum(self.survival_needs.get(agent_id, {}).values())
            allocation[agent_id]["grain"] = min(min_survival, survival_budget / len(self.agents))
        
        # Layer2:Distribution according to work
        if self.total_labor > 0:
            for agent in self.agents:
                agent_id = agent["id"]
                labor_share = (agent["labor_force"] / self.total_labor) * merit_budget
                allocation[agent_id]["grain"] += labor_share
        
        # Layer3:Equal distribution
        equal_share = equal_budget / len(self.agents)
        for agent in self.agents:
            agent_id = agent["id"]
            allocation[agent_id]["grain"] += equal_share
        
        return allocation
    
    def _handle_special_cases(self, base_allocation: Dict[int, Dict[str, float]], 
                            framework: Dict[str, Any]) -> Dict[int, Dict[str, float]]:
        """Handling Extenuating Circumst"""
        adjusted_allocation = copy.deepcopy(base_allocation)
        
        # Check if any families are under-allocated
        for agent in self.agents:
            agent_id = agent["id"]
            min_survival = sum(self.survival_needs.get(agent_id, {}).values())
            current_allocation = adjusted_allocation[agent_id]["grain"]
            
            if current_allocation < min_survival:
                # Resources need to be redeployed from other households
                deficit = min_survival - current_allocation
                # Record Conflict:Survival Not Satisfied
                if self.logger:
                    try:
                        self.logger.log_conflict(
                            conflict_topic="Survival Not Satisfied",
                            conflicting_parties=[agent_id],
                            conflict_description=f"Gap={deficit:.2f}"
                        )
                    except Exception:
                        pass
                self._redistribute_for_survival(adjusted_allocation, agent_id, deficit)
        
        return adjusted_allocation
    
    def _redistribute_for_survival(self, allocation: Dict[int, Dict[str, float]], 
                                 needy_agent_id: int, deficit: float) -> None:
        """Reallocate resources for survival needs"""
        
        # Find out which families are left
        surplus_agents = []
        
        for agent in self.agents:
            agent_id = agent["id"]
            if agent_id == needy_agent_id:
                continue
                
            current = allocation[agent_id]["grain"]
            min_needed = sum(self.survival_needs.get(agent_id, {}).values())
            
            if current > min_needed:
                surplus = current - min_needed
                surplus_agents.append((agent_id, surplus))
        
        # Sort by Remaining,Deployment starts with the most left
        surplus_agents.sort(key=lambda x: x[1], reverse=True)
        
        remaining_deficit = deficit
        
        for agent_id, surplus in surplus_agents:
            if remaining_deficit <= 0:
                break
            
            transfer_amount = min(surplus * 0.5, remaining_deficit)  # Transfer up to half remaining
            
            allocation[agent_id]["grain"] -= transfer_amount
            allocation[needy_agent_id]["grain"] += transfer_amount
            remaining_deficit -= transfer_amount
            
            # Record each redistribution
            if self.logger and transfer_amount > 0:
                try:
                    self.logger.log_decision(
                        decision_type="survival_redistribution",
                        decision_content={
                            "from": agent_id,
                            "to": needy_agent_id,
                            "amount": transfer_amount
                        },
                        supporters=[agent_id],
                        opponents=[]
                    )
                except Exception:
                    pass
    
    def _collect_allocation_opinions(self, allocation: Dict[int, Dict[str, float]], 
                                   framework: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Gather comments from families on the initial allocation plan"""
        opinions = {}
        
        for agent in self.agents:
            agent_id = agent["id"]
            allocated_amount = sum(allocation.get(agent_id, {}).values())
            survival_need = sum(self.survival_needs.get(agent_id, {}).values())
            
            opinion = self._get_allocation_opinion(
                agent, allocated_amount, survival_need, allocation, framework
            )
            opinions[agent_id] = opinion
            
            # Record comments
            if self.logger and opinion.get("has_objection"):
                self.logger.log_discussion_turn(
                    speaker_id=agent_id,
                    speaker_name=agent["family_name"],
                    speaker_value_type=agent["value_type"],
                    content=opinion.get("objection_reason", ""),
                    speech_type="allocation_objection",
                    target_topic="Preliminary Allocation"
                )
        
        return opinions
    
    def _get_allocation_opinion(self, agent: Dict[str, Any], allocated_amount: float,
                              survival_need: float, all_allocations: Dict[int, Dict[str, float]],
                              framework: Dict[str, Any]) -> Dict[str, Any]:
        """Get individual family opinions on the distribution plan(LLMDrive)"""
        
        # Construct descriptions of other household allocations
        other_allocations_str = ""
        for other_agent in self.agents:
            if other_agent["id"] != agent["id"]:
                other_amount = sum(all_allocations.get(other_agent["id"], {}).values())
                other_need = sum(self.survival_needs.get(other_agent["id"], {}).values())
                other_allocations_str += f"- {other_agent['family_name']}Home({other_agent['members']}People,{other_agent['labor_force']}Labor):Assign{other_amount:.1f}Unit,Survival Needs{other_need:.1f}\n"
        
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

Current Consultation Progress:Community has identified the allocation framework({framework['strategy']['name']}),Preliminary calculations of specific allocation figures now need to be discussed.

What's happening in your home:
- Number of members:{agent['members']}People
- Workforce:{agent['labor_force']}People
- Survival Needs:{survival_need:.1f}Unit grain
- Initial Allocation:{allocated_amount:.1f}Unit grain
- Surplus/Gap:{allocated_amount - survival_need:+.1f}Unit

Initial Allocation for Other Families:
{other_allocations_str}

Total Community Resources:{self.total_grain:.1f}Unit

Please evaluate this initial allocation based on your values:
1. Do you accept this quota?(Answer directly"Accept"or"Disagree")
2. If there is an objection,Briefly explain why(No more than50Words)
3. If there is an objection,How many units do you want to adjust to?(Give a specific number)

Please answer in the following format:
Attitude:[Accept/Disagree]
Reason:[Your reasons]
Expected Quantity:[Number](Fill in the current quantity if accepted)
"""
        
        model_name = get_model_name()
        temperature = 0.8
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation.Based on your values and family realities,Be authentic about what you think of the distribution plan."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=300
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # Parsing Responses
            has_objection = "Disagree" in content
            
            # Withdraw Expected Quantity
            expected_amount = allocated_amount  # Default value
            amount_match = re.search(r'Expected Quantity[::]\s*([\d.]+)', content)
            if amount_match:
                try:
                    expected_amount = float(amount_match.group(1))
                except:
                    pass
            
            # Withdraw Reason
            reason_match = re.search(r'Reason[::]\s*(.+?)(?=\n|Expected Quantity|$)', content, re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else "Unspecified"
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="details-opinion",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={
                        "has_objection": has_objection,
                        "expected_amount": expected_amount,
                        "allocated_amount": allocated_amount
                    }
                )
            
            return {
                "has_objection": has_objection,
                "objection_reason": reason if has_objection else "",
                "expected_amount": expected_amount,
                "allocated_amount": allocated_amount,
                "raw_response": content
            }
            
        except Exception as e:
            print(f"  Get{agent['family_name']}Home Opinion Failed: {str(e)}")
            return {
                "has_objection": False,
                "objection_reason": "",
                "expected_amount": allocated_amount,
                "allocated_amount": allocated_amount,
                "raw_response": "Failed to fetch"
            }
    
    def _negotiate_disputed_allocations(self, allocation: Dict[int, Dict[str, float]],
                                      opinions: Dict[int, Dict[str, Any]],
                                      framework: Dict[str, Any]) -> Dict[int, Dict[str, float]]:
        """Negotiate Disputed Allocations"""
        
        # Identify dissenters and their claims
        disputed_agents = [(aid, op) for aid, op in opinions.items() if op.get("has_objection")]
        
        if not disputed_agents:
            return allocation
        
        # Calculate Total Adjustment Requirements
        total_adjustment_need = sum(
            op["expected_amount"] - op["allocated_amount"] 
            for _, op in disputed_agents
        )
        
        print(f"    Total Adjustment Requirements:{total_adjustment_need:+.1f}Unit")
        
        # If the total demand is positive(Request Increase),Needs to be dispensed from another family
        if abs(total_adjustment_need) < 0.5:
            print("    Minor adjustments,Accept existing plan")
            return allocation
        
        # Conduct a round of adjustment negotiations
        adjusted_allocation = self._mediate_allocation_adjustment(
            allocation, disputed_agents, total_adjustment_need, framework
        )
        
        return adjusted_allocation
    
    def _mediate_allocation_adjustment(self, allocation: Dict[int, Dict[str, float]],
                                     disputed_agents: List[Tuple[int, Dict[str, Any]]],
                                     total_need: float,
                                     framework: Dict[str, Any]) -> Dict[int, Dict[str, float]]:
        """Mediation Allocation Adjustment"""
        
        adjusted = copy.deepcopy(allocation)
        
        # Limit Adjustment:Adjust up to10%Total Resources
        max_adjustment = self.total_grain * 0.1
        actual_adjustment = min(abs(total_need), max_adjustment)
        
        if total_need > 0:  # Someone asked for an increase
            # Recipe1:Stream part of the satisfaction
            satisfied_agents = [agent for agent in self.agents 
                              if agent["id"] not in [aid for aid, _ in disputed_agents]]
            
            if satisfied_agents:
                # Scale out from Satisfied
                donors = []
                for agent in satisfied_agents:
                    aid = agent["id"]
                    current = sum(adjusted[aid].values())
                    survival = sum(self.survival_needs.get(aid, {}).values())
                    surplus = current - survival
                    if surplus > 1.0:  # There is a margin to call out
                        donors.append((aid, surplus))
                
                if donors:
                    total_available = sum(s for _, s in donors)
                    actual_transfer = min(actual_adjustment, total_available * 0.3)  # Up to revolutions30%Margin of
                    
                    # FromdonorOutgoing
                    for aid, surplus in donors:
                        transfer_amount = (surplus / total_available) * actual_transfer
                        adjusted[aid]["grain"] -= transfer_amount
                    
                    # Assign to Dissenters
                    for aid, opinion in disputed_agents:
                        requested_increase = opinion["expected_amount"] - opinion["allocated_amount"]
                        if requested_increase > 0:
                            share = (requested_increase / total_need) * actual_transfer
                            adjusted[aid]["grain"] += share
                    
                    print(f"    Resolution:From{len(donors)}Remaining family (s) transferred out{actual_transfer:.1f}Unit")
                    
                    # Document mediation decisions
                    if self.logger:
                        self.logger.log_decision(
                            decision_type="allocation_mediation",
                            decision_content={
                                "transferred_amount": actual_transfer,
                                "donors": [aid for aid, _ in donors],
                                "recipients": [aid for aid, _ in disputed_agents]
                            },
                            supporters=[aid for aid, _ in donors],
                            opponents=[]
                        )
        
        return adjusted
    
    def _validate_and_optimize(self, allocation: Dict[int, Dict[str, float]]) -> Dict[int, Dict[str, float]]:
        """Validate and optimize allocation schemes"""
        
        # Total Validated
        total_allocated = sum(sum(agent_alloc.values()) for agent_alloc in allocation.values())
        
        if abs(total_allocated - self.total_grain) > 0.01:
            # Needs Adjustment
            adjustment_factor = self.total_grain / total_allocated
            # Record Normalization
            if self.logger:
                try:
                    self.logger.log_decision(
                        decision_type="normalization_applied",
                        decision_content={
                            "factor": adjustment_factor,
                            "before_total": total_allocated,
                            "after_total": self.total_grain
                        },
                        supporters=[agent["id"] for agent in self.agents],
                        opponents=[]
                    )
                except Exception:
                    pass
            for agent_id in allocation:
                for resource in allocation[agent_id]:
                    allocation[agent_id][resource] *= adjustment_factor
        
        return allocation

    def _integerize_allocation(self, allocation: Dict[int, Dict[str, float]], enforce_min_survival: bool = True) -> Dict[int, Dict[str, float]]:
        """Integerize Final Allocation(Maximum Remainder Method + Survival Guarantee)
        
        Step:
        1) Based on each householdflooras benchmark;
        2) If you enable Guarantee,then increase the benchmark per household toceil(Survival Needs);
        3) Calculate target total=Round to current total;
        4) If the benchmark and<Objectives,Decimal part from largest to smallest+1;If the benchmark and>Objectives,Decimal part from small to large-1,But not less than a guarantee.
        """
        # Process only grain this resource
        agent_ids = [agent["id"] for agent in self.agents]
        real_values: Dict[int, float] = {aid: float(allocation.get(aid, {}).get("grain", 0.0)) for aid in agent_ids}
        fractional: Dict[int, float] = {}
        base: Dict[int, int] = {}
        min_need: Dict[int, int] = {}
        
        for aid in agent_ids:
            val = real_values.get(aid, 0.0)
            base[aid] = math.floor(val)
            fractional[aid] = val - base[aid]
            if enforce_min_survival:
                need = sum(self.survival_needs.get(aid, {}).values())
                min_need[aid] = int(math.ceil(need)) if need > 0 else 0
            else:
                min_need[aid] = 0
        
        # Apply Guarantee
        for aid in agent_ids:
            if base[aid] < min_need[aid]:
                base[aid] = min_need[aid]
                fractional[aid] = 0.0
        
        current_sum = sum(real_values.values())
        target_total = int(round(current_sum))
        base_sum = sum(base.values())
        
        # If the benchmark and are less than the target,Increase by decimal part from largest to smallest1
        if base_sum < target_total:
            need = target_total - base_sum
            order = sorted(agent_ids, key=lambda a: fractional[a], reverse=True)
            i = 0
            while need > 0 and i < len(order):
                aid = order[i]
                base[aid] += 1
                need -= 1
                i += 1
        # If the benchmark and are greater than the target,Decrease by decimal part from small to large1(Not less than a guarantee)
        elif base_sum > target_total:
            excess = base_sum - target_total
            order = sorted(agent_ids, key=lambda a: fractional[a])
            i = 0
            while excess > 0 and i < len(order):
                aid = order[i]
                if base[aid] > min_need[aid]:
                    base[aid] -= 1
                    excess -= 1
                i += 1
        
        # Assemble newallocation
        new_alloc: Dict[int, Dict[str, float]] = {aid: {"grain": float(base.get(aid, 0))} for aid in agent_ids}
        
        # Logging
        if self.logger:
            try:
                diff = {aid: base[aid] - int(round(real_values.get(aid, 0.0))) for aid in agent_ids}
                self.logger.log_decision(
                    decision_type="integerization_applied",
                    decision_content={
                        "method": "largest_remainder_with_min",
                        "before_total": current_sum,
                        "after_total": sum(base.values()),
                        "changes": diff
                    },
                    supporters=[aid for aid in agent_ids],
                    opponents=[]
                )
            except Exception:
                pass
        
        return new_alloc
    
    def _finalize_proposal(self, detailed_proposal: Dict[int, Dict[str, float]]) -> Dict[int, Dict[str, float]]:
        """Phase4:Final confirmation and fine-tuning(ContainsLLMDrive Multi-Wheel Confirmation)"""
        self.current_stage = "finalization"
        
        # Start phase log
        if self.logger:
            try:
                self.logger.start_stage("finalization", [agent["id"] for agent in self.agents])
            except Exception:
                pass
        
        print("\n   [Page1Round confirmation]Seek final advice from families...")
        
        # First round of feedback
        first_feedback = self._collect_final_confirmation(detailed_proposal, round_num=1)
        
        # Document the first round of feedback
        self._log_feedback(first_feedback, "Page1Round confirmation")
        
        current_proposal = detailed_proposal
        
        # 🎯 If anyone is dissatisfied,Proceed to section2Round of fine-tuning negotiation
        unsatisfied = [aid for aid, fb in first_feedback.items() 
                      if fb.get("satisfaction_level", 3) < 3]
        
        if unsatisfied and len(unsatisfied) <= len(self.agents) // 2:  # A few people are dissatis
            print(f"\n   Discover{len(unsatisfied)}Unsatisfied with,Proceed to section2Round of fine-tuning negotiation...")
            
            # 🎯 Let the dissatisfied person propose a specific adjustment plan
            adjustment_proposals = self._collect_adjustment_proposals(
                current_proposal, first_feedback, unsatisfied
            )
            
            # 🎯 Get other families to vote on the adjustment
            if adjustment_proposals:
                print("\n   Other families vote on the fine-tuning plan...")
                adjusted_proposal = self._vote_on_adjustments(
                    current_proposal, adjustment_proposals
                )
                
                # Page2Round confirmation
                print("\n   [Page2Round confirmation]Ask for advice again...")
                second_feedback = self._collect_final_confirmation(adjusted_proposal, round_num=2)
                self._log_feedback(second_feedback, "Page2Round confirmation")
                
                current_proposal = adjusted_proposal
            else:
                print("   Failed to develop an effective adjustment plan,Keep your plan")
        elif len(unsatisfied) > len(self.agents) // 2:  # Most people are dissatisf
            print(f"\n   ⚠️ Most Families({len(unsatisfied)}Home)Dissatisfied,But the negotiation round limit has been reached")
            print("   Maintain current protocol and document disagreements")
            if self.logger:
                self.logger.log_conflict(
                    conflict_topic="The final proposal is highly divergent",
                    conflicting_parties=unsatisfied,
                    conflict_description=f"Most families are dissatisfied,But the negotiation did not reach a better solution"
                )
        else:
            print("   ✓ Families are basically satisfied,No fine-tuning required")
        
        # Integerization(Maximum Remainder Method + Survival Guarantee)
        try:
            integerized = self._integerize_allocation(current_proposal, enforce_min_survival=True)
            current_proposal = integerized
        except Exception:
            pass
        
        print("\n   ✓ Allocation plan finalized!")
        print("\n   Final Allocation Result:")
        for agent in self.agents:
            aid = agent["id"]
            amount = sum(current_proposal.get(aid, {}).values())
            print(f"    {agent['family_name']}Home:{amount:.0f}Unit")
        
        # End Phase Log
        try:
            # Calculate consensus using the last round of feedback
            final_feedback = first_feedback if not unsatisfied or len(unsatisfied) > len(self.agents) // 2 else second_feedback
            levels = [fb.get("satisfaction_level", 0.0) for fb in final_feedback.values()]
            avg_level = sum(levels) / len(levels) if levels else 0.0
            self.final_average_satisfaction = avg_level
            ok_ratio = sum(1 for l in levels if l >= 3.0) / len(levels) if levels else 0.0
            if self.logger:
                self.logger.end_stage(
                    stage_outcome="Final confirmation complete",
                    consensus_level=ok_ratio
                )
        except Exception:
            pass
        
        return current_proposal
    
    def _collect_final_confirmation(self, proposal: Dict[int, Dict[str, float]], 
                                   round_num: int = 1) -> Dict[int, Dict[str, Any]]:
        """Collect final confirmation feedback(LLMDrive)"""
        feedback = {}
        
        for agent in self.agents:
            agent_id = agent["id"]
            agent_allocation = proposal.get(agent_id, {})
            total_allocation = sum(agent_allocation.values())
            survival_need = sum(self.survival_needs.get(agent_id, {}).values())
            
            # UseLLMGet final confirmation
            confirmation = self._get_final_confirmation_llm(
                agent, total_allocation, survival_need, proposal, round_num
            )
            
            feedback[agent_id] = confirmation
        
        return feedback
    
    def _get_final_confirmation_llm(self, agent: Dict[str, Any], allocated_amount: float,
                                   survival_need: float, all_allocations: Dict[int, Dict[str, float]],
                                   round_num: int) -> Dict[str, Any]:
        """UseLLMGet final confirmation"""
        
        # Construct additional household allocations
        other_info = ""
        for other_agent in self.agents:
            if other_agent["id"] != agent["id"]:
                other_amount = sum(all_allocations.get(other_agent["id"], {}).values())
                other_info += f"- {other_agent['family_name']}Home:{other_amount:.0f}Unit\n"
        
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

After several rounds of negotiation,Final Allocation Protocol now needs to be accounted for in{round_num}Round confirmation.

Final allocation of your home:
- Get the resources:{allocated_amount:.0f}Unit grain
- Survival Needs:{survival_need:.0f}Unit
- Surplus/Gap:{allocated_amount - survival_need:+.0f}Unit

Allocation to other families:
{other_info}

Please rate this final program based on your values:
1. Your Satisfaction(1-5Minutes,1=Very dissatisfied,3=Acceptable,5=Very satisfied)
2. If Satisfaction is Below3Minutes,Please describe your main concern(No more than30Words)
3. If there is a concern,How would you like to adjust?(Brief description)

Please answer in the following format:
Satisfaction:[1-5Number]
Concerns:[Your concerns or"None"]
Adjustment Suggest:[Your Suggestion or"None"]
"""
        
        model_name = get_model_name()
        temperature = 0.8
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation.This is the final confirmation phase,Please be honest about your thoughts on the final plan."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=250
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # Resolution Satisfaction
            satisfaction_level = 3.0  # Default value
            satisfaction_match = re.search(r'Satisfaction[::]\s*([1-5])', content)
            if satisfaction_match:
                try:
                    satisfaction_level = float(satisfaction_match.group(1))
                except:
                    pass
            
            # Extract Concerns
            concern_match = re.search(r'Concerns[::]\s*(.+?)(?=\n|Adjustment Suggest|$)', content, re.DOTALL)
            concern = concern_match.group(1).strip() if concern_match else ""
            has_concern = concern and concern != "None" and satisfaction_level < 3
            
            # Extract Adjustment Suggestions
            adjustment_match = re.search(r'Adjustment Suggest[::]\s*(.+?)$', content, re.DOTALL)
            adjustment_suggestion = adjustment_match.group(1).strip() if adjustment_match else ""
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage=f"finalization-round{round_num}",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={
                        "satisfaction_level": satisfaction_level,
                        "has_concern": has_concern,
                        "concern": concern
                    }
                )
            
            return {
                "satisfaction_level": satisfaction_level,
                "has_concerns": has_concern,
                "concern": concern if has_concern else "",
                "adjustment_suggestion": adjustment_suggestion if has_concern else "",
                "raw_response": content
            }
            
        except Exception as e:
            print(f"  Get{agent['family_name']}Home confirmation failed: {str(e)}")
            # Use rule-basedfallback
            satisfaction = 3.0
            if allocated_amount >= survival_need * 1.1:
                satisfaction = 4.0
            elif allocated_amount < survival_need:
                satisfaction = 2.0
            
            return {
                "satisfaction_level": satisfaction,
                "has_concerns": satisfaction < 3,
                "concern": "Underallocated" if satisfaction < 3 else "",
                "adjustment_suggestion": "",
                "raw_response": "Failed to fetch"
            }
    
    def _log_feedback(self, feedback: Dict[int, Dict[str, Any]], stage_name: str):
        """Log feedback to the log"""
        if not self.logger:
            return
        
        for agent in self.agents:
            aid = agent["id"]
            fb = feedback.get(aid, {})
            self.logger.log_discussion_turn(
                speaker_id=aid,
                speaker_name=agent["family_name"],
                speaker_value_type=agent["value_type"],
                content=f"Satisfaction:{fb.get('satisfaction_level', 0)}, {fb.get('concern', 'No worries')}",
                speech_type="final_confirmation",
                target_topic=stage_name
            )
    
    def _collect_adjustment_proposals(self, current_allocation: Dict[int, Dict[str, float]],
                                    feedback: Dict[int, Dict[str, Any]],
                                    unsatisfied_agents: List[int]) -> List[Dict[str, Any]]:
        """Collect adjustment proposals from dissatisfied families(LLMDrive)"""
        
        proposals = []
        
        for agent_id in unsatisfied_agents:
            agent = next((a for a in self.agents if a["id"] == agent_id), None)
            if not agent:
                continue
            
            fb = feedback.get(agent_id, {})
            current_amount = sum(current_allocation.get(agent_id, {}).values())
            
            # Simplified processing:Draw adjustment suggestions directly from the feedback
            adjustment_text = fb.get("adjustment_suggestion", "")
            
            if adjustment_text and adjustment_text != "None":
                # Try to extract the desired adjustment from the suggestion
                # Example:"Hope to increase5Unit" or "Adjust to30Unit"
                amount_match = re.search(r'(\d+)', adjustment_text)
                if amount_match:
                    requested_change = float(amount_match.group(1))
                    
                    # Determine whether it is incremental or target value
                    if "Increase" in adjustment_text or "Multiple" in adjustment_text:
                        target_amount = current_amount + requested_change
                    else:
                        target_amount = requested_change
                    
                    # Limit Adjustment(Max.±20%)
                    max_change = current_amount * 0.2
                    target_amount = max(current_amount - max_change, 
                                      min(target_amount, current_amount + max_change))
                    
                    proposals.append({
                        "agent_id": agent_id,
                        "agent_name": agent["family_name"],
                        "current_amount": current_amount,
                        "target_amount": target_amount,
                        "reason": fb.get("concern", ""),
                        "adjustment_text": adjustment_text
                    })
                    
                    print(f"    {agent['family_name']}Home Proposal:{current_amount:.0f} → {target_amount:.0f}Unit")
        
        return proposals
    
    def _vote_on_adjustments(self, current_allocation: Dict[int, Dict[str, float]],
                           proposals: List[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
        """Let other families vote on the adjustment proposal(Simplified processing)"""
        
        if not proposals:
            return current_allocation
        
        adjusted = copy.deepcopy(current_allocation)
        
        # Simplified voting:If the total need for the proposal is reasonable,is met on a pro rata basis
        total_increase_needed = sum(
            max(0, p["target_amount"] - p["current_amount"]) 
            for p in proposals
        )
        
        # Identify families who can contribute(Above average)
        avg_allocation = self.total_grain / len(self.agents)
        potential_donors = [
            (agent["id"], sum(adjusted[agent["id"]].values()) - avg_allocation)
            for agent in self.agents
            if agent["id"] not in [p["agent_id"] for p in proposals]
            and sum(adjusted[agent["id"]].values()) > avg_allocation * 1.1
        ]
        
        if not potential_donors:
            print("    No unallocable resources,Keep your plan")
            return current_allocation
        
        total_available = sum(surplus for _, surplus in potential_donors)
        actual_transfer = min(total_increase_needed, total_available * 0.5)  # Up to revolutions50%Margin of
        
        if actual_transfer > 0.5:
            # FromdonorOutgoing
            for donor_id, surplus in potential_donors:
                transfer_out = (surplus / total_available) * actual_transfer
                adjusted[donor_id]["grain"] -= transfer_out
            
            # Assign to sponsor
            for proposal in proposals:
                increase_needed = max(0, proposal["target_amount"] - proposal["current_amount"])
                if increase_needed > 0:
                    share = (increase_needed / total_increase_needed) * actual_transfer
                    adjusted[proposal["agent_id"]]["grain"] += share
            
            print(f"    ✓ Adjustment Passed:Transfer{actual_transfer:.1f}Unit Resource")
            
            # Record Decision
            if self.logger:
                self.logger.log_decision(
                    decision_type="adjustment_voted_approved",
                    decision_content={
                        "transferred_amount": actual_transfer,
                        "proposals": proposals,
                        "donors": [did for did, _ in potential_donors]
                    },
                    supporters=[did for did, _ in potential_donors],
                    opponents=[]
                )
        else:
            print("    Adjustment too small,Keep your plan")
        
        return adjusted
    
    def _create_fallback_proposal(self) -> Dict[int, Dict[str, float]]:
        """Create Fallback Assignment Scenario(Simple Equal Distribution)"""
        per_family = self.total_grain / len(self.agents)
        
        return {
            agent["id"]: {"grain": per_family}
            for agent in self.agents
        }
    
    def _create_negotiation_data(self, success: bool, method: str) -> Dict[str, Any]:
        """Create Negotiation Process Data"""
        return {
            "success": success,
            "method": method,
            "stages_completed": list(self.stage_results.keys()),
            "conversation_rounds": len(self.conversation_history),
            "consensus_items": len(self.consensus_items),
            "final_stage": self.current_stage,
            "stage_results": self.stage_results
        }
    
    # =====================================================================
    # 🆕 Phase 1: LLMDrive Negotiation Enhancement Approach
    # =====================================================================
    
    def _get_agent_by_id(self, agent_id: int) -> Dict[str, Any]:
        """🆕 Auxiliary Methods:PassIDGetagent"""
        return next((a for a in self.agents if a["id"] == agent_id), None)
    
    def _format_principles(self, principles: Dict[str, str]) -> str:
        """🆕 Auxiliary Methods:Formatting principles as strings"""
        return "\n".join([f"- {name}:{desc}" for name, desc in principles.items()])
    
    def _normalize_proposals(self, proposals: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """🆕 Forced Normalization Proposal(Guarantee Mechanism)"""
        total = sum(p.get('current_ratio', p.get('ideal_ratio', 0)) for p in proposals.values())
        
        if total > 0:
            factor = 1.0 / total
            for agent_id in proposals:
                if 'current_ratio' in proposals[agent_id]:
                    proposals[agent_id]['current_ratio'] *= factor
                if 'ideal_ratio' in proposals[agent_id]:
                    proposals[agent_id]['ideal_ratio'] *= factor
                if 'suggested_ratio' in proposals[agent_id]:
                    proposals[agent_id]['suggested_ratio'] *= factor
        
        return proposals
    
    def _collect_ratio_proposals(self, principles: Dict[str, str]) -> Dict[int, Dict[str, Any]]:
        """🆕 Gather initial proportional proposals for each family"""
        proposals = {}
        
        print("   Gather resource ratio suggestions for each household...")
        
        for agent in self.agents:
            agent_id = agent["id"]
            
            # Build Tips - Clear household assignments
            prompt = f"""You are{agent['family_name']}Family Representative,Values:{get_value_type_name(agent['value_type'])}.

[Family situation]
- Household Population:{agent['members']}People
- Workforce:{agent['labor_force']}People

[Community Resource Assignment Tasks]
Community Existing{self.total_grain}Unit resources need to be in{len(self.agents)}Allocation between families.
- Total population:{self.total_members}People
- Total Workforce:{self.total_labor}People

[Community-Determined Distribution Principles]
{self._format_principles(principles)}

[Task]
Integrating community principles and your values,Submit:In this assignment,How much your family deserves?

Please follow theJSONFormat Answer:
{{
    "ideal_ratio": 0.XX,  // Proportion of your home that should be(0To1Between,As0.10Indicates that your home receives10%)
    "minimum_acceptable": 0.YY,  // The lowest percentage you can accept
    "reasoning": "Why your family deserves this share"
}}

Description:hereratioRefers to where your home is located{len(self.agents)}What share of households should be allocated.
Please make sure the answer is validJSONFormat."""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are a family representative involved in resource negotiation.Please be rational,Propose allocations constructively."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content
                
                # InsightsJSON(Enhanced Robustness)
                import json
                import re
                
                # Clean up response text:RemovemarkdownCode block tags and control characters
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                
                # 🔥 EnhanceJSONInsights:Handling control characters and formatting issues
                proposal_data = None
                
                # Method1:Extract numeric fields manually(Most Reliable)
                try:
                    # Extractideal_ratio(Supports integers and decimals)
                    ideal_match = re.search(r'"ideal_ratio":\s*(\d+\.?\d*)', cleaned_text)
                    if ideal_match:
                        ideal_ratio = float(ideal_match.group(1))
                        
                        # Extractminimum_acceptable
                        min_match = re.search(r'"minimum_acceptable":\s*(\d+\.?\d*)', cleaned_text)
                        min_acceptable = float(min_match.group(1)) if min_match else ideal_ratio * 0.7
                        
                        # Extractreasoning(Handling Multiline and Special Characters)
                        reasoning_match = re.search(r'"reasoning":\s*"(.*?)"(?=\s*[,}])', cleaned_text, re.DOTALL)
                        if reasoning_match:
                            reasoning = reasoning_match.group(1)
                            # Clear Control Characters
                            reasoning = reasoning.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                            reasoning = re.sub(r'\s+', ' ', reasoning).strip()
                        else:
                            reasoning = "No reason provided"
                        
                        proposal_data = {
                            "ideal_ratio": ideal_ratio,
                            "minimum_acceptable": min_acceptable,
                            "reasoning": reasoning
                        }
                except Exception as e1:
                    # Method2:Attempt CriteriaJSONInsights(After cleaning)
                    try:
                        # Remove all control characters
                        safe_text = re.sub(r'[\x00-\x1f\x7f]', ' ', cleaned_text)
                        proposal_data = json.loads(safe_text)
                    except Exception as e2:
                        # Method3:Try extracting and parsingJSONSnippet
                        try:
                            json_match = re.search(r'\{[^{}]+\}', cleaned_text)
                            if json_match:
                                safe_fragment = re.sub(r'[\x00-\x1f\x7f]', ' ', json_match.group(0))
                                proposal_data = json.loads(safe_fragment)
                        except:
                            pass
                
                # If all methods fail,Throw Exception Trigger Default
                if not proposal_data:
                    raise ValueError(f"Unable to parseJSONResponse: {cleaned_text[:100]}")
                
                proposals[agent_id] = {
                    "agent": agent["family_name"],
                    "ideal_ratio": proposal_data.get("ideal_ratio", 1.0/len(self.agents)),
                    "minimum_acceptable": proposal_data.get("minimum_acceptable", proposal_data.get("ideal_ratio", 1.0/len(self.agents)) * 0.7),
                    "reasoning": proposal_data.get("reasoning", "Not provided"),
                    "raw_response": response_text
                }
                
                print(f"      {agent['family_name']}Home:{proposals[agent_id]['ideal_ratio']:.1%}(Reason:{proposals[agent_id]['reasoning'][:50]}...)")
                
                # Logging
                if self.logger:
                    try:
                        self.logger.log_negotiation_call(
                            agent_id=agent_id,
                            stage="ratio_proposal",
                            prompt_content=prompt[:200] + "...",
                            response_content=response_text,
                            target_topic="Initial Scale Proposal"
                        )
                    except Exception:
                        pass
                
            except Exception as e:
                print(f"      ⚠️ {agent['family_name']}Proposal fetching failed: {e}")
                # Default Proposal
                proposals[agent_id] = {
                    "agent": agent["family_name"],
                    "ideal_ratio": 1.0 / len(self.agents),
                    "minimum_acceptable": 0.7 / len(self.agents),
                    "reasoning": "System default(Equal distribution)",
                    "raw_response": ""
                }
        
        return proposals
    
    def _aggregate_ratio_proposals(self, proposals: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """🆕 Summary Scale Proposal"""
        total_suggested = sum(p.get("ideal_ratio", 0) for p in proposals.values())
        avg_ratio = total_suggested / len(proposals) if proposals else 0
        
        # Analyze Leading Factors
        high_labor_families = [aid for aid, p in proposals.items() 
                              if self._get_agent_by_id(aid)['labor_force'] > self.total_labor / len(self.agents)]
        high_labor_avg = sum(proposals[aid]['ideal_ratio'] for aid in high_labor_families) / len(high_labor_families) if high_labor_families else avg_ratio
        
        # Jurisdiction Leading Principle
        if high_labor_avg > avg_ratio * 1.2:
            dominant_principle = "C"  # Contribution
        elif abs(high_labor_avg - avg_ratio) < 0.05:
            dominant_principle = "E"  # Equality
        else:
            dominant_principle = "N"  # Needs
        
        aggregated = {
            "total_suggested_ratio": total_suggested,
            "average_ratio": avg_ratio,
            "dominant_principle": dominant_principle,
            "num_proposals": len(proposals)
        }
        
        print(f"      Ratio Summary:Total Suggestions{total_suggested:.1%},Average{avg_ratio:.1%},Dominant Factors:{dominant_principle}")
        
        return aggregated
    
    def _identify_ratio_disputes_enhanced(self, proposals: Dict[int, Dict[str, Any]], aggregated: Dict[str, Any]) -> List[Dict[str, Any]]:
        """🆕 Enhanced Dispute Identification(Lower Threshold)"""
        disputes = []
        
        # 🔥 Check1:Total Proportional Deviation(From10%Descending to5%)
        total_ratio = aggregated["total_suggested_ratio"]
        if abs(total_ratio - 1.0) > 0.05:  # ⬅️ More sensitive
            severity = "high" if abs(total_ratio - 1.0) > 0.1 else "medium"
            
            # 🆕 Identify Top Contributors Exceeding Targets(Most Demanding Top30%Family)
            sorted_proposals = sorted(proposals.items(), 
                                    key=lambda x: x[1].get("ideal_ratio", 0), 
                                    reverse=True)
            num_high_demanders = max(1, int(len(sorted_proposals) * 0.3))
            high_demanders = [aid for aid, _ in sorted_proposals[:num_high_demanders]]
            
            disputes.append({
                "type": "total_mismatch",
                "severity": severity,
                "description": f"Total Ratio{total_ratio:.1%},Deviation{abs(total_ratio-1.0):.1%}",
                "affected_all": True,
                "parties": high_demanders  # ⬅️ Critical:Assign Dispute Parties
            })
        
        # 🔥 Check2:Individual Extreme Suggestions(From2xDescending to1.5x)
        ratios = [p.get("ideal_ratio", p.get("suggested_ratio", 0)) for p in proposals.values() if p.get("ideal_ratio") or p.get("suggested_ratio")]
        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            
            for agent_id, proposal in proposals.items():
                ratio = proposal.get("ideal_ratio", proposal.get("suggested_ratio"))
                if ratio:
                    agent = self._get_agent_by_id(agent_id)
                    
                    # Above average1.5times
                    if ratio > avg_ratio * 1.5:  # ⬅️ More sensitive
                        disputes.append({
                            "type": "high_demand",
                            "severity": "medium",
                            "agent_id": agent_id,
                            "agent_name": agent["family_name"] if agent else "Unknown",
                            "requested": ratio,
                            "average": avg_ratio,
                            "description": f"{agent['family_name'] if agent else 'Unknown'}Request{ratio:.1%},Above average{avg_ratio:.1%}"
                        })
                    
                    # Below average0.7times
                    elif ratio < avg_ratio * 0.7:  # ⬅️ More sensitive
                        disputes.append({
                            "type": "low_demand",
                            "severity": "low",
                            "agent_id": agent_id,
                            "agent_name": agent["family_name"] if agent else "Unknown",
                            "requested": ratio,
                            "average": avg_ratio,
                            "description": f"{agent['family_name'] if agent else 'Unknown'}Request{ratio:.1%},Below average"
                        })
        
        return disputes
    
    def _collect_opening_statements(self, disputes: List[Dict[str, Any]], proposals: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """🆕 Collect the Disputing Party's Position Statement"""
        statements = {}
        
        # Identifying Dispute-Related Families
        disputed_agents = set()
        for dispute in disputes:
            if "agent_id" in dispute:
                disputed_agents.add(dispute["agent_id"])
            elif "parties" in dispute:
                disputed_agents.update(dispute["parties"])
        
        for agent_id in disputed_agents:
            agent = self._get_agent_by_id(agent_id)
            if not agent:
                continue
                
            proposal = proposals.get(agent_id, {})
            ratio = proposal.get('ideal_ratio', proposal.get('suggested_ratio', 0))
            
            # Find the description of the dispute against this family
            relevant_disputes = [
                d["description"] for d in disputes 
                if d.get("agent_id") == agent_id or agent_id in d.get("parties", [])
            ]
            
            prompt = f"""You are{agent['family_name']}Family Representative,Values:{get_value_type_name(agent['value_type'])}.

The proportion of resources you propose to allocate:{ratio:.1%}
Community average:{1.0/len(self.agents):.1%}

Now someone questions your proposal:
{chr(10).join('- ' + d for d in relevant_disputes)}

Please state your position(100Within Words):
1. Why do you think this ratio is reasonable??
2. What are your core needs(The uncompromising part)?
3. Would you like to discuss adjustments??

Keep it simple,Answer honestly."""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are a family representative involved in resource negotiation,Need to secure reasonable resources for your family."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8  # High Temperature,Add personalization
                )
                
                statement = response.choices[0].message.content
                statements[agent_id] = {
                    "agent": agent["family_name"],
                    "statement": statement,
                    "original_ratio": ratio
                }
                
                # Log to Log
                if self.logger:
                    try:
                        self.logger.log_negotiation_call(
                            agent_id=agent_id,
                            stage="negotiation_statement",
                            prompt_content=prompt[:200] + "...",
                            response_content=statement,
                            target_topic="Position Statement"
                        )
                    except Exception:
                        pass
            
            except Exception as e:
                print(f"      ⚠️ {agent['family_name']}Statement failed: {e}")
        
        return statements
    
    def _collect_peer_responses(self, disputes: List[Dict[str, Any]], proposals: Dict[int, Dict[str, Any]], statements: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """🆕 Gather responses from other families"""
        responses = {}
        
        # Identify the parties involved in the dispute
        disputed_ids = set()
        for dispute in disputes:
            if "agent_id" in dispute:
                disputed_ids.add(dispute["agent_id"])
            elif "parties" in dispute:
                disputed_ids.update(dispute["parties"])
        
        # Have a non-disputing party respond
        observers = [a for a in self.agents if a["id"] not in disputed_ids]
        
        # Build Dispute Summary
        if statements:
            statements_text = "\n\n".join([
                f"[{s['agent']}Home]Request{s['original_ratio']:.1%}\n{s['statement']}"
                for s in statements.values()
            ])
        else:
            statements_text = "\n".join([d["description"] for d in disputes])
        
        for observer in observers:
            prompt = f"""You are{observer['family_name']}Family Representative,Values:{get_value_type_name(observer['value_type'])}.
You brought it up yourself.{proposals[observer['id']].get('ideal_ratio', proposals[observer['id']].get('suggested_ratio', 0)):.1%}Resource share.

Now the community is discussing the following disputes:
{statements_text}

As a bystander,Tell us what you think(150Within Words):
1. Which family do you think is more reasonable??Why?
2. To resolve the dispute,Are you willing to adjust your share??
3. What is your suggested solution??

Please be objective,Answer constructively."""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are a Negotiating Mediator,Need to help the community reach a consensus."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8
                )
                
                response_text = response.choices[0].message.content
                
                # Try to extract"Willing to adjust"Signal
                willingness = "Medium"
                if any(word in response_text for word in ["Willing", "Can be adjusted", "Cede", "Decrease"]):
                    willingness = "High"
                elif any(word in response_text for word in ["Unwilling", "Insist", "Unable to", "No"]):
                    willingness = "Low"
                
                responses[observer['id']] = {
                    "agent": observer["family_name"],
                    "response": response_text,
                    "willingness_to_adjust": willingness
                }
                
                # Logging
                if self.logger:
                    try:
                        self.logger.log_negotiation_call(
                            agent_id=observer['id'],
                            stage="negotiation_response",
                            prompt_content=prompt[:200] + "...",
                            response_content=response_text,
                            target_topic="Peer Response"
                        )
                    except Exception:
                        pass
            
            except Exception as e:
                print(f"      ⚠️ {observer['family_name']}Response failed: {e}")
        
        return responses
    
    def _collect_compromises(self, disputes: List[Dict[str, Any]], proposals: Dict[int, Dict[str, Any]], responses: Dict[int, Dict[str, Any]], principles: Dict[str, str]) -> Dict[int, Dict[str, Any]]:
        """🆕 Collect compromises"""
        compromises = {}
        
        # Identify the parties to the dispute
        disputed_ids = set()
        for dispute in disputes:
            if "agent_id" in dispute:
                disputed_ids.add(dispute["agent_id"])
            elif "parties" in dispute:
                disputed_ids.update(dispute["parties"])
        
        # Aggregate feedback from others
        feedback_summary = "\n\n".join([
            f"[{r['agent']}Home]{r['response'][:100]}..."
            for r in responses.values()
        ])
        
        if not feedback_summary:
            feedback_summary = "(No feedback yet)"
        
        for agent_id in disputed_ids:
            agent = self._get_agent_by_id(agent_id)
            if not agent:
                continue
                
            proposal = proposals[agent_id]
            current_ratio = proposal.get('current_ratio', proposal.get('ideal_ratio', proposal.get('suggested_ratio', 0)))
            min_acceptable = proposal.get('minimum_acceptable', current_ratio * 0.7)
            
            prompt = f"""You are{agent['family_name']}Family Representative.

Your current request:{current_ratio:.1%}
Your Bottom Line:{min_acceptable:.1%}

Feedback from other families:
{feedback_summary}

Based on feedback,Are you willing to adjust??

Please answer in the format:
Adjusted Scale:[Number]%(or"Sustain{current_ratio:.1%}")
Reason for adjustment:[Why Adjust/Why persevere]
Whether to make a final concession:Yes/No

Please make sure to answer in the format."""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You need to strike a balance between insisting on your own interests and community harmony."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content
                
                # Resolve Compromise
                ratio_match = re.search(r'Adjusted Scale[::]\s*(\d+(?:\.\d+)?)%', response_text)
                if ratio_match:
                    new_ratio = float(ratio_match.group(1)) / 100
                elif "Sustain" in response_text:
                    new_ratio = current_ratio
                else:
                    new_ratio = current_ratio
                
                reason_match = re.search(r'Reason for adjustment[::]\s*(.+?)(?=\nWhether to make a final concession|$)', response_text, re.DOTALL)
                reason = reason_match.group(1).strip() if reason_match else "Unspecified"
                
                is_final = "Yes" in response_text and "Final concession" in response_text
                
                compromises[agent_id] = {
                    "agent": agent["family_name"],
                    "old_ratio": current_ratio,
                    "new_ratio": new_ratio,
                    "reason": reason,
                    "is_final_offer": is_final,
                    "raw_response": response_text
                }
                
                # Logging
                if self.logger:
                    try:
                        self.logger.log_negotiation_call(
                            agent_id=agent_id,
                            stage="negotiation_compromise",
                            prompt_content=prompt[:200] + "...",
                            response_content=response_text,
                            target_topic="Compromise"
                        )
                    except Exception:
                        pass
            
            except Exception as e:
                print(f"      ⚠️ {agent['family_name']}Failed to get compromise: {e}")
                compromises[agent_id] = {
                    "agent": agent["family_name"],
                    "old_ratio": current_ratio,
                    "new_ratio": current_ratio,
                    "reason": "System default",
                    "is_final_offer": False,
                    "raw_response": ""
                }
        
        return compromises
    
    def _apply_compromises(self, proposals: Dict[int, Dict[str, Any]], compromises: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """🆕 Apply Compromise Update Proposal"""
        updated = copy.deepcopy(proposals)
        
        for agent_id, compromise in compromises.items():
            if agent_id in updated:
                old = updated[agent_id].get('current_ratio', updated[agent_id].get('ideal_ratio', 0))
                new = compromise['new_ratio']
                
                updated[agent_id]['current_ratio'] = new
                if 'suggested_ratio' in updated[agent_id]:
                    updated[agent_id]['suggested_ratio'] = new
                updated[agent_id]['rounds_adjusted'] = updated[agent_id].get('rounds_adjusted', 0) + 1
                
                if abs(new - old) > 0.001:
                    print(f"      {compromise['agent']}:{old:.1%} → {new:.1%} ({compromise['reason'][:30]}...)")
        
        return updated
    
    def _check_consensus(self, proposals: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """🆕 Check for consensus"""
        ratios = [p.get('current_ratio', p.get('ideal_ratio', 0)) for p in proposals.values()]
        total_ratio = sum(ratios)
        
        # Standard1:The total ratio is close to1.0(±3%)
        total_ok = abs(total_ratio - 1.0) < 0.03
        
        # Standard2:All households above the minimum acceptance line
        all_acceptable = all(
            p.get('current_ratio', p.get('ideal_ratio', 0)) >= p.get('minimum_acceptable', 0) * 0.95
            for p in proposals.values()
        )
        
        # Standard3:No extreme inequality
        if ratios and min(ratios) > 0:
            max_ratio = max(ratios)
            min_ratio = min(ratios)
            spread_ok = (max_ratio / min_ratio) < 3.0
        else:
            spread_ok = False
        
        achieved = total_ok and all_acceptable and spread_ok
        
        remaining_disputes = []
        if not total_ok:
            remaining_disputes.append({"type": "total_mismatch", "description": f"Total Ratio{total_ratio:.1%}"})
        if not all_acceptable:
            remaining_disputes.append({"type": "below_minimum", "description": "Families Below Bottom Line"})
        if not spread_ok:
            remaining_disputes.append({"type": "extreme_inequality", "description": "Gap too large"})
        
        return {
            "achieved": achieved,
            "remaining_disputes": remaining_disputes,
            "total_ratio": total_ratio,
            "criteria": {"total_ok": total_ok, "all_acceptable": all_acceptable, "spread_ok": spread_ok}
        }
    
    def _conduct_multi_round_negotiation(self, proposals: Dict[int, Dict[str, Any]], disputes: List[Dict[str, Any]], principles: Dict[str, str]) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
        """🆕 Perform multiple roundsLLMDrive Negotiation"""
        print("\n   🔥 Launch Multi-Round Negotiation Process...")
        
        # Initialization
        current_proposals = copy.deepcopy(proposals)
        for agent_id in current_proposals:
            if 'current_ratio' not in current_proposals[agent_id]:
                current_proposals[agent_id]['current_ratio'] = current_proposals[agent_id].get('ideal_ratio', current_proposals[agent_id].get('suggested_ratio', 0))
            if 'rounds_adjusted' not in current_proposals[agent_id]:
                current_proposals[agent_id]['rounds_adjusted'] = 0
        
        max_rounds = 3
        negotiation_log = []
        statements = None
        consensus = {"achieved": False}
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n   [Page{round_num}Round Negotiation]")
            
            # Sub-Phase1:Disputing Party Presents Position(Only pg.1Round)
            if round_num == 1:
                statements = self._collect_opening_statements(disputes, current_proposals)
                negotiation_log.append({"round": round_num, "phase": "statements", "data": statements})
                print(f"      Collected{len(statements)}position statements")
            
            # Sub-Phase2:Other family responses
            responses = self._collect_peer_responses(disputes, current_proposals, statements)
            negotiation_log.append({"round": round_num, "phase": "responses", "data": responses})
            print(f"      Collected{len(responses)}responses")
            
            # Sub-Phase3:Disputing Party Offers Compromise
            compromises = self._collect_compromises(disputes, current_proposals, responses, principles)
            negotiation_log.append({"round": round_num, "phase": "compromises", "data": compromises})
            print(f"      Collected{len(compromises)}compromises")
            
            # Sub-Phase4:Update Proposal
            current_proposals = self._apply_compromises(current_proposals, compromises)
            
            # Sub-Phase5:Check Consensus
            consensus = self._check_consensus(current_proposals)
            
            if consensus["achieved"]:
                print(f"      ✅ Gaining Consensus!")
                break
            else:
                print(f"      ⚠️ There are still{len(consensus['remaining_disputes'])}disputes,Continue Negotiation...")
                disputes = consensus['remaining_disputes']
        
        # If consensus is still not reached,Force Normalization
        if not consensus["achieved"]:
            print("\n   ⚠️ Negotiations not fully converged,Apply normalization...")
            current_proposals = self._normalize_proposals(current_proposals)
            consensus = self._check_consensus(current_proposals)
        
        return current_proposals, negotiation_log
    
    def _allocate_by_negotiated_ratios(self, negotiated_ratios: Dict[int, float]) -> Dict[int, Dict[str, float]]:
        """🆕 Direct use of negotiated proportional allocation of resources"""
        allocation = {}
        
        # Normalization(Ensure summation=1.0)
        total_ratio = sum(negotiated_ratios.values())
        factor = 1.0 / total_ratio if total_ratio > 0 else 1.0
        
        for agent in self.agents:
            aid = agent["id"]
            ratio = negotiated_ratios.get(aid, 1.0 / len(self.agents))
            normalized_ratio = ratio * factor
            allocated_grain = self.total_grain * normalized_ratio
            
            allocation[aid] = {"grain": allocated_grain}
            
            print(f"    {agent['family_name']}Home:{allocated_grain:.1f}Unit ({normalized_ratio:.1%})")
        
        # Record Assignment Decision
        if self.logger:
            try:
                self.logger.log_decision(
                    decision_type="llm_negotiated_allocation",
                    decision_content={
                        "method": "direct_ratio_allocation",
                        "ratios": {aid: negotiated_ratios[aid] for aid in negotiated_ratios},
                        "total_allocated": sum(a["grain"] for a in allocation.values())
                    },
                    supporters=[agent["id"] for agent in self.agents],
                    opponents=[]
                )
            except Exception:
                pass
        
        return allocation

    
    # ========================================
    # 🆕 New Stage1:Values Exchange and Fair Understanding Exploration
    # ========================================
    
    def _value_dialogue_phase(self) -> Dict[str, Any]:
        """Phase1:Values Exchange and Fair Understanding Exploration"""
        self.current_stage = "value_dialogue"
        
        print("\n═══════════════════════════════════════")
        print("   Phase1:Values Exchange and Fair Understanding Exploration")
        print("═══════════════════════════════════════")
        
        # Start phase log
        if self.logger:
            try:
                self.logger.start_stage("value_dialogue", [agent["id"] for agent in self.agents])
            except Exception:
                pass
        
        # Step1:Gather initial fair understanding
        print("\n   📝 Gather each family's initial understanding of fairness...")
        initial_understanding = {}
        
        for agent in self.agents:
            understanding = self._collect_initial_fairness_view(agent)
            initial_understanding[agent["id"]] = understanding
            print(f"    {agent['family_name']}Home({agent['value_type']}):{understanding['summary']}")
        
        # Step2:Multiple rounds of dialogue and exchanges
        dialogue_records = []
        value_absorption_tracker = {
            agent["id"]: {
                "absorbed_elements": [],
                "dialogue_partners": [],
                "dialogue_partner_values": []  # 🆕 Track the types of values you've talked to
            } for agent in self.agents
        }
        
        # 🔥 Dynamic calculation of required rounds
        num_rounds = self._calculate_required_rounds()
        print(f"   📊 According to configuration,Planned to proceed{num_rounds}Round the conversation to ensure full coverage")
        
        for round_idx in range(num_rounds):
            print(f"\n   💬 Page{round_idx+1}Round of Values Dialogue...")
            
            # Generate Conversation Pairing
            pairs = self._generate_diverse_dialogue_pairs(round_idx)
            
            for speaker, listener in pairs:
                # Have a two-way conversation
                dialogue = self._conduct_bidirectional_dialogue(
                    speaker, listener,
                    initial_understanding[speaker["id"]],
                    initial_understanding[listener["id"]]
                )
                
                dialogue_records.append(dialogue)
                
                # Analyze Value Element Absorption
                absorption = self._analyze_value_absorption(dialogue, speaker, listener)
                
                # Document absorbed value elements
                if absorption["speaker_absorbed"]:
                    value_absorption_tracker[speaker["id"]]["absorbed_elements"].extend(
                        absorption["speaker_absorbed"]
                    )
                    value_absorption_tracker[speaker["id"]]["dialogue_partners"].append(
                        listener["id"]
                    )
                    value_absorption_tracker[speaker["id"]]["dialogue_partner_values"].append(
                        listener["value_type"]
                    )
                
                if absorption["listener_absorbed"]:
                    value_absorption_tracker[listener["id"]]["absorbed_elements"].extend(
                        absorption["listener_absorbed"]
                    )
                    value_absorption_tracker[listener["id"]]["dialogue_partners"].append(
                        speaker["id"]
                    )
                    value_absorption_tracker[listener["id"]]["dialogue_partner_values"].append(
                        speaker["value_type"]
                    )
                
                print(f"      {speaker['family_name']} ↔ {listener['family_name']}")
        
        # Step3:Gathering Final Fair Understanding
        print("\n   📝 Gathering Fair Understanding After Dialogue...")
        final_understanding = {}
        
        for agent in self.agents:
            understanding = self._collect_evolved_fairness_view(
                agent,
                dialogue_records,
                value_absorption_tracker[agent["id"]]
            )
            final_understanding[agent["id"]] = understanding
            
            # Check to understand if there is a change
            if self._has_understanding_evolved(
                initial_understanding[agent["id"]],
                understanding
            ):
                print(f"    ✓ {agent['family_name']}Fair understanding of home has evolved")
        
        # Step4:Analyze Conversation Coverage
        print("\n   📊 Analyze Conversation Coverage...")
        coverage_stats = self._analyze_dialogue_coverage(value_absorption_tracker)
        
        # Step5:Analyze values plasticity
        print("\n   🔬 Analyze values plasticity...")
        plasticity_analysis = self._analyze_value_plasticity(
            initial_understanding,
            final_understanding,
            value_absorption_tracker
        )
        
        # Output plasticity analysis results
        print(f"\n   Values Plasticity Ranking(High to Low):")
        for rank, (vtype, score) in enumerate(plasticity_analysis["plasticity_ranking"], 1):
            print(f"    {rank}. {vtype}: {score:.2f}")
        
        # End Phase Log
        if self.logger:
            try:
                self.logger.end_stage(
                    stage_outcome=f"Done{len(dialogue_records)}conversations,Identify values plasticity differences",
                    consensus_level=0.0
                )
            except Exception:
                pass
        
        return {
            "dialogue_records": dialogue_records,
            "initial_understanding": initial_understanding,
            "final_understanding": final_understanding,
            "absorption_tracker": value_absorption_tracker,
            "plasticity_analysis": plasticity_analysis,
            "coverage_stats": coverage_stats
        }
    
    def _calculate_required_rounds(self) -> int:
        """Dynamically calculate required conversation rounds
        
        According toAgentQuantity and Values Distribution Calculate the minimum number of rounds required:
        1. Requires at least (V-1) Round eachAgentExposure to all other values
        2. need to have enough rounds for allAgentcan participate.
        3. Increase buffer rounds to cope with uneven distribution
        """
        value_types = set(a["value_type"] for a in self.agents)
        n_value_types = len(value_types)
        n_agents = len(self.agents)
        
        if n_value_types <= 1:
            print("   ⚠️ Warning:There is only one value,Inability to engage in cross-value dialogue")
            return 0
        
        # Calculate minimum required rounds
        # 1. Cover all values needs V-1 Round
        min_rounds_for_coverage = n_value_types - 1
        
        # 2. Let allAgentare participating in the required rounds(About half of each roundAgentParticipation)
        min_rounds_for_participation = (n_agents + 1) // 2
        
        # 3. Take the maximum of both
        base_rounds = max(min_rounds_for_coverage, min_rounds_for_participation)
        
        # 4. Increase1Wheel as buffer(Dealing with uneven distribution)
        required_rounds = base_rounds + 1
        
        return required_rounds
    
    def _collect_initial_fairness_view(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """CollectAgentInitial Fair Understanding of"""
        
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

[Family situation]
- Number of members:{agent['members']}People
- Workforce:{agent['labor_force']}People
- Core Beliefs:{agent['core_beliefs'][0]}

[Task]
Describe your experience with"Equitable resource allocation"Understanding:

1. What is Fairness?(For2-3Sentence description)
2. What are the key criteria for judging whether the distribution is fair??
3. In Resource Allocation,What principles do you value most??

Please be sincere,Articulate your point of view,No more than150Words.
"""
        
        model_name = get_model_name()
        temperature = 0.7
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation,Please genuinely express your understanding of fairness in accordance with your values."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=300
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="value_dialogue-initial",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={"view_type": "initial_fairness"}
                )
            
            # Extract summary
            summary = content[:50] + "..." if len(content) > 50 else content
            
            return {
                "full_view": content,
                "summary": summary,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"   ⚠️ {agent['family_name']}Initial understanding acquisition failed: {e}")
            return {
                "full_view": "Failed to fetch",
                "summary": "Fair understanding based on values",
                "timestamp": time.time()
            }
    
    def _generate_diverse_dialogue_pairs(self, round_idx: int) -> List[Tuple[Dict, Dict]]:
        """Generate Conversation Pairing - Roundtable Rotation Algorithm
        
        UseRound-Robin TournamentThe algorithm ensures:
        1. Each value pair will be paired
        2. Systematically covers all value combinations
        3. AllAgentSame level of involvement
        """
        # Group by Values
        value_groups = {}
        for agent in self.agents:
            vtype = agent["value_type"]
            if vtype not in value_groups:
                value_groups[vtype] = []
            value_groups[vtype].append(agent)
        
        value_types = list(value_groups.keys())
        n_value_types = len(value_types)
        
        if n_value_types < 2:
            print("   ⚠️ Warning:AllAgentShared values,Inability to engage in cross-value dialogue")
            return []
        
        # 🔥 Use the roundtable rotation algorithm to get value pairs for this round
        value_pair_schedule = self._create_round_robin_schedule(value_types)
        
        # Get this round of Values Matchmaking
        if round_idx < len(value_pair_schedule):
            round_pairs = value_pair_schedule[round_idx]
        else:
            # If the predetermined round is exceeded,Recycle
            round_pairs = value_pair_schedule[round_idx % len(value_pair_schedule)]
        
        pairs = []
        
        # Created for each value pairAgentPair
        for vtype1, vtype2 in round_pairs:
            agents1 = value_groups.get(vtype1, [])
            agents2 = value_groups.get(vtype2, [])
            
            if not agents1 or not agents2:
                continue
            
            # Matchmaking Strategies:Let each groupAgentBoth take turns pairing
            # Useround_idxAs offset,Let different rounds pair differentlyAgent
            max_len = max(len(agents1), len(agents2))
            for i in range(max_len):
                # RecycleAgent,Make sure everyone can participate
                agent1 = agents1[(i + round_idx) % len(agents1)]
                agent2 = agents2[(i + round_idx) % len(agents2)]
                
                if agent1["id"] != agent2["id"]:
                    pairs.append((agent1, agent2))
        
        # Deduplication(Avoid duplication of the same pair in this round)
        unique_pairs = []
        seen = set()
        for a1, a2 in pairs:
            pair_key = tuple(sorted([a1["id"], a2["id"]]))
            if pair_key not in seen:
                unique_pairs.append((a1, a2))
                seen.add(pair_key)
        
        # Statistical engagement
        used_agents = set()
        for a1, a2 in unique_pairs:
            used_agents.add(a1["id"])
            used_agents.add(a2["id"])
        
        print(f"      This round of pairing{len(unique_pairs)}Yes.,Overwrite{len(used_agents)}/{len(self.agents)}PieceAgent")
        
        return unique_pairs
    
    def _create_round_robin_schedule(self, value_types: List[str]) -> List[List[Tuple[str, str]]]:
        """Create Roundtable Rollover Pairing Table
        
        fornValues,Generaten-1Matchmaking,Make sure each values pair is matched
        
        Example:5Values [A, B, C, D, E]
        Page1Round: (A,B), (A,C), (A,D), (A,E), (B,C), (B,D), (B,E), (C,D), (C,E), (D,E) Subset of
        We actually use a rotation matrix:
        Page1Round: (0,1), (2,3), 4Separate...
        Page2Round: (0,2), (1,4), 3Separate...
        ...
        """
        n = len(value_types)
        if n < 2:
            return []
        
        schedule = []
        
        # Round Table Algorithm:Requiredn-1Complete all matches in rounds
        for round_idx in range(n - 1):
            round_pairs = []
            
            # Using the Round Table Rotation Algorithm
            # Fixed Section0locations,Rotate elsewhere
            for i in range(n):
                # Calculate index of paired partner
                j = (i + round_idx + 1) % n
                
                # Ensurei < j,Avoid duplicate pairings
                if i < j:
                    round_pairs.append((value_types[i], value_types[j]))
            
            schedule.append(round_pairs)
        
        return schedule
    
    def _conduct_bidirectional_dialogue(self, speaker: Dict, listener: Dict,
                                       speaker_initial: Dict, listener_initial: Dict) -> Dict:
        """Engage in a two-way value dialogue"""
        
        # Phase 1:SpeakerElaboration
        speaker_prompt = f"""You are{speaker['family_name']}Representatives of the family,Values are{speaker['value_type']}.

[Your understanding of fairness]
{speaker_initial['full_view']}

[Task]
Now with{listener['family_name']}Family({listener['value_type']}Values)Have a conversation.
Explain to the person:
1. What is at the heart of your view of equity
2. Why do you think this understanding is justified?

Request:Sincere,Open,Concise(No more than100Words)
"""
        
        speaker_statement = self._call_llm_simple(speaker_prompt, temperature=0.8)
        
        # Phase 2:ListenerResponses and questions
        listener_prompt = f"""You are{listener['family_name']}Representatives of the family,Values are{listener['value_type']}.

[Your understanding of fairness]
{listener_initial['full_view']}

[The other person's point of view]
{speaker['family_name']}Say:"{speaker_statement}"

[Task]
Please respond and ask:
1. What opinions do you agree or disagree with?Why?
2. Ask a question,Learn more about their values

Request:Respect but not follow blindly,Willing to understand(No more than100Words)
"""
        
        listener_response = self._call_llm_simple(listener_prompt, temperature=0.8)
        
        # Phase 3:SpeakerAnswer and reflect
        speaker_reflect_prompt = f"""You are{speaker['family_name']}Representatives of the family.

[The other party's response]
{listener['family_name']}Say:"{listener_response}"

[Task]
Answer the other person's question,and think about it.:
1. Whether the other person's point of view is justified?
2. Are you willing to incorporate certain elements of the other person's perspective?
3. Whether your fair understanding needs to be adjusted or supplemented?

Request:Reflect sincerely(No more than100Words)
"""
        
        speaker_reflection = self._call_llm_simple(speaker_reflect_prompt, temperature=0.7)
        
        # Phase 4:ListenerReflect
        listener_reflect_prompt = f"""You are{listener['family_name']}Representatives of the family.

[Response from the other party]
{speaker['family_name']}Say:"{speaker_reflection}"

[Task]
Reflect on this conversation:
1. Whether the other person's perspective influences yours?
2. Are you willing to stand up for your core values while,Absorb some of the other person's views?

Request:Simple reflection(No more than80Words)
"""
        
        listener_reflection = self._call_llm_simple(listener_reflect_prompt, temperature=0.7)
        
        # Record Conversation to Log
        if self.logger:
            try:
                self.logger.log_discussion_turn(
                    speaker_id=speaker["id"],
                    speaker_name=speaker["family_name"],
                    speaker_value_type=speaker["value_type"],
                    content=speaker_statement,
                    speech_type="value_statement",
                    target_topic="Fair Understanding Dialogue"
                )
                self.logger.log_discussion_turn(
                    speaker_id=listener["id"],
                    speaker_name=listener["family_name"],
                    speaker_value_type=listener["value_type"],
                    content=listener_response,
                    speech_type="value_response",
                    target_topic="Fair Understanding Dialogue"
                )
            except Exception:
                pass
        
        return {
            "speaker": speaker["id"],
            "listener": listener["id"],
            "speaker_name": speaker["family_name"],
            "listener_name": listener["family_name"],
            "speaker_statement": speaker_statement,
            "listener_response": listener_response,
            "speaker_reflection": speaker_reflection,
            "listener_reflection": listener_reflection,
            "timestamp": time.time()
        }
    
    def _call_llm_simple(self, prompt: str, temperature: float = 0.7) -> str:
        """SimplifiedLLMCall"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Failed to fetch: {str(e)}"
    
    def _parse_json(self, text: str, default: Any = None) -> Any:
        """InsightsJSONText,With fault-tolerant handling
        
        Parameter:
            text: JSONText
            default: Default value when parsing fails
        
        Back:
            Parsed Objects,ordefault
        """
        if not text or not isinstance(text, str):
            return default if default is not None else {}
        
        # Try1:Direct parsing
        try:
            return json.loads(text)
        except:
            pass
        
        # Try2:ExtractJSONBlock
        try:
            # FindJSONBlock(```json ... ``` or ``` ... ```)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except:
            pass
        
        # Try3:Find the first completeJSONObject
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        # Try4:Clear control characters after parsing
        try:
            cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
            return json.loads(cleaned)
        except:
            pass
        
        # All failed,Back to defaults
        return default if default is not None else {}
    
    def _analyze_value_absorption(self, dialogue: Dict, speaker: Dict, listener: Dict) -> Dict:
        """Analyze the absorption of value elements in conversations"""
        
        analysis_prompt = f"""Analyze the values impact in the following conversations:

[Interlocutor]
- {speaker['family_name']}({speaker['value_type']}Values)
- {listener['family_name']}({listener['value_type']}Values)

[Conversation content]
{speaker['family_name']}Elaboration:{dialogue['speaker_statement']}
{listener['family_name']}Response:{dialogue['listener_response']}
{speaker['family_name']}Reflect:{dialogue['speaker_reflection']}
{listener['family_name']}Reflect:{dialogue['listener_reflection']}

Please analyze:
1. {speaker['family_name']}Is it absorbed?{listener['family_name']}Values Element?What exactly??
2. {listener['family_name']}Is it absorbed?{speaker['family_name']}Values Element?What exactly??

inJSONFormat Back:
{{
  "speaker_absorbed": ["Element1", "Element2"],
  "listener_absorbed": ["Element1", "Element2"]
}}

If not absorbed,Returns an empty array.
"""
        
        response = self._call_llm_simple(analysis_prompt, temperature=0.3)
        parsed = self._parse_json(response, default={"speaker_absorbed": [], "listener_absorbed": []})
        
        return {
            "speaker_absorbed": parsed.get("speaker_absorbed", []),
            "listener_absorbed": parsed.get("listener_absorbed", [])
        }
    
    def _collect_evolved_fairness_view(self, agent: Dict, dialogue_records: List, 
                                      absorption_data: Dict) -> Dict:
        """Gathering Fair Understanding After Dialogue"""
        
        # Find out what's going on with theAgentRelated Conversations
        relevant_dialogues = [
            d for d in dialogue_records
            if d["speaker"] == agent["id"] or d["listener"] == agent["id"]
        ]
        
        # Build a summary of the conversation
        dialogue_summary = ""
        for idx, d in enumerate(relevant_dialogues[-2:], 1):  # Recent2conversations
            if d["speaker"] == agent["id"]:
                dialogue_summary += f"{idx}. You and{d['listener_name']}Conversation,You reflect on:{d['speaker_reflection'][:40]}...\n"
            else:
                dialogue_summary += f"{idx}. {d['speaker_name']}Chat with you,You reflect on:{d['listener_reflection'][:40]}...\n"
        
        # Absorbed Elements
        absorbed_summary = ""
        if absorption_data["absorbed_elements"]:
            absorbed_summary = "\nYou incorporated the following perspectives into the conversation:\n" + "\n".join([f"- {e}" for e in absorption_data["absorbed_elements"][:3]])
        
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

[Conversations you participated in]
{dialogue_summary}

{absorbed_summary}

[Task]
After conversations with other families,Please rephrase your"Equitable resource allocation"Understanding:

1. Has your understanding of fairness changed??
2. Now how do you define fair distribution?
3. Do you still adhere to your core principles,or has it expanded??

Please be sincere,No more than150Words.
"""
        
        model_name = get_model_name()
        temperature = 0.7
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation,After conversations with others,May have a new understanding of fairness."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=300
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="value_dialogue-evolved",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={"view_type": "evolved_fairness"}
                )
            
            summary = content[:50] + "..." if len(content) > 50 else content
            
            return {
                "full_view": content,
                "summary": summary,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"   ⚠️ {agent['family_name']}Evolutionary understanding acquisition failed: {e}")
            return {
                "full_view": "Failed to fetch",
                "summary": "Fair Understanding",
                "timestamp": time.time()
            }
    
    def _has_understanding_evolved(self, initial: Dict, final: Dict) -> bool:
        """Check if fair understanding has evolved"""
        # Simple Comparison:If the text is significantly different,then thinks that evolution
        initial_text = initial.get("full_view", "")
        final_text = final.get("full_view", "")
        
        if len(initial_text) < 10 or len(final_text) < 10:
            return False
        
        # If text similarity is lower than80%,Thought there was an evolution
        common_words = set(initial_text.split()) & set(final_text.split())
        total_words = set(initial_text.split()) | set(final_text.split())
        
        if len(total_words) == 0:
            return False
        
        similarity = len(common_words) / len(total_words)
        return similarity < 0.8
    
    def _analyze_value_plasticity(self, initial: Dict, final: Dict, 
                                 absorption_tracker: Dict) -> Dict:
        """Analyze the plasticity of different values"""
        
        # Group by value type
        value_types = {}
        for agent in self.agents:
            vtype = agent["value_type"]
            if vtype not in value_types:
                value_types[vtype] = []
            value_types[vtype].append(agent["id"])
        
        # Calculate the plasticity score for each value
        plasticity_scores = {}
        
        for vtype, agent_ids in value_types.items():
            total_absorbed = 0
            total_changes = 0
            
            for agent_id in agent_ids:
                # Count the number of value elements absorbed
                absorbed_count = len(absorption_tracker[agent_id]["absorbed_elements"])
                total_absorbed += absorbed_count
                
                # Check if fair understanding has changed
                if self._has_understanding_evolved(initial[agent_id], final[agent_id]):
                    total_changes += 1
            
            # Calculate plasticity score
            avg_absorbed = total_absorbed / len(agent_ids) if len(agent_ids) > 0 else 0
            change_rate = total_changes / len(agent_ids) if len(agent_ids) > 0 else 0
            plasticity_score = avg_absorbed * 0.6 + change_rate * 0.4
            
            plasticity_scores[vtype] = {
                "score": plasticity_score,
                "avg_absorbed": avg_absorbed,
                "change_rate": change_rate,
                "sample_size": len(agent_ids)
            }
        
        # Sort
        ranked = sorted(plasticity_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        return {
            "plasticity_scores": plasticity_scores,
            "plasticity_ranking": [(vtype, data["score"]) for vtype, data in ranked],
            "most_plastic": ranked[0][0] if ranked else None,
            "most_persistent": ranked[-1][0] if ranked else None
        }
    
    def _analyze_dialogue_coverage(self, absorption_tracker: Dict) -> Dict:
        """Analyze Conversation Coverage,Ensure that eachAgentExposure to all values"""
        
        # Get all value types
        all_value_types = set(agent["value_type"] for agent in self.agents)
        
        coverage_report = {}
        full_coverage_count = 0
        
        for agent in self.agents:
            agent_id = agent["id"]
            agent_value = agent["value_type"]
            
            # TheAgentValues Conversed
            dialogue_values = set(absorption_tracker[agent_id]["dialogue_partner_values"])
            
            # Values that should be talked about(Except your own.)
            expected_values = all_value_types - {agent_value}
            
            # Calculate Coverage
            if len(expected_values) > 0:
                coverage_rate = len(dialogue_values & expected_values) / len(expected_values)
            else:
                coverage_rate = 1.0  # There is only one value
            
            # Uncovered Values
            missing_values = expected_values - dialogue_values
            
            coverage_report[agent_id] = {
                "agent_name": agent["family_name"],
                "agent_value": agent_value,
                "dialogue_values": list(dialogue_values),
                "expected_values": list(expected_values),
                "missing_values": list(missing_values),
                "coverage_rate": coverage_rate,
                "full_coverage": len(missing_values) == 0
            }
            
            if len(missing_values) == 0:
                full_coverage_count += 1
            else:
                print(f"    {agent['family_name']}Home Uncontacted Values: {', '.join(missing_values)}")
        
        # Overall Statistics
        avg_coverage = sum(r["coverage_rate"] for r in coverage_report.values()) / len(coverage_report)
        full_coverage_rate = full_coverage_count / len(self.agents)
        
        print(f"    Average Coverage: {avg_coverage:.1%}")
        print(f"    Full CoverageAgentNumber: {full_coverage_count}/{len(self.agents)} ({full_coverage_rate:.1%})")
        
        return {
            "per_agent": coverage_report,
            "average_coverage": avg_coverage,
            "full_coverage_count": full_coverage_count,
            "full_coverage_rate": full_coverage_rate
        }
    
    # ========================================
    # 🆕 New Stage2:Consultation framework based on dialogue history
    # ========================================
    
    def _negotiate_framework_with_dialogue(self, dialogue_results: Dict) -> Dict[str, Any]:
        """Phase2:Based on the Dialogue History Consultation Framework"""
        self.current_stage = "framework"
        
        print("\n═══════════════════════════════════════")
        print("   Phase2:Negotiated Allocation Framework")
        print("═══════════════════════════════════════")
        
        # Start Framework Negotiation Phase
        if self.logger:
            try:
                self.logger.start_stage("negotiate_framework", [agent["id"] for agent in self.agents])
            except Exception:
                pass
        
        # Step1:Collect Proposed Allocation
        print("\n   📊 Gather allotment suggestions for each household...")
        ratio_proposals = {}
        
        for agent in self.agents:
            agent_id = agent["id"]
            
            # Build thisAgentConversation Background
            dialogue_context = self._build_agent_dialogue_context(
                agent_id, 
                dialogue_results
            )
            
            # Collect proposals
            proposal = self._collect_proposal_with_dialogue_context(
                agent,
                dialogue_context,
                dialogue_results["final_understanding"][agent_id]
            )
            
            ratio_proposals[agent_id] = proposal
            ratio_value = proposal.get("suggested_ratio", 0)
            print(f"    {agent['family_name']}Proportion of homes recommended:{ratio_value:.1%}")
        
        # Step2:Identify and Negotiate Disputes
        aggregated = self._aggregate_ratio_proposals(ratio_proposals)
        disputes = self._identify_ratio_disputes_enhanced(ratio_proposals, aggregated)
        
        if not disputes:
            print("   ✅ No apparent disputes,Direct access to the initial proposal")
            final_proposals = ratio_proposals
            negotiation_data = {"method": "direct_acceptance", "rounds": 0}
        else:
            print(f"   🔥 Recognized{len(disputes)}disputed points,Start Negotiation...")
            final_proposals, negotiation_log = self._conduct_multi_round_negotiation(
                ratio_proposals, disputes, {}
            )
            negotiation_data = {
                "method": "multi_round",
                "rounds": len(negotiation_log),
                "log": negotiation_log
            }
        
        # Step3:Building the framework
        allocation_ratios = {
            aid: p.get("current_ratio", p.get("suggested_ratio", 1.0/len(self.agents)))
            for aid, p in final_proposals.items()
        }
        
        framework = {
            "strategy": {
                "name": "Dialogue-driven negotiation of assignments",
                "base_method": "dialogue_negotiated",
                "description": f"Values Based Dialogue,Via{negotiation_data.get('rounds', 0)}Round of negotiation reached"
            },
            "ratios": allocation_ratios,
            "negotiated_ratios": allocation_ratios,
            "negotiation_data": negotiation_data,
            "based_on_dialogue": True
        }
        
        print(f"\n   ✅ Negotiation complete:{framework['strategy']['name']}")
        
        # End Frame Phase
        if self.logger:
            try:
                self.logger.end_stage(
                    stage_outcome=f"Negotiate to reach consensus" if negotiation_data.get("method") == "direct_acceptance" else f"Meridian{negotiation_data['rounds']}Round Negotiation",
                    consensus_level=0.9
                )
            except Exception:
                pass
        
        return framework
    
    def _build_agent_dialogue_context(self, agent_id: int, dialogue_results: Dict) -> str:
        """forAgentBuild Conversation Background Summary"""
        
        agent = next((a for a in self.agents if a["id"] == agent_id), None)
        if not agent:
            return ""
        
        dialogues = dialogue_results["dialogue_records"]
        
        # Screening vs. theAgentRelated Conversations
        relevant_dialogues = [
            d for d in dialogues
            if d["speaker"] == agent_id or d["listener"] == agent_id
        ]
        
        context_parts = []
        
        # 1. Conversation Summary
        context_parts.append("[Summary of conversations you participated in]")
        for idx, dialogue in enumerate(relevant_dialogues[-3:], 1):  # Recent3conversations
            if dialogue["speaker"] == agent_id:
                partner_name = dialogue["listener_name"]
                reflection = dialogue["speaker_reflection"][:40]
                context_parts.append(f"{idx}. You and{partner_name}Home conversations,You reflect on:{reflection}...")
            else:
                partner_name = dialogue["speaker_name"]
                reflection = dialogue["listener_reflection"][:40]
                context_parts.append(f"{idx}. {partner_name}Home conversations with you,You reflect on:{reflection}...")
        
        # 2. Absorbed value elements
        absorbed = dialogue_results["absorption_tracker"][agent_id]["absorbed_elements"]
        if absorbed:
            context_parts.append("\n[The perspectives you absorbed in the conversation]")
            for element in absorbed[:3]:  # Max.3Piece
                context_parts.append(f"- {element}")
        
        return "\n".join(context_parts)
    
    def _collect_proposal_with_dialogue_context(self, agent: Dict, dialogue_context: str, 
                                               final_understanding: Dict) -> Dict:
        """Collect Assignment Proposals with Conversation Background"""
        
        prompt = f"""You are{agent['family_name']}Representatives of the family,Values are{agent['value_type']}.

{dialogue_context}

[Your understanding of fairness]
{final_understanding['full_view']}

[Family situation]
- Household Population:{agent['members']}People
- Workforce:{agent['labor_force']}People

[Community Resource Assignment Tasks]
Community Existing{self.total_grain:.1f}Unit resources need to be in{len(self.agents)}Allocation between families.
- Total population:{self.total_members}People
- Total Workforce:{self.total_labor}People

[Task]
Based on your values and conversations,Submit:In this assignment,How much your family deserves?

Please useJSONFormat Answer:
{{
  "suggested_ratio": 0.XX,  // Proportion of your home that should be(0To1Between,As0.10Indicates that your home receives10%Resources)
  "reasoning": "Why your family deserves this share(Can cite ideas from conversations)",
  "flexibility": "The space you're willing to compromise(high/medium/low)"
}}

Description:hereratioRefers to where your home is located{len(self.agents)}What share of households should be allocated.
"""
        
        model_name = get_model_name()
        temperature = 0.7
        
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a family representative participating in a community resource consultation,Suggest assignments based on conversational experiences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=300
            )
            duration = time.time() - start_time
            
            content = response.choices[0].message.content
            
            # RecordsLLMInteraction
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_negotiation_call(
                    round_number=self.round_number,
                    stage="framework-proposal",
                    agent=agent,
                    input_prompt=prompt,
                    raw_output=content,
                    model=model_name,
                    temperature=temperature,
                    duration=duration,
                    success=True,
                    processed_data={"proposal_type": "with_dialogue_context"}
                )
            
            # InsightsJSON
            parsed = self._parse_json(content, default={
                "suggested_ratio": 1.0 / len(self.agents),
                "reasoning": "Based on the principle of equity",
                "flexibility": "medium"
            })
            
            # 🔧 Make sure to includeideal_ratioField(Compatibility)
            if "suggested_ratio" in parsed and "ideal_ratio" not in parsed:
                parsed["ideal_ratio"] = parsed["suggested_ratio"]
            elif "ideal_ratio" not in parsed:
                parsed["ideal_ratio"] = 1.0 / len(self.agents)
            
            return parsed
            
        except Exception as e:
            print(f"   ⚠️ {agent['family_name']}Proposal fetching failed: {e}")
            default_ratio = 1.0 / len(self.agents)
            return {
                "suggested_ratio": default_ratio,
                "ideal_ratio": default_ratio,  # 🔧 Compatibility
                "reasoning": "Failed to fetch,Use Equal Distribution",
                "flexibility": "medium"
            }

    # ========================================================================
    # 🆕 Refactored Negotiation Method(Focus Assignment,Remove Values Discussion)
    # ========================================================================
    
    def _collect_allocation_requests_v2(self) -> Dict[int, Dict[str, Any]]:
        """Phase1:Collect eachagentAllocation Expectations(Values-based+Family situation)"""
        print("\n  📝 Gather household distribution expectations...")
        requests = {}
        
        for agent in self.agents:
            try:
                request = self._get_agent_allocation_request_v2(agent)
                requests[agent["id"]] = request
                print(f"     ✓ {agent['family_name']}({agent['value_type']})Expectations:{request.get('requested_amount', 0):.1f}Unit")
            except Exception as e:
                print(f"     ⚠️ {agent['family_name']}Request failed:{e}")
                # Default Expectations:Based on average distribution
                default_amount = self.total_grain / len(self.agents)
                requests[agent["id"]] = {
                    "requested_amount": default_amount,
                    "reasoning": "Failed to fetch,Use default values",
                    "comments_on_others": {}
                }
        
        total_requested = sum(r.get("requested_amount", 0) for r in requests.values())
        print(f"\n  📊 Summary of Expectations:Total demand={total_requested:.1f}Unit,Available={self.total_grain:.1f}Unit")
        if total_requested > self.total_grain:
            print(f"     ⚠️ Total Demand Exceeded{total_requested - self.total_grain:.1f}Unit({(total_requested/self.total_grain - 1)*100:.1f}%)")
        
        return requests
    
    def _get_agent_allocation_request_v2(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Get SingleagentAllocation Expectations(Use newPrompt)"""
        agent_id = agent["id"]
        
        # Prepare additional family information
        other_families_info = ""
        for other_agent in self.agents:
            if other_agent["id"] != agent_id:
                other_need = self.survival_needs.get(other_agent["id"], {}).get("grain", 0)
                other_families_info += f"- {other_agent['family_name']}Home:{other_agent['members']}People,{other_agent['labor_force']}Workforce,Survival Needs{other_need:.1f}Unit\n"
        
        # My needs
        my_need = self.survival_needs.get(agent_id, {}).get("grain", 0)
        
        # Calculate Reference
        avg_per_family = self.total_grain / len(self.agents)
        
        # BuildPrompt
        prompt = f"""You are{agent['family_name']}Family(ID:{agent_id}),Values are{agent['value_type']}.

[Community resources]
- Total Grain:{self.total_grain}Unit(Shared by the whole community)
- Total Community Population:{self.total_members}People
- Total Community Workforce:{self.total_labor}People
- If evenly distributed:Appointments per household{avg_per_family:.1f}Unit

[Your family situation]
- Number of members:{agent['members']}People
- Workforce:{agent['labor_force']}People
- Survival Needs:{my_need:.1f}Unit(It's just survival.,Excluding production requirements)
- Core Values:{agent['value_type']}({agent.get('core_beliefs', ['Equitable distribution'])[0]})

[What happened to the other families]
{other_families_info}

[Task:Raise your distribution expectations]

As{agent['value_type']}Family of Values,Please:

1. Propose the amount of food you would like to receive(Specific value,Unit:Unit grain)
   
   Important:
   - The quantity you expect should be taken into account[Survival Needs + Required for production],It's not just survival needs.
   - Reference:If evenly distributed,Appointments per household{avg_per_family:.1f}Unit
   - You can ask for more or less based on your values
   - Example:merit_basedMay ask for more(If you have a large workforce,),needs_basedMay be required to meet demand

2. State your reason(Based on your needs,Contribution,Values)

3. Evaluate other families objectively:
   - Families whose needs or contributions require special consideration?Why?
   - Based on your{agent['value_type']}Values,How do you think resources should be balanced between families?

Request:
- Direct,Specific,Propose a clear quantity
- Based on your{agent['value_type']}Position,But take into account the reality of the community
- Your review will be referenced during the negotiation process

Please useJSONFormat Answer:
{{
  "requested_amount": <The amount of food you expect(Number,should be in{my_need:.0f}-{avg_per_family*1.5:.0f}Between)>,
  "reasoning": "<Your reasons>",
  "comments_on_others": {{
    "<Family name>": "<Reviews>",
    ...
  }}
}}
"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a role-playing expert,Please answer questions based on the family information and values provided,inJSONFormat Back."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            # 🐛 DEBUG:PrintLLMOriginal Return
            print(f"       [DEBUG] {agent['family_name']}ofLLMBack(ago200Character):")
            print(f"       {content[:200]}")
            
            # InsightsJSON
            parsed = self._parse_json(content, default={
                "requested_amount": self.total_grain / len(self.agents),
                "reasoning": "Default Request",
                "comments_on_others": {}
            })
            
            # 🐛 DEBUG:Print parsing results
            print(f"       [DEBUG] After parsingrequested_amount: {parsed.get('requested_amount', 'NOT_FOUND')}")
            
            # Ensurerequested_amountIs Number
            if "requested_amount" not in parsed or not isinstance(parsed["requested_amount"], (int, float)):
                print(f"       ⚠️ requested_amountInvalid,Use default values:{self.total_grain / len(self.agents):.1f}")
                parsed["requested_amount"] = self.total_grain / len(self.agents)
            
            return parsed
            
        except Exception as e:
            print(f"       Get{agent['family_name']}Error requesting:{e}")
            return {
                "requested_amount": self.total_grain / len(self.agents),
                "reasoning": "Failed to fetch,Use average",
                "comments_on_others": {}
            }
    
    def _three_round_negotiation_v2(self, allocation_requests: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
        """Phase2:3Round of iterative negotiation"""
        self.negotiation_history = []
        
        # Generate Initial Scenario
        print("\n  🎯 Generate Initial Compromise...")
        current_proposal = self._generate_initial_proposal_v2(allocation_requests)
        self._print_proposal_summary(current_proposal, "Initial plan")
        
        # 3Round Negotiation
        for round_idx in range(3):
            print(f"\n  {'='*60}")
            print(f"  💬 Page{round_idx+1}/3Round Negotiation")
            print(f"  {'='*60}")
            
            # Gather feedback
            feedback = self._collect_feedback_on_proposal_v2(current_proposal, allocation_requests, round_idx+1)
            
            # Identify Disagreements
            conflicts, unhappy_agents = self._identify_conflicts_v2(feedback)
            
            # Dialogue and negotiation(If there is dissatisfaction)
            if unhappy_agents:
                print(f"\n     🗣️ {len(unhappy_agents)}family dissatisfaction,Conduct dialogue and negotiation...")
                dialogue_results = self._conduct_group_dialogue_v2(unhappy_agents, current_proposal, allocation_requests)
                
                # Conversation-based adjustments
                current_proposal = self._adjust_proposal_based_on_dialogue_v2(
                    current_proposal, feedback, dialogue_results, allocation_requests
                )
            else:
                print(f"\n     ✅ All Family Satisfaction>=3Minutes,Negotiation went well")
                # Feedback-based fine-tuning
                current_proposal = self._adjust_proposal_based_on_feedback_v2(
                    current_proposal, feedback, allocation_requests
                )
            
            # Record History
            self.negotiation_history.append({
                "round": round_idx + 1,
                "proposal": copy.deepcopy(current_proposal),
                "feedback": feedback,
                "conflicts": conflicts,
                "unhappy_count": len(unhappy_agents)
            })
            
            self._print_proposal_summary(current_proposal, f"Page{round_idx+1}After round adjustment")
        
        return current_proposal
    
    def _generate_initial_proposal_v2(self, allocation_requests: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
        """Generate Initial Compromise"""
        total_requested = sum(r.get("requested_amount", 0) for r in allocation_requests.values())
        
        # 🐛 DEBUG:Print expectations for each household
        print(f"\n  [DEBUG] Initial Scenario Generation - Expectation Details:")
        for agent_id, request in allocation_requests.items():
            agent = next((a for a in self.agents if a["id"] == agent_id), None)
            if agent:
                print(f"     {agent['family_name']}(ID:{agent_id}): Expectations{request.get('requested_amount', 0):.1f}Unit")
        print(f"  [DEBUG] Total demand={total_requested:.1f},Available={self.total_grain:.1f}")
        
        proposal = {}
        
        if total_requested <= self.total_grain:
            # Demand not exceeded,Direct Satisfaction + Allocation Remaining
            remaining = self.total_grain - total_requested
            print(f"  [DEBUG] Demand not exceeded,Remaining{remaining:.1f}Unit Split")
            for agent_id, request in allocation_requests.items():
                base_amount = request.get("requested_amount", 0)
                bonus = remaining / len(allocation_requests)
                proposal[agent_id] = {"grain": base_amount + bonus}
        else:
            # Demand exceeded,Scaled down
            scale_factor = self.total_grain / total_requested
            print(f"  [DEBUG] Demand exceeded,Scaled down,scale_factor={scale_factor:.4f}")
            for agent_id, request in allocation_requests.items():
                requested = request.get("requested_amount", 0)
                allocated = requested * scale_factor
                proposal[agent_id] = {"grain": allocated}
                agent = next((a for a in self.agents if a["id"] == agent_id), None)
                if agent:
                    print(f"     {agent['family_name']}: {requested:.1f} × {scale_factor:.4f} = {allocated:.1f}")
        
        return proposal
    
    def _collect_feedback_on_proposal_v2(
        self, 
        proposal: Dict[int, Dict[str, float]], 
        allocation_requests: Dict[int, Dict[str, Any]],
        round_num: int
    ) -> List[Dict[str, Any]]:
        """CollectagentsFeedback on current scenario"""
        print(f"\n     📊 Gather feedback...")
        feedback_list = []
        
        for agent in self.agents:
            agent_id = agent["id"]
            allocated = proposal.get(agent_id, {}).get("grain", 0)
            requested = allocation_requests.get(agent_id, {}).get("requested_amount", 0)
            gap = allocated - requested
            
            # Build Other Family Allocation Summary
            others_allocation = ""
            for other_id, other_alloc in proposal.items():
                if other_id != agent_id:
                    other_agent = next((a for a in self.agents if a["id"] == other_id), None)
                    if other_agent:
                        others_allocation += f"- {other_agent['family_name']}:{other_alloc.get('grain', 0):.1f}Unit\n"
            
            prompt = f"""You are{agent['family_name']}Family(Values:{agent['value_type']}).

[Current Proposed Allocation Scheme](Page{round_num}Round)
- Your family:{allocated:.1f}Unit grain
- Your expectations:{requested:.1f}Unit
- Gap:{gap:+.1f}Unit({'Satisfaction rate' if gap >= 0 else 'Gap'}:{abs(allocated/requested*100 - 100):.1f}%)

[Other Family Allocations]
{others_allocation}

[Important]
This is a negotiation process,Be authentic about how you feel!
Based on your{agent['value_type']}Values,If you think the distribution is unfair,Please specify.

[Your Comment]
1. Your true satisfaction with your current plan(1-5Minutes)
2. If<=3Minutes,Please specify your dissatisfaction:
   - You think you share too little/Too much?Why?
   - Which households are unreasonably allocated?Why?
3. Your adjustment suggestion(Specific amount and justification)

Please useJSONFormat Answer:
{{
  "satisfaction": <1-5Number>,
  "problems": "<If<=3Minutes,Describe the grievance>",
  "adjustment_suggestions": "<If<=3Minutes,Suggest specific adjustments>"
}}
"""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are a role-playing expert,inJSONFormat Answer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=400
                )
                
                content = response.choices[0].message.content
                parsed = self._parse_json(content, default={
                    "satisfaction": 3,
                    "problems": "",
                    "adjustment_suggestions": ""
                })
                
                # EnsuresatisfactionIs Number
                if "satisfaction" not in parsed or not isinstance(parsed["satisfaction"], (int, float)):
                    parsed["satisfaction"] = 3
                
                feedback_list.append({
                    "agent_id": agent_id,
                    "agent_name": agent['family_name'],
                    "agent_value": agent['value_type'],
                    "allocated": allocated,
                    "requested": requested,
                    "gap": gap,
                    "satisfaction": parsed["satisfaction"],
                    "problems": parsed.get("problems", ""),
                    "suggestions": parsed.get("adjustment_suggestions", "")
                })
                
                print(f"        {agent['family_name']}:Satisfaction{parsed['satisfaction']}/5")
                
            except Exception as e:
                print(f"        ⚠️ {agent['family_name']}Failed to get feedback:{e}")
                feedback_list.append({
                    "agent_id": agent_id,
                    "agent_name": agent['family_name'],
                    "agent_value": agent['value_type'],
                    "allocated": allocated,
                    "requested": requested,
                    "gap": gap,
                    "satisfaction": 3,
                    "problems": "",
                    "suggestions": ""
                })
        
        return feedback_list
    
    def _identify_conflicts_v2(self, feedback: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Dict]]:
        """Identify conflicts and grievancesagents"""
        # Dissatisfiedagents(Satisfaction<=3Minutes,Includes"Barely accepting"Situation)
        unhappy_agents = [f for f in feedback if f.get("satisfaction", 3) <= 3]
        
        # Conflict vs.(Temporarily simplified,Subsequent extensibility)
        conflicts = []
        
        return conflicts, unhappy_agents
    
    def _conduct_group_dialogue_v2(
        self, 
        unhappy_agents: List[Dict[str, Any]], 
        current_proposal: Dict[int, Dict[str, float]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Conduct breakout session negotiation"""
        num_unhappy = len(unhappy_agents)
        
        if num_unhappy <= 4:
            # Small number of dissatisfied families: use an all-member conversation.
            return self._all_member_dialogue_v2(unhappy_agents, current_proposal, allocation_requests)
        elif num_unhappy <= 8:
            # Moderate dissatisfaction: use value-oriented group conversations.
            return self._group_dialogue_v2(unhappy_agents, current_proposal, allocation_requests)
        else:
            # Widespread dissatisfaction: prioritize the least satisfied families.
            top_unhappy = sorted(unhappy_agents, key=lambda x: x.get("satisfaction", 3))[:6]
            return self._group_dialogue_v2(top_unhappy, current_proposal, allocation_requests)
    
    def _all_member_dialogue_v2(
        self, 
        unhappy_agents: List[Dict[str, Any]], 
        current_proposal: Dict[int, Dict[str, float]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Conversation with all dissatisfied families (at most four agents)."""
        print(f"        💬 All-member conversation ({len(unhappy_agents)} dissatisfied families)")
        
        # Construct the conversation prompt.
        unhappy_list = ""
        for f in unhappy_agents:
            unhappy_list += f"- {f['agent_name']}(Satisfaction{f['satisfaction']}/5):{f.get('problems', 'Dissatisfied')}\n"
        
        prompt = f"""[Collective Negotiation Dial]

The current allocation scheme raises the following grievances:
{unhappy_list}

Please express your dissatisfaction with the family:
1. What's the most unacceptable thing about you??
2. What compromises are you willing to make to reach consensus??
3. How do you think the allocation should be adjusted?

Please useJSONFormat Answer(One entry per family):
{{
  "<Family name>": {{
    "unacceptable": "<Unacceptable points>",
    "willing_to_compromise": "<Content willing to compromise>",
    "adjustment_proposal": "<Adjustment Suggest>"
  }},
  ...
}}
"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are the negotiation moderator,Helping multiple families reach consensus."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            parsed = self._parse_json(content, default={})
            
            print(f"        ✓ Conversation Complete,Collected{len(parsed)}responses from families")
            return {"type": "group_dialogue", "results": parsed}
            
        except Exception as e:
            print(f"        ⚠️ Conversation failed:{e}")
            return {"type": "group_dialogue", "results": {}}
    
    def _group_dialogue_v2(
        self, 
        unhappy_agents: List[Dict[str, Any]], 
        current_proposal: Dict[int, Dict[str, float]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Group conversations(>4Dissatisfiedagents)"""
        print(f"        💬 Group Conversation Mode({len(unhappy_agents)}disgruntled families)")
        
        # Group by Values
        groups = {}
        for f in unhappy_agents:
            value_type = f.get("agent_value", "unknown")
            if value_type not in groups:
                groups[value_type] = []
            groups[value_type].append(f)
        
        all_results = {}
        
        for value_type, group_members in groups.items():
            if len(group_members) == 0:
                continue
            
            print(f"           Group{len(all_results)+1}({value_type}):{len(group_members)}families")
            
            # Conversations per group
            group_list = ""
            for f in group_members:
                group_list += f"- {f['agent_name']}(Satisfaction{f['satisfaction']}/5)\n"
            
            prompt = f"""[Group consultations:{value_type}Values Family]

Dissatisfied families in this group:
{group_list}

Invite this group of families to discuss:
1. What are your common aspirations??
2. How are you willing to compromise to reach consensus?
3. How do you suggest adjusting the allocation?

Please useJSONFormat Answer:
{{
  "common_demands": "<Joint Appeal>",
  "compromise_willingness": "<Willingness to compromise>",
  "group_proposal": "<Group Recommendations>"
}}
"""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You are the moderator of the group consultation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                content = response.choices[0].message.content
                parsed = self._parse_json(content, default={})
                all_results[value_type] = parsed
                
            except Exception as e:
                print(f"           ⚠️ Group{len(all_results)+1}Conversation failed:{e}")
        
        print(f"        ✓ Done{len(all_results)}Group Conversations")
        return {"type": "group_dialogue", "results": all_results}
    
    def _adjust_proposal_based_on_dialogue_v2(
        self,
        current_proposal: Dict[int, Dict[str, float]],
        feedback: List[Dict[str, Any]],
        dialogue_results: Dict[str, Any],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Adjust the protocol based on the outcome of the conversation"""
        adjusted_proposal = copy.deepcopy(current_proposal)
        
        # Simplified Adjustment Logic:UnhappyagentsIncrease Allocation,From SatisfiedagentsIntermediate Adjustment
        unhappy = [f for f in feedback if f.get("satisfaction", 3) < 3]
        happy = [f for f in feedback if f.get("satisfaction", 3) >= 4]
        
        if not unhappy or not happy:
            return adjusted_proposal
        
        # Calculate Adjustments
        total_deficit = sum(f.get("gap", 0) for f in unhappy if f.get("gap", 0) < 0)
        total_surplus = sum(
            (adjusted_proposal.get(f['agent_id'], {}).get('grain', 0) - 
             allocation_requests.get(f['agent_id'], {}).get('requested_amount', 0))
            for f in happy
        )
        
        # Dispensing a portion from the satisfied to the dissatisfied
        adjustment_amount = min(abs(total_deficit) * 0.3, total_surplus * 0.2)
        
        if adjustment_amount > 0:
            # Add to Dissatisfied
            per_unhappy = adjustment_amount / len(unhappy)
            for f in unhappy:
                agent_id = f['agent_id']
                current = adjusted_proposal.get(agent_id, {}).get('grain', 0)
                adjusted_proposal[agent_id] = {"grain": current + per_unhappy}
            
            # Decrease from Satisfied
            per_happy = adjustment_amount / len(happy)
            for f in happy:
                agent_id = f['agent_id']
                current = adjusted_proposal.get(agent_id, {}).get('grain', 0)
                adjusted_proposal[agent_id] = {"grain": max(0, current - per_happy)}
        
        # Ensure total is unchanged
        total_allocated = sum(a.get("grain", 0) for a in adjusted_proposal.values())
        if abs(total_allocated - self.total_grain) > 0.01:
            scale = self.total_grain / total_allocated if total_allocated > 0 else 1.0
            for agent_id in adjusted_proposal:
                adjusted_proposal[agent_id]["grain"] *= scale
        
        return adjusted_proposal
    
    def _adjust_proposal_based_on_feedback_v2(
        self,
        current_proposal: Dict[int, Dict[str, float]],
        feedback: List[Dict[str, Any]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Feedback-based fine-tuning scheme(When no conversation is needed)"""
        # Fine-Tuning Logic:Slightly Smooth Satisfaction Difference
        adjusted_proposal = copy.deepcopy(current_proposal)
        
        avg_satisfaction = sum(f.get("satisfaction", 3) for f in feedback) / len(feedback) if feedback else 3
        
        for f in feedback:
            agent_id = f['agent_id']
            satisfaction = f.get("satisfaction", 3)
            current_alloc = adjusted_proposal.get(agent_id, {}).get('grain', 0)
            
            # If Satisfaction is Below Average,Slight increase
            if satisfaction < avg_satisfaction:
                adjustment = (avg_satisfaction - satisfaction) * 1.0  # Per Point Gap Adjustment1Unit
                adjusted_proposal[agent_id] = {"grain": current_alloc + adjustment}
            # If Satisfaction is Above Average,Slightly reduced
            elif satisfaction > avg_satisfaction:
                adjustment = (satisfaction - avg_satisfaction) * 0.5  # Decrease by a small amount
                adjusted_proposal[agent_id] = {"grain": max(0, current_alloc - adjustment)}
        
        # Normalization
        total_allocated = sum(a.get("grain", 0) for a in adjusted_proposal.values())
        if total_allocated > 0:
            scale = self.total_grain / total_allocated
            for agent_id in adjusted_proposal:
                adjusted_proposal[agent_id]["grain"] *= scale
        
        return adjusted_proposal
    
    def _final_confirmation_v2(
        self,
        final_proposal: Dict[int, Dict[str, float]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Phase3:Final confirmation"""
        print("\n  ✅ Collect final confirmation...")
        
        confirmations = []
        accept_count = 0
        
        for agent in self.agents:
            agent_id = agent["id"]
            allocated = final_proposal.get(agent_id, {}).get("grain", 0)
            requested = allocation_requests.get(agent_id, {}).get("requested_amount", 0)
            
            prompt = f"""[Final protocol confirmation]

You are{agent['family_name']}Family({agent['value_type']}).

Via3Round Negotiation,Final Allocation Scenario:
- Your family gets:{allocated:.1f}Unit grain
- What you originally expected:{requested:.1f}Unit
- Satisfaction rate:{(allocated/requested*100) if requested > 0 else 100:.1f}%

Please confirm this final plan:
1. Do you accept this plan?(Yes/No)
2. Briefly describe how you feel(Satisfied/Acceptable/Dissatisfied,and why)

Please useJSONFormat Answer:
{{
  "accept": <trueorfalse>,
  "feeling": "<How you feel>"
}}
"""
            
            try:
                response = client.chat.completions.create(
                    model=get_model_name(),
                    messages=[
                        {"role": "system", "content": "You're a role-playing expert,inJSONFormat Answer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                
                content = response.choices[0].message.content
                parsed = self._parse_json(content, default={"accept": True, "feeling": "Acceptable"})
                
                accept = parsed.get("accept", True)
                if accept:
                    accept_count += 1
                    status = "✓ Accept"
                else:
                    status = "✗ Not Accepted"
                
                print(f"     {status} {agent['family_name']}:{parsed.get('feeling', '')}")
                
                confirmations.append({
                    "agent_id": agent_id,
                    "accept": accept,
                    "feeling": parsed.get("feeling", "")
                })
                
            except Exception as e:
                print(f"     ⚠️ {agent['family_name']}Confirmation failed:{e},Accept by default")
                confirmations.append({
                    "agent_id": agent_id,
                    "accept": True,
                    "feeling": "Accept by default"
                })
                accept_count += 1
        
        acceptance_rate = accept_count / len(self.agents) if self.agents else 0
        print(f"\n  📊 Acceptance rate:{acceptance_rate*100:.1f}% ({accept_count}/{len(self.agents)})")
        
        # If the acceptance rate is too low,Make final fine-tuning
        if acceptance_rate < 0.6:
            print(f"  ⚠️ Acceptance Rate Below60%,Make final fine-tuning...")
            final_proposal = self._last_resort_adjustment_v2(final_proposal, confirmations, allocation_requests)
        
        # Integerization
        final_proposal = self._integerize_allocation_v2(final_proposal)
        
        return final_proposal
    
    def _last_resort_adjustment_v2(
        self,
        proposal: Dict[int, Dict[str, float]],
        confirmations: List[Dict[str, Any]],
        allocation_requests: Dict[int, Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        """Final fine-tuning(When acceptance rate is too low)"""
        adjusted = copy.deepcopy(proposal)
        
        # Find out what's unacceptableagents
        rejecters = [c for c in confirmations if not c.get("accept", True)]
        accepters = [c for c in confirmations if c.get("accept", True)]
        
        if not rejecters or not accepters:
            return adjusted
        
        # Dispensing a little from the recipient to the rejector
        adjustment_per_rejecter = (self.total_grain * 0.05) / len(rejecters)  # 5%Resource reallocation
        adjustment_per_accepter = (adjustment_per_rejecter * len(rejecters)) / len(accepters)
        
        for c in rejecters:
            agent_id = c['agent_id']
            current = adjusted.get(agent_id, {}).get('grain', 0)
            adjusted[agent_id] = {"grain": current + adjustment_per_rejecter}
        
        for c in accepters:
            agent_id = c['agent_id']
            current = adjusted.get(agent_id, {}).get('grain', 0)
            adjusted[agent_id] = {"grain": max(0, current - adjustment_per_accepter)}
        
        # Normalization
        total = sum(a.get("grain", 0) for a in adjusted.values())
        if total > 0:
            scale = self.total_grain / total
            for agent_id in adjusted:
                adjusted[agent_id]["grain"] *= scale
        
        print(f"     ✓ Fine-tuning done")
        return adjusted
    
    def _integerize_allocation_v2(self, proposal: Dict[int, Dict[str, float]]) -> Dict[int, Dict[str, float]]:
        """Integer Allocation Results"""
        integerized = {}
        remainder = self.total_grain
        
        # Take the integer part first
        for agent_id, allocation in proposal.items():
            grain = allocation.get("grain", 0)
            int_grain = math.floor(grain)
            integerized[agent_id] = {"grain": int_grain}
            remainder -= int_grain
        
        # Allocation Remaining(Sort by decimal part)
        fractional_parts = [
            (agent_id, proposal[agent_id].get("grain", 0) - math.floor(proposal[agent_id].get("grain", 0)))
            for agent_id in proposal
        ]
        fractional_parts.sort(key=lambda x: x[1], reverse=True)
        
        for i in range(int(remainder)):
            if i < len(fractional_parts):
                agent_id = fractional_parts[i][0]
                integerized[agent_id]["grain"] += 1
        
        return integerized
    
    def _print_proposal_summary(self, proposal: Dict[int, Dict[str, float]], title: str):
        """Print Protocol Summary"""
        print(f"\n     📋 {title}:")
        for agent_id, allocation in proposal.items():
            agent = next((a for a in self.agents if a["id"] == agent_id), None)
            if agent:
                grain = allocation.get("grain", 0)
                print(f"        {agent['family_name']}:{grain:.1f}Unit")

def get_value_type_name(value_type: str) -> str:
    """Get a Chinese name for your values"""
    mapping = {
        "egalitarian": "Egalitarianism",
        "merit_based": "Contributionism",
        "needs_based": "Demand Doctrine",
        "altruistic": "Altruism",
        "pragmatic": "Pragmatism"
    }
    return mapping.get(value_type, value_type)


def collaborative_negotiation_distribution(
    total_resources: Dict[str, float],
    agents: List[Dict[str, Any]],
    survival_needs: Dict[int, Dict[str, float]],
    round_number: int = 1,
    previous_distribution: Dict[int, Dict[str, float]] = None,
    max_negotiation_rounds: int = 4,
    experiment_id: str = None,
    return_metadata: bool = True  # 🆕 New Parameter,Controls whether metadata is returned
) -> Any:
    """Main Entry Function for Collaborative Negotiation Assignment
    
    Parameter:
        total_resources: Total Resources Dictionary
        agents: Proxy List
        survival_needs: Survival Needs Dictionary
        round_number: Current number of rounds
        previous_distribution: Previous Round Allocation Result(Not used yet)
        max_negotiation_rounds: Maximum number of negotiation rounds(Not used yet)
        experiment_id: ExperimentID,Log used to unify all rounds
        return_metadata: Whether to return negotiation metadata(Containsdialogue_resultsEtc.)
        
    Back:
        Ifreturn_metadata=True: (final_allocation, negotiation_data)
        Ifreturn_metadata=False: final_allocation
    """
    
    try:
        # Create Negotiation Mechanism Instance
        negotiation = CollaborativeNegotiation(
            agents=agents,
            total_resources=total_resources,
            survival_needs=survival_needs,
            round_number=round_number,
            experiment_id=experiment_id
        )
        
        # Run the negotiation process
        final_allocation, negotiation_data = negotiation.run_collaborative_negotiation()
        
        # Print summary of results
        print(f"\n Summary of Negotiations:")
        print(f"   Successful Completion:{negotiation_data['success']}")
        print(f"   Method:{negotiation_data['method']}")
        print(f"   Completion Stage:{negotiation_data['stages_completed']}")
        
        # 🆕 Decide what to return based on the parameters
        if return_metadata:
            return final_allocation, negotiation_data
        else:
            return final_allocation
        
    except Exception as e:
        print(f"\n Negotiation allocation failed,Use equal distribution as fallback scheme: {str(e)}")
        
        # Fallback to Equal Distribution
        num_families = len(agents)
        if num_families == 0:
            fallback_result = {}
        else:
            per_family_amount = total_resources.get("grain", 0) / num_families
            fallback_result = {
                agent["id"]: {"grain": per_family_amount}
                for agent in agents
            }
        
        # 🆕 Fallback scenarios also need to be consideredreturn_metadata
        if return_metadata:
            fallback_metadata = {
                "success": False,
                "method": "fallback_equal",
                "stages_completed": 0,
                "dialogue_results": None,
                "error": str(e)
            }
            return fallback_result, fallback_metadata
        else:
            return fallback_result
