# Agentic Workflows Project (WAT Framework)

This project uses the **WAT architecture** (Workflows, Agents, Tools) to build reliable, scalable AI-powered automation.

## 📁 Project Structure

```
├── workflows/          # Markdown SOPs defining what to do and how
├── tools/              # Python scripts for deterministic execution
├── config/             # Configuration files (style guides, API configs)
├── Brand_Assets/       # Logo, brand guidelines, and design assets
├── .tmp/               # Temporary files (scraped data, intermediates)
├── .env.example        # Template for environment variables
├── .env                # API keys and credentials (NEVER commit)
├── credentials.json    # Google OAuth token (NEVER commit)
└── CLAUDE.md           # AI agent operating instructions
```

## 🎯 Quick Start

1. **Copy `.env.example` to `.env`** and fill in your API keys
   ```bash
   cp .env.example .env
   ```

2. **Create a workflow** in `workflows/` to define your SOP
   - Describe the objective, inputs, tools, and outputs
   - Include error handling steps

3. **Write the tool** in `tools/` as a Python script
   - Import from `.env` for credentials
   - Keep it deterministic and testable

4. **I'll orchestrate** - Read your workflow, call tools in sequence, handle failures

## 🔄 The WAT Loop

```
YOU (define objective)
  ↓
WORKFLOW (I read the SOP)
  ↓
ME (coordinate & decide)
  ↓
TOOLS (Python does the work)
  ↓
RESULTS (cloud services, never local files)
```

## 🛠️ Building Tools

Each tool is a Python script that:
- Takes inputs from CLI arguments or `.env`
- Does ONE thing reliably
- Returns structured output (JSON, CSV, or file path)
- Is testable independently

Example structure:
```python
# tools/example_tool.py
import os
import json
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv("API_KEY")
    # Do work
    print(json.dumps({"status": "success", "data": result}))

if __name__ == "__main__":
    main()
```

## 📝 Writing Workflows

Each workflow is a Markdown file that describes:
- **Objective**: What should happen
- **Inputs**: What data/config is needed
- **Steps**: Which tools to run in order
- **Outputs**: Where results go (usually cloud services)
- **Error Handling**: What to do if steps fail

## 🔐 Security

- **Never commit `.env` or `credentials.json`** - they're in `.gitignore`
- Store API keys only in `.env`
- Regenerate tokens/keys if ever leaked
- Use `.env.example` as a template for new team members

## 📊 Cloud-First Delivery

- Final deliverables: Google Sheets, Docs, Slides (shareable links)
- Intermediate data: `.tmp/` (regenerated as needed)
- Local files: Only for processing, nothing permanent

## 🚀 Ready to Build

Open a workflow or tool and we'll get started. Ask me to:
- "Read the newsletter workflow and let's build it"
- "Create a scraper tool for [website]"
- "Set up a competitive analysis workflow"

Let's build something great! 🎯
