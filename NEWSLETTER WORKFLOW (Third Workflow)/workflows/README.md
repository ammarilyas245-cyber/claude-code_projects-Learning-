# Workflows

This directory contains Markdown SOPs (Standard Operating Procedures) that define:
- **Objective**: What the workflow accomplishes
- **Inputs**: What data or parameters are required
- **Tools**: Which scripts from `tools/` to use
- **Steps**: The exact sequence of actions
- **Outputs**: What gets delivered
- **Edge Cases**: How to handle failures

Each workflow is a complete instruction set that can be executed by the agent.

## Creating a Workflow

Use this template:

```markdown
# Workflow Name

## Objective
What this workflow accomplishes.

## Inputs
- Parameter 1 (type): Description
- Parameter 2 (type): Description

## Tools
- `tools/script_name.py`: What it does

## Steps
1. First step
2. Second step
3. Third step

## Outputs
- Output 1: Where it goes
- Output 2: Format and location

## Edge Cases
- If X happens, do Y
- If Z fails, retry with W
```
