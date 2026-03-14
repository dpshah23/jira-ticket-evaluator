import os
import django
import asyncio
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jira_ticket_evaluator.settings')
django.setup()

from backend_logic.services import Evaluator

evaluator = Evaluator()

async def main():
    try:
        ticket = {'id': 'KAN-4', 'summary': 'Add a New login button', 'description': 'Some description'}
        pr = {'title': 'Added Login Button', 'body': 'This PR adds a login button', 'files': []}
        await evaluator.async_evaluate(ticket, pr, 'dpshah23/jira-ticket-evaluator', '1')
    except Exception as e:
        with open('error_debug.txt', 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)

if __name__ == '__main__':
    asyncio.run(main())
