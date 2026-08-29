##  When Fairness Evolves: Value Orientation and Evolution in Multi-Agent Resource Allocation

This repository is the source code for our paper: When Fairness Evolves:
Value Orientation and Evolution in Multi-Agent Resource Allocation.

## Allocation Mechanisms

| Mechanism | Description |
|---|---|
| `equal` | Equal distribution across families |
| `llm_needs_based` | Needs-oriented distribution |
| `contribution_based` | Labor-proportional distribution |
| `discussion` | Discussion and progressive-voting negotiation |

## Requirements

Python 3.8 or later is recommended.

```bash
python3 -m pip install -r requirements.txt
```

## LLM Configuration

LLM-backed runs read credentials from environment variables. Credentials are
not stored in the source code.

```bash
export OPENAI_API_KEY=" "
export OPENAI_BASE_URL=" "
export FAIRNESS_MODEL=" "
```

## Agent Profiles

Create `fairness_sim/config/agents.json` before running new simulations. The
expected format is:

```json
{
  "agents": [
    {
      "id": 1,
      "family_name": "Example",
      "value_type": "pragmatic",
      "members": 5,
      "labor_force": 4,
      "background": "...",
      "core_beliefs": ["...", "...", "..."],
      "resource_stance": "...",
      "ideal_distribution": "...",
      "fairness_view": "..."
    }
  ]
}
```

An empty template is provided at `fairness_sim/config/agents.template.json`.

## Run One Condition

```bash
PYTHONPATH=. python3 scripts/run_paper_condition.py \
  --method discussion \
  --rounds 30
```

When `--initial-resource` is omitted, the initial resource pool is derived from
the configured cohort's base survival needs. Use `--resource-multiplier` to
set the resource level, or pass an absolute `--initial-resource` value.

Available methods are `equal`, `llm_needs_based`, `contribution_based`, and
`discussion`.

The default entry point runs a discussion condition:

```bash
PYTHONPATH=. python3 scripts/run_simulation.py
```
