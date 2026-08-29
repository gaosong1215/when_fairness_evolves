"""
Calculate statistics from agents.json
"""
import json
from pathlib import Path

# Load the generated package configuration regardless of the current directory.
agents_path = Path(__file__).resolve().parents[1] / "config" / "agents.json"
if not agents_path.exists():
    raise SystemExit(
        "No generated agents found. Run "
        "python3 -m fairness_sim.agents.generate_agents first."
    )
with agents_path.open('r', encoding='utf-8') as f:
    data = json.load(f)

agents = data['agents']
if not agents:
    raise SystemExit(
        "The generated agent file is empty. Run "
        "python3 -m fairness_sim.agents.generate_agents first."
    )

print("=" * 80)
print("Agents Statistics")
print("=" * 80)

# Calculate totals
total_agents = len(agents)
total_members = sum(agent['members'] for agent in agents)
total_labor_force = sum(agent['labor_force'] for agent in agents)
total_non_labor = total_members - total_labor_force

print(f"\nBasic Statistics:")
print(f"  Number of households: {total_agents}")
print(f"  Total population: {total_members}")
print(f"  Total Workforce: {total_labor_force}")
print(f"  Non-labor: {total_non_labor}")

# Calculate base survival needs
# Labor force: 2 units per person
# Non-labor: 1 unit per person
labor_needs = total_labor_force * 2
non_labor_needs = total_non_labor * 1
base_needs = labor_needs + non_labor_needs

print(f"\nSurvival Consumption Calculation:")
print(f"  Labor consumption: {total_labor_force} × 2 = {labor_needs}")
print(f"  Non-labor consumption: {total_non_labor} × 1 = {non_labor_needs}")
print(f"  Base Total Demand: {base_needs}")

# Calculate resources for different alpha levels
print(f"\nResource totals at different alpha levels:")
print(f"  {'α':>6} | {'Total resources':>10} | {'Environment description'}")
print("-" * 50)

alpha_levels = [
    (2.0, "Scarcity(Base Consumption)"),
    (2.2, "Moderate(Base Consumption)"),
    (2.4, "Abundance(Consumption Escalation Threshold)")
]

for alpha, desc in alpha_levels:
    resources = alpha * base_needs
    print(f"  {alpha:6.1f} | {resources:10.0f} | {desc}")

# Calculate per-family statistics
print(f"\nAverage Household Statistics:")
avg_members = total_members / total_agents
avg_labor = total_labor_force / total_agents
avg_needs = base_needs / total_agents

print(f"  Average number of members: {avg_members:.2f}")
print(f"  Average workforce: {avg_labor:.2f}")
print(f"  Average Demand: {avg_needs:.2f}")

# Value type distribution
value_counts = {}
for agent in agents:
    vtype = agent['value_type']
    value_counts[vtype] = value_counts.get(vtype, 0) + 1

print(f"\nValues Distribution:")
for vtype, count in sorted(value_counts.items()):
    pct = count / total_agents * 100
    print(f"  {vtype:15s}: {count:2d} ({pct:5.1f}%)")

# Detailed breakdown by family
print(f"\n" + "=" * 80)
print("Detailed family list")
print("=" * 80)
print(f"{'ID':>3} | {'Family':12s} | {'Values':15s} | {'Member':>4} | {'Labor':>4} | {'Demand':>6}")
print("-" * 80)

for agent in agents:
    agent_needs = agent['labor_force'] * 2 + (agent['members'] - agent['labor_force']) * 1
    print(f"{agent['id']:3d} | {agent['family_name']:12s} | {agent['value_type']:15s} | "
          f"{agent['members']:4d} | {agent['labor_force']:4d} | {agent_needs:6.0f}")

print("\n" + "=" * 80)
print("Important")
print("=" * 80)
print(f"""
Based on current {total_agents} configurations for families:

1. Basic survival needs = {base_needs} Unit
   
2. Suggested Initial Resource Allocation:
   - Scarce Environment (α=2.0): {base_needs * 2.0:.0f} Unit
   - Moderate environment (α=2.2): {base_needs * 2.2:.0f} Unit  
   - Enriching environment (α=2.4): {base_needs * 2.4:.0f} Unit
   
3. Consumption mechanism(Current Settings):
   - α <= 2.4: Base Consumption (c=1.0) → Actual consumption = {base_needs}
   - 2.4 < α <= 3.0: Moderate escalation (c=1.0~1.3)
   - α > 3.0: Accelerated upgrades (c>1.3)
   
4. Expected equilibrium:
   - All environments will eventually trend α≈5.0
   - Stable resources approx. {base_needs * 5.0:.0f} Unit
""")




