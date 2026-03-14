# Jira Ticket Evaluator

Automating Pull Request Compliance with AI Agents & MCP.

## Key Features (Hackathon Requirements Satisfied)

### 1. 🤖 AI Agent Workflow
Unlike an API script that simply formats strings and sends one API call, this project implements a **LangChain ReAct Agent** (`backend_logic/services.py`). The Agent uses a multi-step loop (Thought -> Action -> Observation) to:
1. Call a Jira tool to understand the ticket contexts and extract discrete acceptance criteria.
2. Formulate a plan mapping each PR change to an acceptance criteria.
3. Arrive at a Pass/Partial/Fail evaluation independently.

### 2. 🔌 True MCP Integration
The evaluator natively connects to the official Anthropic `@modelcontextprotocol/server-github` via STDIO.
- Instead of using a statically typed `PyGithub` API call, the agent uses the **Model Context Protocol** dynamically.
- The standard LangChain MCP adapter loads the GitHub Server's tools (e.g. `get_file_contents`, `search_repositories`), granting the agent autonomous capability to read and retrieve source code on-demand.

### 3. 🧠 Multiple LLM Support (Local + Cloud)
Because of the heavy reasoning required by the agent architecture, you can hot-swap the model based on your `LLM_PROVIDER` environment variable:
- `ollama` (Local Llama3 for free inference)
- `openai` (GPT-4o)
- `gemini` (Google Gemini 1.5 Pro)

---

## Technical Architecture
**Backend:** Django / Django REST Framework
**Agent Orchestration:** LangChain / Langchain MCP Adapters
**MCP Protocol Manager:** Built-in Python `mcp` library

## Setup & Execution

### 1. Environment Configuration
Create a `.env` file containing:
```env
# Required for JIRA tool access
JIRA_TOKEN="your_jira_token"
JIRA_EMAIL="your_jira_email"
JIRA_DOMAIN="your_jira_domain"

# Required for the GitHub MCP Server
GITHUB_TOKEN="your_github_token"

# Optional: LLM Configuration (Default is Ollama)
LLM_PROVIDER="openai" # options: "ollama", "openai", "gemini"
OPENAI_API_KEY="..." # If using openai
GOOGLE_API_KEY="..." # If using gemini
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Note: Ensure you have `Node.js` installed to run the GitHub MCP Server via `npx`)*

### 3. Run the Service
```bash
python manage.py runserver
```

### 4. Test the Endpoint (Example Request)
Send a POST request to the API with your Github Repo and PR info:
```json
// POST /api/evaluate/
{
  "jira_id": "PROJ-123",
  "github_repo": "yourorg/yourrepo",
  "github_pr": "42"
}
```

The system will respond with an evaluated breakdown, proving the agent cross-referenced the PR's codebase with Jira criteria!
