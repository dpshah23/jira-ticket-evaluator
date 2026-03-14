# AI-Powered Jira & PR Compliance Evaluator
## Professional Product Documentation

### 1. Overview
The **Jira & PR Compliance Evaluator** is an automated software quality assurance tool that bridges the gap between business requirements and technical implementation. By leveraging local Large Language Models (LLMs) via Ollama, the system analyzes GitHub Pull Requests against Jira tickets to ensure that every code change aligns with documented requirements.

---

### 2. Core Features
- **Automated Requirement Mapping:** Automatically fetches and parses Jira ticket descriptions (supporting Atlassian Document Format).
- **Code Diff Analysis:** Retrieves detailed code patches from GitHub PRs using the PyGitHub integration.
- **Privacy-First AI Evaluation:** Uses local inference (Ollama) to perform deep semantic analysis without sending proprietary code to external APIs.
- **Verdict & Evidence System:** Provides a "Pass," "Partial," or "Fail" status accompanied by a detailed reasoning report and file-specific evidence.
- **Interactive Dashboard:** A modern, responsive web interface built with Django and Tailwind CSS.

---

### 3. System Architecture
The application follows a decoupled service-oriented architecture:
- **Frontend:** Django Templates + JavaScript + Tailwind CSS.
- **Backend:** Django REST Framework (Python 3.12).
- **Service Layer:** 
  - `JiraClient`: Manages authentication and ADF-to-text conversion.
  - `GitHubClient`: Handles PR metadata and multi-file patching.
  - `Evaluator`: Orchestrates the local LLM prompt engineering and output parsing.
- **AI Engine:** Ollama (defaulting to `smollm2:1.7b` for memory efficiency).

---

### 4. Technical Requirements
- **Operating System:** Windows, macOS, or Linux.
- **Python Version:** 3.10+ (Current: 3.12).
- **Dependencies:** 
  - Django 4.2+ / 6.0
  - PyGitHub
  - ollama-python
  - python-dotenv
  - django-cors-headers
- **Inference Engine:** [Ollama](https://ollama.com/) must be installed and running locally on port 11434.

---

### 5. Installation & Setup

#### Step 1: Clone and Environment Setup
```powershell
pip install -r requirements.txt
```

#### Step 2: Configuration (.env)
Create a `.env` file in the root directory:
```env
GITHUB_TOKEN="your_github_token"
JIRA_TOKEN="your_jira_token"
JIRA_EMAIL="your_email@domain.com"
JIRA_DOMAIN="your_jira_domain"
OLLAMA_MODEL="smollm2:1.7b-instruct-q4_K_M"
OLLAMA_BASE_URL="http://localhost:11434"
```

#### Step 3: Run the Server
```powershell
python manage.py migrate
python manage.py runserver
```

---

### 6. User Guide
1. Launch the dashboard at `http://localhost:8000`.
2. **Jira ID:** Enter the ticket key (e.g., `PROJ-123`).
3. **GitHub Repository:** Enter the full owner/repo name (e.g., `dpshah23/jira-ticket-evaluator`).
4. **PR Number:** Enter the numeric ID of the pull request.
5. Click **Run Evaluation** and wait for the AI to process the requirements.

---

### 7. Evaluation Logic (Verdicts)
- **✅ Pass:** All Jira requirements are clearly addressed in the PR patches.
- **⚠️ Partial:** Some requirements are met, but others are missing or only partially implemented.
- **❌ Fail:** The code changes do not address the core requirements or have major deviations.

---

### 8. Security & Privacy
- **No Data Leakage:** All code and ticket content remain within the local network. 
- **Token Management:** Uses secure environment variables for API access.
- **Audit Ready:** Since logic is handled by local LLMs, organizations can audit the prompts used for evaluation.

---

### 9. Maintenance & Troubleshooting
- **Memory Errors:** If the system fails with a 500 Memory Error, ensure heavy models like Llama3 are stopped (`ollama stop llama3`).
- **Connection Errors:** Verify Ollama is running by visiting `http://localhost:11434` in your browser.
- **API Limits:** Ensure your GitHub and Jira tokens have appropriate permissions (read-only is sufficient).
