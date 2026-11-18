# YouTube Analysis Automation

This project uses the **WAT Framework** (Workflows, Agents, Tools) for reliable, scalable automation.

## Project Structure

```
.
├── CLAUDE.md                 # Framework instructions and architecture
├── README.md                 # This file
├── .env                      # API keys and credentials (gitignored)
├── .gitignore               # Git ignore rules
│
├── workflows/               # Markdown SOPs defining what to do
│   └── youtube_analysis_automation.md  # Weekly YouTube analysis SOP
│
├── tools/                   # Python scripts for execution
│   └── example_tool.py      # Sample tool template
│
├── config/                  # Configuration files
│   └── (project configs, style guides, etc.)
│
├── Brand_Assets/            # Brand logos and guidelines
│   └── (logos, style guides, etc.)
│
└── .tmp/                    # Temporary files (regenerated as needed)
    └── (scraped data, intermediate exports, etc.)
```

## How to Get Started

1. **Read the CLAUDE.md** - Understand the WAT framework architecture
2. **Create workflows** in `workflows/` - Define what you want automated
3. **Write tools** in `tools/` - Implement the execution logic
4. **Configure credentials** in `.env` - Add your API keys
5. **Run workflows** - Execute tools through the agent layer

## Key Principles

- **Workflows** are your instructions (what to do)
- **Tools** are deterministic Python scripts (how to do it)
- **Agent** (you) coordinates between intent and execution
- **Cloud services** are your deliverable destination (Google Sheets, Slides, etc.)
- **Local files** are just for processing (disposable after delivery)

## Important Notes

- Never commit `.env` or credential files
- Keep workflows updated as you learn
- Document errors and learnings for continuous improvement
- Leverage existing tools before creating new ones
