import os
import requests
import asyncio
from django.conf import settings
from github import Github
import ollama
from base64 import b64decode
import json
import traceback
from asgiref.sync import async_to_sync

# MCP and Agent imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
# Corrected langchain_mcp_adapters import
try:
    from langchain_mcp_adapters.tools import load_mcp_tools
except ImportError:
    # Handle potentially different version or missing package
    load_mcp_tools = None

from langgraph.prebuilt import create_react_agent
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

class Evaluator:
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)

    def evaluate(self, ticket, pr, github_repo, github_pr_number):
        """Simple and reliable evaluation using direct Ollama client."""
        try:
            # Check if model exists
            try:
                models = self.client.list()
                model_list = models.get('models', [])
                # Handle cases where m is a dict with 'name' (older) or 'model' (newer)
                model_names = []
                for m in model_list:
                    if isinstance(m, dict):
                        model_names.append(m.get('name', m.get('model', '')))
                    else:
                        model_names.append(getattr(m, 'model', getattr(m, 'name', '')))

                if self.model not in model_names and f"{self.model}:latest" not in model_names:
                    return json.dumps({
                        "verdict": "Fail",
                        "reasoning": f"Model '{self.model}' not found in Ollama. Available: {', '.join(model_names[:5])}. Please run 'ollama pull {self.model}'.",
                        "evidence": []
                    })
            except Exception as e:
                print(f"Ollama list check failed: {e}")
                # Continue anyway, let the chat call fail if it must

            prompt = f"""
            Analyze if the following GitHub Pull Request satisfies the Jira Ticket requirements.

            JIRA TICKET:
            ID: {ticket['id']}
            Summary: {ticket['summary']}
            Description: {ticket['description']}

            GITHUB PR:
            Repo: {github_repo}
            PR #: {github_pr_number}
            Title: {pr['title']}
            Body: {pr['body']}
            
            FILES CHANGED:
            {self._format_files(pr['files'])}

            Output format (JSON ONLY):
            {{
                "verdict": "Pass" | "Partial" | "Fail",
                "reasoning": "Detailed breakdown of what matched and what did not.",
                "evidence": [
                    {{ "file": "path/to/file", "comment": "description of change found" }}
                ]
            }}
            """
            
            print(f"DEBUG: Using model {self.model}")
            # Decrease timeout or use a simpler call if needed
            response = self.client.chat(
                model=self.model, 
                messages=[
                    {'role': 'system', 'content': 'You are a senior code reviewer. Respond ONLY with valid JSON. Do not include any other text.'},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': 0.1,
                    'num_predict': 500, # Limit output length to prevent hangs
                }
            )
            
            content = response['message']['content']
            # Basic cleanup in case model adds markers
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            print(f"DEBUG: Ollama response: {content[:100]}...")
            return content.strip()

        except Exception as e:
            error_data = traceback.format_exc()
            print(error_data)
            return json.dumps({
                "verdict": "Fail",
                "reasoning": f"System Error: {str(e)}. Check if Ollama is running at {settings.OLLAMA_BASE_URL}",
                "evidence": []
            })

    def _format_files(self, files):
        formatted = ""
        for f in files:
            # Truncate large patches to avoid context overflow
            patch = f['patch'] if f.get('patch') else "No patch data"
            if len(patch) > 2000:
                patch = patch[:2000] + "... (truncated)"
            formatted += f"File: {f['filename']}\nStatus: {f['status']}\nDiff:\n{patch}\n\n"
        return formatted

