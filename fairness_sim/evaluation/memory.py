"""
Historical Memory Module - Phase 1 Implementation
Stores and retrieves historical data from multi-round simulations, enabling agents to reference past experiences during evaluation
"""
from typing import Dict, List, Any, Optional
import copy


class HistoricalMemoryModule:
    """
    Historical Memory Module
    
    Design Principles:
    1. Only stores and retrieves data, does not participate in allocation decisions
    2. Enable/disable switch for controlled experiments
    3. Minimal intrusion, easy to integrate
    """
    
    def __init__(self, enable: bool = True):
        """Initialize historical memory module
        
        Args:
            enable: Whether to enable historical memory (for control experiments)
        """
        self.enable = enable
        self.rounds_data = []  # Store complete data for all rounds
        self.value_evolution = {}  # 🆕 Store value evolution history {agent_id: [evolution_records]}
        
        if self.enable:
            print("[OK] Historical awareness module enabled")
        else:
            print("[DISABLED] Historical awareness module disabled (control group mode)")
    
    def add_round(self, 
                  round_num: int,
                  distribution: Dict[int, Dict[str, float]],
                  evaluations: List[Dict[str, Any]],
                  productions: Dict[int, Dict[str, float]],
                  resources: Dict[str, float]):
        """Add historical data for one round
        
        Args:
            round_num: Round number
            distribution: Distribution results {agent_id: {resource: amount}}
            evaluations: Evaluation results list [{agent_id, fairness_score, evaluation}]
            productions: Production results {agent_id: {resource: amount}}
            resources: Total resources for this round {resource: amount}
        """
        if not self.enable:
            print(f"[DEBUG] add_round: Skipped (not enabled)")
            return  # If not enabled, don't store data
        
        # Deep copy to avoid reference issues
        round_data = {
            "round": round_num,
            "distribution": copy.deepcopy(distribution),
            "evaluations": copy.deepcopy(evaluations),
            "productions": copy.deepcopy(productions),
            "total_resources": copy.deepcopy(resources)
        }
        
        self.rounds_data.append(round_data)
        print(f"[DEBUG] add_round: Round {round_num} data stored, total {len(self.rounds_data)} rounds")
    
    def record_value_evolution(self, agent_id: int, round_number: int, evolution_data: Dict[str, Any]):
        """Record value evolution for an agent (Simplified version)
        
        Design philosophy: Just record the understanding, don't classify whether it evolved.
        
        Args:
            agent_id: Agent ID
            round_number: Round number when evolution occurred
            evolution_data: Dictionary containing evolution information
                - original_value: Original value type
                - fairness_understanding: Complete answer to question 3
                - round: Round number
                - full_response: Full LLM response (optional)
        """
        if not self.enable:
            return
        
        if agent_id not in self.value_evolution:
            self.value_evolution[agent_id] = []
        
        # Simplified record structure
        evolution_record = {
            'round': round_number,
            'original_value': evolution_data.get('original_value', 'unknown'),
            'fairness_understanding': evolution_data.get('fairness_understanding', ''),
            'full_response': evolution_data.get('full_response', '')
        }
        
        self.value_evolution[agent_id].append(evolution_record)
        print(f"[DEBUG] Recorded fairness understanding for agent {agent_id}, round {round_number}")
    
    def get_current_value_understanding(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Get agent's most recent value understanding
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Most recent evolution record, or None if no evolution recorded
        """
        if not self.enable or agent_id not in self.value_evolution or not self.value_evolution[agent_id]:
            return None
        
        # Return most recent evolution record
        return self.value_evolution[agent_id][-1]
    
    def get_value_evolution_history(self, agent_id: int, n_rounds: int = 3) -> List[Dict[str, Any]]:
        """Get agent's value evolution history
        
        Args:
            agent_id: Agent ID
            n_rounds: Number of recent rounds to return
            
        Returns:
            List of evolution records
        """
        if not self.enable or agent_id not in self.value_evolution:
            return []
        
        # Return most recent n records
        return self.value_evolution[agent_id][-n_rounds:] if len(self.value_evolution[agent_id]) >= n_rounds else self.value_evolution[agent_id]
    
    def get_agent_history(self, agent_id: int, n_rounds: int = 3) -> Dict[str, List]:
        """Get historical data for a specific agent
        
        Args:
            agent_id: Agent ID
            n_rounds: Return data for the most recent n rounds
            
        Returns:
            Dictionary containing allocations, satisfactions, productions, and fairness_understandings
        """
        if not self.enable or len(self.rounds_data) == 0:
            return {
                "allocations": [],
                "satisfactions": [],
                "productions": [],
                "fairness_understandings": []
            }
        
        # Get most recent n rounds
        recent_rounds = self.rounds_data[-n_rounds:] if len(self.rounds_data) >= n_rounds else self.rounds_data
        
        allocations = []
        satisfactions = []
        productions = []
        fairness_understandings = []
        
        for round_data in recent_rounds:
            # Extract agent's allocation (grain resource)
            allocation = round_data["distribution"].get(agent_id, {}).get("grain", 0.0)
            allocations.append(allocation)
            
            # Extract agent's satisfaction score and fairness understanding
            satisfaction = None
            understanding = None
            for eval_item in round_data["evaluations"]:
                if eval_item.get("agent_id") == agent_id:
                    satisfaction = eval_item.get("fairness_score")
                    understanding = eval_item.get("fairness_understanding")
                    break
            if satisfaction is not None:
                satisfactions.append(satisfaction)
            if understanding:
                fairness_understandings.append(understanding)
            
            # Extract agent's production amount
            production = round_data["productions"].get(agent_id, {}).get("grain", 0.0)
            productions.append(production)
        
        return {
            "allocations": allocations,
            "satisfactions": satisfactions,
            "productions": productions,
            "fairness_understandings": fairness_understandings
        }
    
    def get_community_history(self, n_rounds: int = 3) -> Dict[str, Any]:
        """Get historical trends for the entire community
        
        Args:
            n_rounds: Return data for the most recent n rounds
            
        Returns:
            Dictionary containing total resources, average satisfaction, and trend analysis
        """
        if not self.enable or len(self.rounds_data) == 0:
            return {
                "total_resources": [],
                "avg_satisfaction": [],
                "trend": "stable"
            }
        
        # Get most recent n rounds
        recent_rounds = self.rounds_data[-n_rounds:] if len(self.rounds_data) >= n_rounds else self.rounds_data
        
        total_resources = []
        avg_satisfactions = []
        
        for round_data in recent_rounds:
            # Extract total resources
            total_res = round_data["total_resources"].get("grain", 0.0)
            total_resources.append(total_res)
            
            # Calculate average satisfaction
            scores = [e.get("fairness_score") for e in round_data["evaluations"] 
                     if e.get("fairness_score") is not None]
            if scores:
                avg_satisfactions.append(sum(scores) / len(scores))
        
        # Analyze trend
        trend = self._analyze_trend(total_resources)
        
        return {
            "total_resources": total_resources,
            "avg_satisfaction": avg_satisfactions,
            "trend": trend
        }
    
    def _analyze_trend(self, values: List[float]) -> str:
        """Analyze trend of a value sequence
        
        Args:
            values: List of values
            
        Returns:
            "rising" | "declining" | "stable"
        """
        if len(values) < 2:
            return "stable"
        
        # Compare recent average with earlier average
        mid_point = len(values) // 2
        recent_avg = sum(values[mid_point:]) / len(values[mid_point:])
        earlier_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else recent_avg
        
        if recent_avg > earlier_avg * 1.05:  # Rising more than 5%
            return "rising"
        elif recent_avg < earlier_avg * 0.95:  # Declining more than 5%
            return "declining"
        else:
            return "stable"
    
    def get_value_context_for_prompt(self, agent_id: int, agent_value_type: str) -> str:
        """Generate past fairness understanding context for LLM prompts (Simplified version)
        
        Design philosophy: Always show past understanding if exists, without judging whether it evolved.
        
        Args:
            agent_id: Agent ID
            agent_value_type: Agent's original value type
            
        Returns:
            Formatted text showing past fairness understanding, empty if no history
        """
        if not self.enable or agent_id not in self.value_evolution:
            return ""
        
        # Get recent history (last 2-3 rounds)
        history = self.value_evolution[agent_id][-3:]  # Show at most 3 rounds
        
        if not history:
            return ""
        
        # Build context
        context = "\n[Your Past Fairness Understanding]\n"
        for record in history:
            round_num = record['round']
            understanding = record.get('fairness_understanding', '')
            
            # Truncate if too long (keep first 250 chars)
            if len(understanding) > 250:
                understanding = understanding[:250] + "..."
            
            context += f"Round {round_num}: \"{understanding}\"\n"
        
        return context
    
    def format_for_prompt(self, agent_id: int, round_number: int) -> str:
        """Generate historical text suitable for inserting into prompt
        
        Args:
            agent_id: Agent ID
            round_number: Current round number
            
        Returns:
            Formatted historical information text
        """
        # 🚫 DISABLED: Historical review in evaluation prompt
        # Return empty string to avoid providing historical data during evaluation
        # Reason: User requested to remove historical review from evaluation
        return ""
        
        # ========== Original implementation (disabled) ==========
        # Uncomment below to re-enable historical review in evaluation
        
        # # Return empty string for round 1 or when disabled
        # if not self.enable or round_number <= 1 or len(self.rounds_data) == 0:
        #     print(f"[DEBUG] format_for_prompt: Returning empty (enable={self.enable}, round={round_number}, data_len={len(self.rounds_data)})")
        #     return ""
        # 
        # print(f"[DEBUG] format_for_prompt: Generating history (agent={agent_id}, round={round_number}, data_len={len(self.rounds_data)})")
        # 
        # # Get historical data
        # agent_hist = self.get_agent_history(agent_id, n_rounds=min(3, round_number - 1))
        # community_hist = self.get_community_history(n_rounds=min(3, round_number - 1))
        # 
        # # Format agent history
        # allocations_str = self._format_list_with_trend(agent_hist["allocations"])
        # satisfactions_str = self._format_list(agent_hist["satisfactions"])
        # productions_str = self._format_list_with_trend(agent_hist["productions"])
        # 
        # # Format community history
        # resources_str = self._format_list_with_trend(community_hist["total_resources"])
        # avg_sat_str = self._format_list(community_hist["avg_satisfaction"])
        # trend_desc = self._get_trend_description(community_hist["trend"])
        # 
        # # Format fairness understanding evolution
        # understanding_history = ""
        # if agent_hist["fairness_understandings"]:
        #     understanding_history = "\nYour Past Fairness Understanding:\n"
        #     start_round = round_number - len(agent_hist["fairness_understandings"])
        #     for i, understanding in enumerate(agent_hist["fairness_understandings"], 1):
        #         # Keep full understanding text (no truncation for better context)
        #         understanding_history += f"  Round {start_round + i}: \"{understanding}\"\n"
        # 
        # # Build historical text
        # historical_text = f"""
        # [📊 Historical Review](Past {len(agent_hist['allocations'])} rounds, for reference)
        # Your Experience:
        # - Allocations: {allocations_str}
        # - Satisfaction: {satisfactions_str}
        # - Your Production: {productions_str}
        # {understanding_history}
        # Community Overall:
        # - Total Resources: {resources_str} {trend_desc}
        # - Average Satisfaction: {avg_sat_str}
        # """
        # 
        # return historical_text
    
    def _format_list(self, values: List[float]) -> str:
        """Format value list as arrow-connected string"""
        if not values:
            return "No data"
        return " → ".join(f"{v:.1f}" for v in values)
    
    def _format_list_with_trend(self, values: List[float]) -> str:
        """Format value list and add trend arrow"""
        if not values:
            return "No data"
        
        base_str = " → ".join(f"{v:.1f}" for v in values)
        
        # Add trend indicator
        if len(values) >= 2:
            change = (values[-1] - values[-2]) / values[-2] if values[-2] != 0 else 0
            if change > 0.1:
                base_str += " ↑"
            elif change < -0.1:
                base_str += " ↓"
            else:
                base_str += " →"
        
        return base_str
    
    def _get_trend_description(self, trend: str) -> str:
        """Get trend description"""
        trend_map = {
            "rising": "(📈 Rising trend)",
            "declining": "(📉 Declining trend)",
            "stable": "(➡️ Relatively stable)"
        }
        return trend_map.get(trend, "")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics of historical memory (for debugging)"""
        return {
            "enabled": self.enable,
            "total_rounds": len(self.rounds_data),
            "memory_size_bytes": len(str(self.rounds_data))
        }


# Test code
if __name__ == "__main__":
    print("="*60)
    print("Historical Memory Module Test")
    print("="*60)
    
    # Create module instance
    memory = HistoricalMemoryModule(enable=True)
    
    # Simulate adding 3 rounds of data
    for round_num in range(1, 4):
        memory.add_round(
            round_num=round_num,
            distribution={
                1: {"grain": 25.0 + round_num},
                2: {"grain": 30.0 - round_num}
            },
            evaluations=[
                {"agent_id": 1, "fairness_score": 3.0 + round_num * 0.5},
                {"agent_id": 2, "fairness_score": 4.0 - round_num * 0.3}
            ],
            productions={
                1: {"grain": 23.0 + round_num},
                2: {"grain": 28.0 - round_num}
            },
            resources={"grain": 250.0 - round_num * 10}
        )
    
    # Test retrieval
    print("\nTest 1: Get agent 1's history")
    agent1_hist = memory.get_agent_history(1, n_rounds=3)
    print(f"Allocations: {agent1_hist['allocations']}")
    print(f"Satisfaction: {agent1_hist['satisfactions']}")
    print(f"Production: {agent1_hist['productions']}")
    
    print("\nTest 2: Get community history")
    community_hist = memory.get_community_history(n_rounds=3)
    print(f"Total resources: {community_hist['total_resources']}")
    print(f"Average satisfaction: {community_hist['avg_satisfaction']}")
    print(f"Trend: {community_hist['trend']}")
    
    print("\nTest 3: Generate prompt text")
    prompt_text = memory.format_for_prompt(agent_id=1, round_number=4)
    print(prompt_text)
    
    print("\nTest 4: Statistics")
    stats = memory.get_stats()
    print(f"Status: {stats}")
    
    print("\n✅ Module test complete!")

