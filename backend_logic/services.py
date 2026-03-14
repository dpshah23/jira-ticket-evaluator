import os
import requests
from django.conf import settings
from github import Github
import ollama
from base64 import b64decode
import json

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

    def evaluate(self, ticket, pr):
        prompt = f"""
        Analyze if the following GitHub Pull Request (PR) satisfies the requirements of the Jira Ticket.

        JIRA TICKET:
        ID: {ticket['id']}
        Summary: {ticket['summary']}
        Description: {ticket['description']}

        GITHUB PULL REQUEST:
        Title: {pr['title']}
        Description: {pr['body']}
        
        Files Changed:
        {self._format_files(pr['files'])}

        Evaluation Criteria:
        1. Does the code implementation match the ticket requirements?
        2. Are there any missing features or unaddressed bugs mentioned in the ticket?
        3. Is the implementation logic sound based on the description?

        Please provide your response in the following JSON format:
        {{
            "verdict": "Pass" | "Partial" | "Fail",
            "reasoning": "Detailed explanation of the verdict",
            "evidence": [
                {{
                    "file": "filename",
                    "comment": "how it relates to the requirement"
                }}
            ]
        }}
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': 'You are an expert senior software engineer and code reviewer.'},
                {'role': 'user', 'content': prompt}
            ])
            return response['message']['content']
        except Exception as e:
            error_msg = str(e)
            if "CUDA" in error_msg or "terminated" in error_msg:
                return json.dumps({
                    "verdict": "Fail",
                    "reasoning": f"LLM Error: The Ollama runner failed (likely GPU/CUDA issue). Please ensure Ollama is running correctly. Technical detail: {error_msg}",
                    "evidence": []
                })
            return str(e)

    def _format_files(self, files):
        formatted = ""
        for f in files:
            formatted += f"File: {f['filename']}\nStatus: {f['status']}\nPatch:\n{f['patch']}\n\n"
        return formatted
