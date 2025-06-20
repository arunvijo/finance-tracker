from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from rest_framework import viewsets, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from .models import Transaction, Budget, Goal, Profile
from .serializers import TransactionSerializer, BudgetSerializer, GoalSerializer
from .utils import generate_upi_link
from django.utils.dateformat import DateFormat
from django.utils.timezone import localtime

# ──────── ViewSets ──────── #

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ──────── Auth APIs ──────── #

class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully 👋")
    return redirect('login')


# ──────── Auth Views ──────── #

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        profile_image = request.FILES.get('profile_image')

        if not username or not password:
            messages.error(request, 'Username and password are required')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists ❌')
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        Token.objects.get_or_create(user=user)

        if profile_image:
            profile = Profile.objects.get(user=user)
            profile.profile_image = profile_image
            profile.save()

        messages.success(request, 'Account created successfully 🎉 Please login.')
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            Token.objects.get_or_create(user=user)
            messages.success(request, f'Welcome back, {user.username} 👋')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password ❌')
            return redirect('login')

    return render(request, 'login.html')


# ──────── HTML Dashboard Views ──────── #


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.timezone import now
from .models import Transaction, Budget, Goal, RecurringExpense

@login_required
def dashboard_view(request):
    user = request.user
    # 1. Recent data for cards
    recent_transactions = Transaction.objects.filter(user=user).order_by('-date_time')[:5]
    recent_budgets = Budget.objects.filter(user=user).order_by('-id')[:5]
    goals = Goal.objects.filter(user=user).order_by('-id')[:5]
    recurring_expenses = RecurringExpense.objects.filter(user=user).order_by('next_due_date')

    # 2. Graph data: last 7 transactions (oldest to newest)
    tx_query = Transaction.objects.filter(user=user).order_by('-date_time')[:7][::-1]
    tx_labels = [tx.date_time.strftime('%d %b') for tx in tx_query]
    tx_amounts = [float(tx.amount) for tx in tx_query]

    # 3. Graph data: current month budgets
    current_month = now().month
    current_year = now().year
    budgets = Budget.objects.filter(user=user, month=current_month, year=current_year)
    budget_labels = [budget.category for budget in budgets]
    budget_amounts = [float(budget.amount) for budget in budgets]

    context = {
        'recent_transactions': recent_transactions,
        'recent_budgets': recent_budgets,
        'goals': goals,
        'recurring_expenses': recurring_expenses,
        'tx_labels': tx_labels,
        'tx_amounts': tx_amounts,
        'budget_labels': budget_labels,
        'budget_amounts': budget_amounts,
    }

    return render(request, 'dashboard.html', context)



@login_required
def transactions_page(request):
    if request.method == 'POST':
        type = request.POST.get('type')
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        description = request.POST.get('description', '')

        if type and amount and category:
            Transaction.objects.create(
                user=request.user,
                type=type,
                amount=amount,
                category=category,
                description=description,
                payment_method='UPI',
                status='Paid',
                is_auto_logged=False
            )
            messages.success(request, 'Transaction added successfully! ✅')
            return redirect('transactions_page')
        else:
            messages.error(request, 'Please fill all required fields.')

    transactions = Transaction.objects.filter(user=request.user).order_by('-date_time')
    return render(request, 'transactions.html', {'transactions': transactions})


@login_required
def budgets_page(request):
    now = timezone.now()

    if request.method == 'POST':
        category = request.POST.get('category')
        amount = request.POST.get('amount')

        if category and amount:
            Budget.objects.create(
                user=request.user,
                category=category,
                amount=amount,
                month=now.month,
                year=now.year
            )
            messages.success(request, 'Budget added successfully! ✅')
            return redirect('budgets_page')
        else:
            messages.error(request, 'Please fill all required fields.')

    budgets = Budget.objects.filter(user=request.user, month=now.month, year=now.year)
    return render(request, 'budgets.html', {'budgets': budgets})


@login_required
def goals_page(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        target_amount = request.POST.get('target_amount')
        deadline = request.POST.get('deadline')

        if title and target_amount and deadline:
            Goal.objects.create(
                user=request.user,
                title=title,
                target_amount=target_amount,
                deadline=deadline
            )
            messages.success(request, 'Goal added successfully! 🎯')
            return redirect('goals_page')
        else:
            messages.error(request, 'Please fill all required fields.')

    goals = Goal.objects.filter(user=request.user).order_by('-id')
    return render(request, 'goals.html', {'goals': goals})


@login_required
def upi_page(request):
    return render(request, 'generate_upi.html')

@login_required
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_upi_page(request):
    if request.method == 'POST':
        upi_id = request.data.get('upi_id')
        name = request.data.get('name')
        amount = request.data.get('amount')
        note = request.data.get('note', '')

        if not all([upi_id, name, amount]):
            return render(request, 'generate_upi.html', {'error': 'Missing required fields'})

        link = generate_upi_link(upi_id, name, amount, note)

        Transaction.objects.create(
            user=request.user,
            type='Expense',
            amount=amount,
            category='Other',
            description=f'Pending GPay to {name}',
            payment_method='UPI',
            is_auto_logged=True,
            status='Pending'
        )

        return render(request, 'generate_upi.html', {'upi_link': link})

    return render(request, 'generate_upi.html')
