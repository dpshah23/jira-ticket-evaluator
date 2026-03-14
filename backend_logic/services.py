import os
import requests
import asyncio
from django.conf import settings
from github import Github
import ollama
from base64 import b64decode
import json
from asgiref.sync import async_to_sync

# MCP and Agent imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import initialize_agent, AgentType
from langchain_core.tools import tool

class JiraClient:
    def __init__(self):
        self.token = settings.JIRA_TOKEN
        self.email = settings.JIRA_EMAIL
        self.domain = settings.JIRA_DOMAIN
        self.base_url = f"https://{self.domain}.atlassian.net/rest/api/3"
        self.auth = (self.email, self.token)

    def get_ticket(self, ticket_id):
        url = f"{self.base_url}/issue/{ticket_id}"
        response = requests.get(url, auth=self.auth)
        if response.status_code == 200:
            data = response.json()
            return {
                'id': data['key'],
                'summary': data['fields']['summary'],
                'description': self._parse_description(data['fields'].get('description')),
                'status': data['fields']['status']['name']
            }
        return None

    def _parse_description(self, description_doc):
        if not description_doc:
            return ""
        # Jira uses Atlassian Document Format (ADF) in v3 API
        text_parts = []
        if isinstance(description_doc, dict) and 'content' in description_doc:
            for content in description_doc['content']:
                if 'content' in content:
                    for inner in content['content']:
                        if inner.get('type') == 'text':
                            text_parts.append(inner.get('text', ''))
        return " ".join(text_parts)

class GitHubClient:
    def __init__(self):
        self.g = Github(settings.GITHUB_TOKEN)

    def get_pr_details(self, repo_full_name, pr_number):
        repo = self.g.get_repo(repo_full_name)
        pr = repo.get_pull(int(pr_number))
        
        files = []
        for file in pr.get_files():
            files.append({
                'filename': file.filename,
                'status': file.status,
                'patch': file.patch,
                'additions': file.additions,
                'deletions': file.deletions
            })

        return {
            'title': pr.title,
            'body': pr.body,
            'files': files,
            'diff_url': pr.diff_url
        }

@tool
def get_jira_ticket_tool(ticket_id: str) -> str:
    """Fetch a Jira ticket by ID to read its summary and description."""
    client = JiraClient()
    return json.dumps(client.get_ticket(ticket_id))

class Evaluator:
    def __init__(self):
        # Allow falling back to another provider via settings (or environment variable directly if not in settings)
        provider = os.getenv("LLM_PROVIDER", "ollama")
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            # Expecting OPENAI_API_KEY to be set
            self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Expecting GOOGLE_API_KEY to be set
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
        else:
            from langchain_community.chat_models import ChatOllama
            self.llm = ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.1)

    async def async_evaluate(self, ticket, pr, github_repo, github_pr_number):
        github_token = settings.GITHUB_TOKEN
        # Ensure we find npx on Windows
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        server_parameters = StdioServerParameters(
            command=npx_cmd,
            args=["-y", "@modelcontextprotocol/server-github"],
            env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": github_token}
        )

        async with stdio_client(server_parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Load MCP tools provided by the Github MCP server
                github_tools = await load_mcp_tools(session)
                
                # Combine MCP tools with custom Jira tool
                tools = github_tools + [get_jira_ticket_tool]

                # Create the agent
                agent = initialize_agent(
                    tools, 
                    self.llm, 
                    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
                    verbose=True,
                    handle_parsing_errors=True
                )

                prompt = f"""
                You are an expert AI software engineer. Your task is to evaluate a GitHub PR against its corresponding Jira ticket.
                Follow these exact steps:
                1. You may use the Jira tool to fetch more contexts if needed about ticket ID: {ticket['id']}.
                   Ticket Summary: {ticket['summary']}
                   Ticket Description: {ticket['description']}
                2. IMPORTANT: Use the github tools to fetch files changed in PR #{github_pr_number} in repo {github_repo}. 
                   Read the code modifications carefully.
                   Here is the title and description of the PR as context: {pr['title']} - {pr['body']}
                3. Evaluate whether the PR fulfills each requirement stated in the ticket description.
                4. Produce a final structured JSON output EXACTLY matching this schema:
                {{
                    "verdict": "Pass" | "Partial" | "Fail",
                    "reasoning": "Detailed explanation...",
                    "evidence": [
                        {{
                            "file": "filename",
                            "comment": "how it relates"
                        }}
                    ]
                }}
                Do not output any introductory or conversational text, ONLY raw JSON in the final answer.
                """
                
                response = agent.run(prompt)
                return response

    def evaluate(self, ticket, pr, github_repo, github_pr_number):
        try:
            return async_to_sync(self.async_evaluate)(ticket, pr, github_repo, github_pr_number)
        except Exception as e:
            error_msg = str(e)
            return json.dumps({
                "verdict": "Fail",
                "reasoning": f"Agent or MCP Exception: {error_msg}",
                "evidence": []
            })

