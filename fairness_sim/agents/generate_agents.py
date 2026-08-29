from fairness_sim.llm_client import get_llm_client, get_model_name
import os
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Any

# Setup DeepSeek client
client = get_llm_client()

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT_FILE = PACKAGE_ROOT / "config" / "agents.json"

# Define value types
VALUE_TYPES = {
    "egalitarian": "Egalitarian",
    "needs_based": "Needs-Based", 
    "merit_based": "Merit-Based",
    "altruistic": "Altruistic",
    "pragmatic": "Pragmatic"
}

# Common surnames list (expanded to 60+) - ensures each agent has a unique surname
COMMON_SURNAMES = [
    # English/American surnames (20)
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Anderson", "Taylor", "Thomas", "Moore", "Jackson",
    "Martin", "Lee", "Thompson", "White", "Harris",
    
    # European surnames (20)
    "Wilson", "Clark", "Lewis", "Walker", "Hall",
    "Allen", "Young", "King", "Wright", "Scott",
    "Green", "Baker", "Adams", "Nelson", "Carter",
    "Mitchell", "Roberts", "Turner", "Phillips", "Campbell",
    
    # Additional diverse surnames (20)
    "Parker", "Evans", "Edwards", "Collins", "Stewart",
    "Morris", "Rogers", "Reed", "Cook", "Morgan",
    "Bell", "Murphy", "Bailey", "Rivera", "Cooper",
    "Richardson", "Cox", "Howard", "Ward", "Torres",
    
    # Extra surnames for future expansion (10)
    "Peterson", "Gray", "Ramirez", "James", "Watson",
    "Brooks", "Kelly", "Sanders", "Price", "Bennett"
]

# Value type descriptions
VALUE_DESCRIPTIONS = {
    "egalitarian": "The core of egalitarianism is the belief that all people should be treated equally and receive equal resource allocation, regardless of differences in contribution or need. Egalitarians emphasize equality of outcome rather than equality of opportunity, and are highly sensitive to inequality.",
    
    "needs_based": "Needs-based values hold that resources should be allocated according to individual actual needs. This value system prioritizes meeting basic needs, particularly for vulnerable groups, believing that everyone has the right to obtain basic resources necessary for survival and dignity.",
    
    "merit_based": "Merit-based values hold that resource allocation should reflect individual contribution. This value system emphasizes the principle of more work for more reward, values incentive mechanisms and efficiency, and believes that rewards should be proportional to effort to promote productivity and value creation.",
    
    "altruistic": "Altruistic values manifest in the willingness to sacrifice personal interests to help others, especially those in difficult situations. This value system highly values overall community welfare and harmony, emphasizes mutual help and solidarity, and places collective interests above personal interests.",
    
    "pragmatic": "Pragmatic values seek balanced compromise solutions that consider multiple factors, focusing on long-term system sustainability. This value system flexibly adjusts its stance according to context, caring about both fairness and efficiency, attempting to find optimal practical solutions."
}

def create_agent_prompt(value_type: str, agent_id: int, suggested_surname: str = "") -> str:
    """Create prompt for generating agent
    
    Args:
        value_type: Type of value orientation
        agent_id: Agent ID
        suggested_surname: Suggested surname for the family
        
    Returns:
        Prompt text
    """
    
    value_type_name = VALUE_TYPES[value_type]
    description = VALUE_DESCRIPTIONS[value_type]
    
    surname_suggestion = f"Please use '{suggested_surname}' as the family surname" if suggested_surname else ""
    
    prompt = f"""Based on {value_type_name} values, create a family agent in a community farm. This family should have distinctive characteristics and a background story.

{description}

{surname_suggestion}

Please provide the following information in strict JSON format:

```json
{{
  "id": {agent_id},
  "family_name": "Family surname",
  "value_type": "{value_type}",
  "members": Total family members (integer between 2-8),
  "labor_force": Number of laborers (cannot exceed total members),
  "background": "Brief family background story (100-150 words)",
  
  "core_beliefs": [
    "Core belief 1",
    "Core belief 2",
    "Core belief 3"
  ],
  
  "resource_stance": "Basic stance on resource allocation (50-100 words)",
  "ideal_distribution": "What is considered the ideal distribution method (50-100 words)",
  "fairness_view": "View and understanding of fairness (50-100 words)"
}}
```

Please ensure all generated content is consistent with the fundamental principles of {value_type_name} and reflects authentic family characteristics. Return only JSON format content without any additional explanations or prefixes/suffixes.
"""
    return prompt

def call_openai_api(prompt: str, retries: int = 3) -> Dict[str, Any]:
    """Call OpenAI API to generate agent information
    
    Args:
        prompt: Prompt text
        retries: Number of retry attempts
        
    Returns:
        Agent data dictionary
    """
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": "You are a professional character creation assistant, skilled at creating detailed character descriptions based on specific values. Your responses will strictly follow the required JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Get generated content
            content = response.choices[0].message.content
            
            # Extract JSON part
            json_content = extract_json(content)
            
            # Parse JSON
            agent_data = json.loads(json_content)
            return agent_data
            
        except Exception as e:
            print(f"Attempt {attempt+1}/{retries} failed: {str(e)}")
            if attempt < retries - 1:
                print("Waiting 5 seconds before retry...")
                time.sleep(5)
            else:
                raise Exception(f"Failed to generate agent after maximum retries: {str(e)}")

def extract_json(text: str) -> str:
    """Extract JSON content from text
    
    Args:
        text: Text containing JSON
        
    Returns:
        JSON string
    """
    # Find start and end positions of JSON
    start = text.find("{")
    end = text.rfind("}")
    
    if start == -1 or end == -1:
        raise ValueError("Unable to find valid JSON in response")
    
    return text[start:end+1]

