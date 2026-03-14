from django.urls import path
from .views import TicketEvaluatorView, FrontendView

urlpatterns = [
    path('', FrontendView.as_view(), name='index'),
    path('evaluate/', TicketEvaluatorView.as_view(), name='evaluate-ticket'),
]


