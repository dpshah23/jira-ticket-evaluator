from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import JiraClient, GitHubClient, Evaluator
import json

class TicketEvaluatorView(APIView):
    def post(self, request):
        jira_ticket_id = request.data.get('jira_id')
        github_repo = request.data.get('github_repo') # e.g., 'owner/repo'
        github_pr_number = request.data.get('github_pr')

        if not all([jira_ticket_id, github_repo, github_pr_number]):
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        jira_client = JiraClient()
        github_client = GitHubClient()
        evaluator = Evaluator()

        ticket = jira_client.get_ticket(jira_ticket_id)
        if not ticket:
            return Response({'error': 'Jira ticket not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            pr = github_client.get_pr_details(github_repo, github_pr_number)
        except Exception as e:
            return Response({'error': f'GitHub PR could not be fetched: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)

        evaluation_result = evaluator.evaluate(ticket, pr, github_repo, github_pr_number)
        
        # Try to parse the evaluation result as JSON
        try:
            # Look for JSON block in Ollama'sresponse
            start_index = evaluation_result.find('{')
            end_index = evaluation_result.rfind('}') + 1
            if start_index != -1 and end_index != -1:
                json_part = evaluation_result[start_index:end_index]
                parsed_evaluation = json.loads(json_part)
            else:
                parsed_evaluation = evaluation_result
        except:
            parsed_evaluation = evaluation_result

        return Response({
            'ticket': ticket,
            'pr_summary': {
                'title': pr['title'],
                'files_count': len(pr['files'])
            },
            'evaluation': parsed_evaluation
        })