def validate_agent(agent_data: Dict[str, Any]) -> bool:
    """Validate completeness and consistency of agent data
    
    Args:
        agent_data: Agent data dictionary
        
    Returns:
        True if data is valid, False otherwise
    """
    required_fields = [
        "id", "family_name", "value_type", "members", "labor_force", 
        "background", "core_beliefs", "resource_stance", 
        "ideal_distribution", "fairness_view"
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in agent_data:
            print(f"Missing field: {field}")
            return False
    
    # Check numeric household constraints before the cohort is used by the
    # simulation's population and labor-force calculations.
    try:
        members = int(agent_data["members"])
        labor_force = int(agent_data["labor_force"])
    except (TypeError, ValueError):
        print("Members and labor_force must be integers")
        return False
    agent_data["members"] = members
    agent_data["labor_force"] = labor_force

    if members < 1 or labor_force < 0:
        print("Members must be positive and labor_force cannot be negative")
        return False
    
    # Validate labor force doesn't exceed total members
    if labor_force > members:
        print(f"Labor force ({labor_force}) exceeds total members ({members})")
        # Correct labor force number
        agent_data["labor_force"] = members
        print(f"Automatically corrected labor force to {agent_data['labor_force']}")
    
    return True

def generate_agents(agents_per_value: int = 1, start_id: int = 1,
                    surnames_exclude: List[str] = None) -> List[Dict[str, Any]]:
    """Generate a cohort of agents.

    One agent is generated for each value type by default. Increase
    ``agents_per_value`` when a larger synthetic cohort is needed.
    
    Returns:
        List of agent data
    """
    if agents_per_value < 1:
        raise ValueError("agents_per_value must be at least 1")

    agents = []
    used_surnames = set(surnames_exclude or [])  # Track used surnames
    
    # Randomly shuffle surname list
    available_surnames = COMMON_SURNAMES.copy()
    random.shuffle(available_surnames)
    
    current_id = start_id
    for value_type in VALUE_TYPES.keys():
        for _ in range(agents_per_value):
            print(f"Generating {VALUE_TYPES[value_type]} ({value_type}) agent...")

            # Select an unused surname.
            surname = available_surnames.pop(0) if available_surnames else ""

            # Create prompt and call the configured LLM.
            prompt = create_agent_prompt(value_type, current_id, surname)
            agent_data = call_openai_api(prompt)
            agent_data["id"] = current_id
            agent_data["value_type"] = value_type

            # Ensure surname uniqueness.
            if agent_data["family_name"] in used_surnames and available_surnames:
                new_surname = available_surnames.pop(0)
                print(f"Detected duplicate surname '{agent_data['family_name']}', automatically changed to '{new_surname}'")
                agent_data["family_name"] = new_surname

            used_surnames.add(agent_data["family_name"])

            if validate_agent(agent_data):
                agents.append(agent_data)
                print(f"Successfully generated {VALUE_TYPES[value_type]} agent: {agent_data['family_name']} family with {agent_data['members']} members (labor force: {agent_data['labor_force']})")
            else:
                print(f"Generated {VALUE_TYPES[value_type]} agent data failed validation")
            current_id += 1
    
    return agents

def generate_agents_from(start_id: int = 1, surnames_exclude: List[str] = None,
                         agents_per_value: int = 1) -> List[Dict[str, Any]]:
    """Generate an additional cohort starting from the specified ID.
    
    Args:
        start_id: Starting ID (inclusive)
        surnames_exclude: List of already-used surnames to avoid
    Returns:
        List of newly generated agents
    """
    return generate_agents(
        agents_per_value=agents_per_value,
        start_id=start_id,
        surnames_exclude=surnames_exclude,
    )

def save_agents(agents: List[Dict[str, Any]], filename: str = None):
    """Save agents to JSON file
    
    Args:
        agents: List of agent data
        filename: File name
    """
    output_path = Path(filename) if filename else DEFAULT_AGENT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump({"agents": agents}, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved {len(agents)} agents to {output_path}")

def load_agents(filename: str = None) -> List[Dict[str, Any]]:
    """Load agents from file
    
    Args:
        filename: Agent file name
        
    Returns:
        List of agents
    """
    input_path = Path(filename) if filename else DEFAULT_AGENT_FILE
    try:
        with input_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("agents", [])
    except Exception as e:
        print(f"Error loading agents from {input_path}: {str(e)}")
        return []

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic family agents for a simulation.")
    parser.add_argument(
        "--file", default=str(DEFAULT_AGENT_FILE),
        help="Output/append file path (default: fairness_sim/config/agents.json)",
    )
    parser.add_argument(
        "--per-value", type=int, default=1,
        help="Number of agents to generate for each value type (default: 1)",
    )
    parser.add_argument("--append", action="store_true", help="Append a cohort to an existing file")
    args = parser.parse_args()

    try:
        print("Starting community farm agent generation...")
        if args.append and os.path.exists(args.file):
            print(f"Appending to existing file: {args.file}")
            current = load_agents(args.file)
            used = [a.get("family_name", "") for a in current]
            start_id = max((a.get("id", 0) for a in current), default=0) + 1
            extra = generate_agents_from(
                start_id=start_id,
                surnames_exclude=used,
                agents_per_value=args.per_value,
            )
            current.extend(extra)
            save_agents(current, args.file)
        else:
            agents = generate_agents(agents_per_value=args.per_value)
            save_agents(agents, args.file)
        print("Agent generation completed!")
    except Exception as e:
        print(f"Program execution error: {str(e)}")

if __name__ == "__main__":
    main() 
