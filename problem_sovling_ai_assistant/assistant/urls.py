from django.urls import path
from .views import ProblemCardCreateView

urlpatterns = [
    path('', ProblemCardCreateView.as_view(), name='home'),
]
