### core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, BudgetViewSet, GoalViewSet, generate_upi, sms_parser, register_user, CustomLoginView, logout_user

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'budgets', BudgetViewSet, basename='budgets')
router.register(r'goals', GoalViewSet, basename='goals')

urlpatterns = [
    path('', include(router.urls)),
    path('generate-upi-link/', generate_upi),
    path('sms-parser/', sms_parser),
    path('register/', register_user),
    path('login/', CustomLoginView.as_view()),
    path('logout/', logout_user),
    path('suggest-budget/', suggest_budget),

]