import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

DEFAULT_AGENT_FILE = Path(__file__).resolve().parents[1] / "config" / "agents.json"

class AgentManager:
    """Agent manager for loading and accessing agent data"""
    
    def __init__(self, agent_file: str = None):
        """Initialize agent manager
        
        Args:
            agent_file: Path to JSON file containing agent information
        """
        if agent_file is None:
            agent_file = str(DEFAULT_AGENT_FILE)
        elif not os.path.isabs(agent_file):
            agent_file = str(Path.cwd() / agent_file)
        
        self.agents = self._load_agents(agent_file)
        self.agent_by_id = {agent["id"]: agent for agent in self.agents}
        self.agent_by_value_type = self._group_by_value_type()
    
    def _load_agents(self, agent_file: str) -> List[Dict[str, Any]]:
        """Load agents from file"""
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("agents", [])
        except Exception as e:
            print(f"Failed to load agent file: {str(e)}")
            return []
    
    def _group_by_value_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group agents by value type"""
        result = {}
        for agent in self.agents:
            value_type = agent["value_type"]
            if value_type not in result:
                result[value_type] = []
            result[value_type].append(agent)
        return result
    
    def get_agent(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Get agent by ID"""
        return self.agent_by_id.get(agent_id)
    
    def get_agents_by_value_type(self, value_type: str) -> List[Dict[str, Any]]:
        """Get agents by value type"""
        return self.agent_by_value_type.get(value_type, [])
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents"""
        return self.agents
    
    def print_agent_list(self):
        """Print a concise list of all agents"""
        print("\n" + "="*70)
        print("AGENT LIST")
        print("="*70)
        print(f"Total agents: {len(self.agents)}\n")
        
        # Header
        print(f"{'ID':<4} {'Family Name':<15} {'Value Type':<18} {'Members':<8} {'Labor':<6}")
        print("-"*70)
        
        # Agent rows
        for agent in self.agents:
            print(f"{agent['id']:<4} {agent['family_name']:<15} {agent['value_type']:<18} {agent['members']:<8} {agent['labor_force']:<6}")
        
        print("="*70)
        
        # Value type statistics
        print("\nValue Type Distribution:")
        print("-"*40)
        value_counts = {}
        for agent in self.agents:
            vtype = agent['value_type']
            if vtype not in value_counts:
                value_counts[vtype] = []
            value_counts[vtype].append(agent['family_name'])
        
        for vtype, families in sorted(value_counts.items()):
            family_str = ", ".join(families)
            print(f"  {vtype:<18}: {len(families)} agents ({family_str})")
        print("="*70 + "\n")
    
    def print_agent_summary(self, agent_id: int = None):
        """Print agent summary
        
        If agent_id is not specified, prints summary of all agents
        """
        agents_to_print = [self.get_agent(agent_id)] if agent_id else self.agents
        
        for agent in agents_to_print:
            if agent:
                print("\n" + "="*50)
                print(f"Family ID: {agent['id']}")
                print(f"Family Name: {agent['family_name']}")
                print(f"Value Type: {agent['value_type']}")
                print(f"Members: {agent['members']} (Labor Force: {agent['labor_force']})")
                print(f"Background: {agent['background']}")
                
                print("\nCore Beliefs:")
                for belief in agent['core_beliefs']:
                    print(f"- {belief}")
                    
                print(f"\nResource Stance: {agent['resource_stance']}")
                print(f"Ideal Distribution: {agent['ideal_distribution']}")
                
                if 'fairness_view' in agent:
                    print(f"Fairness View: {agent['fairness_view']}")
                
                print("="*50)

# Example usage
if __name__ == "__main__":
    manager = AgentManager()
    
    # Print concise agent list
    manager.print_agent_list()
    
    # Uncomment to see detailed summary of all agents
    # manager.print_agent_summary()
    
    # Example: Get agents by value type
    print("\nExample: Querying egalitarian agents...")
    egalitarian_agents = manager.get_agents_by_value_type("egalitarian")
    if egalitarian_agents:
        print("Egalitarian Families:")
        for agent in egalitarian_agents:
            print(f"  - {agent['family_name']} family (ID: {agent['id']}, Members: {agent['members']})")
    
    # Example: Get specific agent
    print("\nExample: Querying specific agent (ID=1)...")
    agent = manager.get_agent(1)
    if agent:
        print(f"  {agent['family_name']} family: {agent['value_type']}")
        print(f"  Background: {agent['background'][:100]}...") 
