# WAT Framework Project

This project follows the **WAT Architecture** (Workflows, Agents, Tools):

- **Workflows** (`workflows/`): Markdown SOPs defining what to do and how
- **Agents** (you): Orchestrate and make intelligent decisions
- **Tools** (`tools/`): Python scripts for deterministic execution

## Project Structure

```
.tmp/              # Temporary/intermediate files (regenerable)
tools/             # Python scripts for execution
workflows/         # Markdown SOPs and instructions
.env               # API keys and credentials (gitignored)
CLAUDE.md          # Agent instructions
```

## Getting Started

1. Read `CLAUDE.md` for the full framework
2. Create workflows in `workflows/` as needed
3. Build tools in `tools/` to execute workflows
4. Set up `.env` with required API keys
