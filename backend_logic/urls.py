from django.urls import path
from .views import TicketEvaluatorView

urlpatterns = [
    path('evaluate/', TicketEvaluatorView.as_view(), name='evaluate-ticket'),
]


