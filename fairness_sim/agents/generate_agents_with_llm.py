"""
Use LLM to generate diverse and realistic agents
"""
from fairness_sim.llm_client import get_llm_client, get_model_name
import json
import random
import time
from pathlib import Path

DEFAULT_AGENT_FILE = Path(__file__).resolve().parents[1] / "config" / "agents.json"

# APIConfiguration
MODEL = get_model_name()

# Initialize Client
client = get_llm_client()

# Value Type
VALUE_TYPES = ["egalitarian", "needs_based", "merit_based", "altruistic", "pragmatic"]

# Last name pool
FAMILY_NAMES = [
    "Anderson", "Taylor", "Thomas", "Moore", "Jackson",
    "Martin", "Lee", "Thompson", "White", "Harris",
    "Clark", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres",
    "Nguyen", "Hill", "Flores", "Green", "Adams",
    "Nelson", "Baker", "Hall", "Rivera", "Campbell"
]


def generate_agent_with_llm(agent_id: int, family_name: str, value_type: str, members: int, labor_force: int) -> dict:
    """
    Use LLM to generate a realistic and diverse agent
    
    Args:
        agent_id: Agent ID
        family_name: Family name
        value_type: Value type
        members: Number of family members
        labor_force: Number of labor force
        
    Returns:
        Agent dictionary
    """
    
    # Values description
    value_descriptions = {
        "egalitarian": "believes in absolute equality - everyone should receive the same resources regardless of their contribution or needs",
        "needs_based": "believes resources should be allocated based on individual needs - those who need more should receive more",
        "merit_based": "believes resources should be allocated based on contribution and effort - those who work harder should receive more",
        "altruistic": "believes in helping others and collective welfare - willing to sacrifice personal gain for community benefit",
        "pragmatic": "believes in practical solutions that balance different interests - flexible and adaptable to changing circumstances"
    }
    
    prompt = f"""You are creating a diverse family character for a community farm simulation. Generate a realistic family profile with the following constraints:

**Required Information:**
- Family Name: {family_name}
- Value Type: {value_type} ({value_descriptions[value_type]})
- Number of Members: {members}
- Labor Force: {labor_force}

**Generate the following fields in JSON format:**

1. **background** (150-200 words): A rich, realistic family history including:
   - How they came to the community farm
   - Their past experiences that shaped their values
   - Their role and reputation in the community
   - Specific details that make them unique and memorable

2. **core_beliefs** (array of 3 strings): Three specific, concrete beliefs that reflect their {value_type} worldview. Make them distinctive and actionable.

3. **resource_stance** (2-3 sentences): Their specific position on how community resources should be managed and distributed.

4. **ideal_distribution** (2-3 sentences): Their preferred method for allocating resources in the community.

5. **fairness_view** (2-3 sentences): Their philosophical view on what constitutes fairness and justice.

**Important Guidelines:**
- Make the family unique and memorable with specific details
- Ensure all content strongly reflects the {value_type} value type
- Use realistic, human language - avoid clichés
- Create internal consistency across all fields
- Make them feel like real people with real motivations

**Output Format:**
Return ONLY a valid JSON object with these exact keys: background, core_beliefs, resource_stance, ideal_distribution, fairness_view

Example structure:
{{
  "background": "...",
  "core_beliefs": ["...", "...", "..."],
  "resource_stance": "...",
  "ideal_distribution": "...",
  "fairness_view": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative writer specializing in character development. Generate realistic, diverse, and internally consistent family profiles in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.9,  # High temperatures to increase diversity
            max_tokens=800
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extractJSON(May bemarkdownPackage)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # InsightsJSON
        agent_data = json.loads(content)
        
        # Build a completeagentObject
        agent = {
            "id": agent_id,
            "family_name": family_name,
            "value_type": value_type,
            "members": members,
            "labor_force": labor_force,
            "background": agent_data["background"],
            "core_beliefs": agent_data["core_beliefs"],
            "resource_stance": agent_data["resource_stance"],
            "ideal_distribution": agent_data["ideal_distribution"],
            "fairness_view": agent_data["fairness_view"]
        }
        
        return agent
        
    except Exception as e:
        print(f"❌ Generateagent {agent_id} Failed: {e}")
        print(f"Response Content: {content if 'content' in locals() else 'No response'}")
        return None


def load_existing_agents(filepath: str = None) -> dict:
    """Load existing agents from file"""
    filepath = Path(filepath) if filepath else DEFAULT_AGENT_FILE
    try:
        with filepath.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"agents": []}


def save_agents(agents_data: dict, filepath: str = None):
    """Save agents to file"""
    filepath = Path(filepath) if filepath else DEFAULT_AGENT_FILE
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open('w', encoding='utf-8') as f:
        json.dump(agents_data, f, indent=2, ensure_ascii=False)


def main():
    """Main function"""
    print("=" * 80)
    print("LLM Agent Generator")
    print("=" * 80)
    
    # Load Existingagents
    agents_data = load_existing_agents()
    existing_agents = agents_data.get("agents", [])
    
    print(f"\nCurrently existing {len(existing_agents)} Pieceagents")
    
    # Get Used Last Name and MaxID
    used_names = [agent["family_name"] for agent in existing_agents]
    max_id = max([agent["id"] for agent in existing_agents]) if existing_agents else 0
    
    # Ask how many new ones to generateagents
    while True:
        try:
            count = int(input(f"\nHow many new ones to generateagents? (Available Last Name Count: {len(FAMILY_NAMES) - len(used_names)}): "))
            if count <= 0:
                print("Quantity must be greater than0")
                continue
            if count > len(FAMILY_NAMES) - len(used_names):
                print(f"Insufficient Last Name Pool!Up to can be generated {len(FAMILY_NAMES) - len(used_names)} Piece")
                continue
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Available Last Name Pools
    available_names = [name for name in FAMILY_NAMES if name not in used_names]
    
    # Balanced Distribution Value Type
    value_distribution = []
    for i in range(count):
        value_type = VALUE_TYPES[i % len(VALUE_TYPES)]
        value_distribution.append(value_type)
    
    # Shuffle order
    random.shuffle(value_distribution)
    
    # Randomly select last name
    selected_names = random.sample(available_names, count)
    
    print(f"\nGet startedLLMGenerate {count} Pieceagents...")
    print("⚠️  This may take a while,Please be patient...\n")
    
    new_agents = []
    failed_count = 0
    
    for i in range(count):
        agent_id = max_id + i + 1
        family_name = selected_names[i]
        value_type = value_distribution[i]
        members = random.randint(5, 8)
        labor_force = random.randint(3, min(5, members - 1))
        
        print(f"[{i+1}/{count}] Generating {family_name} ({value_type})...", end=" ")
        
        agent = generate_agent_with_llm(agent_id, family_name, value_type, members, labor_force)
        
        if agent:
            new_agents.append(agent)
            print("✓")
        else:
            failed_count += 1
            print("✗")
        
        # AvoidAPICurrent limiting,Interval1Seconds
        if i < count - 1:
            time.sleep(1)
    
    print(f"\nBuild Complete!Success: {len(new_agents)}/{count}, Failed: {failed_count}")
    
    if not new_agents:
        print("\nNo Successfully Generatedagents")
        return
    
    # Show generatedagentsInformation
    print("\nGeneratedagents:")
    print("-" * 80)
    value_counts = {}
    for agent in new_agents:
        print(f"ID {agent['id']:2d}: {agent['family_name']:12s} | "
              f"{agent['value_type']:15s} | "
              f"Member:{agent['members']} Workforce:{agent['labor_force']}")
        value_counts[agent['value_type']] = value_counts.get(agent['value_type'], 0) + 1
    
    print("\nNew Values Distribution:")
    for value_type in VALUE_TYPES:
        count_val = value_counts.get(value_type, 0)
        print(f"  {value_type:15s}: {count_val}")
    
    # Show an exampleagent
    if new_agents:
        print("\n" + "=" * 80)
        print("ExampleAgent:")
        print("=" * 80)
        sample = new_agents[0]
        print(f"\nID: {sample['id']}")
        print(f"Family: {sample['family_name']}")
        print(f"Value Type: {sample['value_type']}")
        print(f"Members: {sample['members']}, Labor Force: {sample['labor_force']}")
        print(f"\nBackground:\n{sample['background']}")
        print(f"\nCore Beliefs:")
        for belief in sample['core_beliefs']:
            print(f"  - {belief}")
        print(f"\nResource Stance:\n{sample['resource_stance']}")
    
    # Ask if you want to save
    response = input(f"\nDo you want to {len(new_agents)} NewagentsAdd to agents.json? (y/n): ")
    
    if response.lower() == 'y':
        # Mergeagents
        agents_data["agents"] = existing_agents + new_agents
        
        # Save to file
        save_agents(agents_data)
        
        print(f"\n✓ Saved!agents.json Now contains {len(agents_data['agents'])} Pieceagents")
        
        # Updated Total Value Distribution
        all_value_counts = {}
        for agent in agents_data["agents"]:
            vtype = agent["value_type"]
            all_value_counts[vtype] = all_value_counts.get(vtype, 0) + 1
        
        print("\nOverall Values Distribution:")
        for value_type in VALUE_TYPES:
            count_val = all_value_counts.get(value_type, 0)
            print(f"  {value_type:15s}: {count_val}")
    else:
        print("\nSaved canceled")


if __name__ == "__main__":
    main()
