import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jira_ticket_evaluator.settings')
django.setup()

from backend_logic.services import Evaluator

evaluator = Evaluator()

try:
    ticket = {'id': 'KAN-4', 'summary': 'Add a New login button', 'description': 'Some description'}
    pr = {'title': 'Added Login Button', 'body': 'This PR adds a login button', 'files': []}
    result = evaluator.evaluate(ticket, pr, 'dpshah23/jira-ticket-evaluator', '1')
    print("RESULT:", result)
except Exception as e:
    print("EXCEPTION CAUGHT:")
    traceback.print_exc()
