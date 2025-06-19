# views.py (updated)

from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from .models import Transaction, Budget, Goal, RecurringExpense
from .serializers import TransactionSerializer, BudgetSerializer, GoalSerializer
from .utils import generate_upi_link, parse_sms_data


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        transaction = serializer.save(user=self.request.user)
        detect_recurring(self.request.user, transaction.description, transaction.amount)


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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user_api(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    token = Token.objects.create(user=user)
    return Response({'token': token.key, 'username': user.username})


class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    request.user.auth_token.delete()
    logout(request)
    return Response({'success': 'Logged out'})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully \U0001F44B")
    return redirect('login')


# HTML Views

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Username and password are required')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists ❌')
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        Token.objects.get_or_create(user=user)
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
            messages.success(request, f'Welcome back, {user.username} \U0001f44b')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password ❌')
            return redirect('login')

    return render(request, 'login.html')


@login_required
def dashboard_view(request):
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-date_time')[:5]
    recent_budgets = Budget.objects.filter(user=request.user).order_by('-id')[:5]
    goals = Goal.objects.filter(user=request.user).order_by('-id')[:5]
    return render(request, 'dashboard.html', {
        'recent_transactions': recent_transactions,
        'recent_budgets': recent_budgets,
        'goals': goals,
    })

@login_required
def transactions_page(request):
    # Shows all transactions, not just current user's
    transactions = Transaction.objects.all().order_by('-date_time')
    return render(request, 'transactions.html', {'transactions': transactions})



@login_required
def budgets_page(request):
    now = timezone.now()
    budgets = Budget.objects.filter(user=request.user, month=now.month, year=now.year)
    return render(request, 'budgets.html', {'budgets': budgets})


@login_required
def goals_page(request):
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'goals.html', {'goals': goals})

@login_required
def upi_page(request):
    return render(request, 'generate_upi.html')

@login_required
def sms_page(request):
    return render(request, 'sms_parser.html')

from django.contrib.auth.decorators import login_required

@login_required
def health_score_page(request):
    return render(request, 'health.html')

@login_required
def private_mode_page(request):
    return render(request, 'private.html')

@login_required
def voice_transaction_page(request):
    return render(request, 'voice_transaction.html')

@login_required
def scan_bill_page(request):
    return render(request, 'scan_bill.html')









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

        # Save transaction
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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sms_parser(request):
    sms_text = request.data.get('sms')

    parsed = parse_sms_data(sms_text)
    if parsed:
        transaction = Transaction.objects.create(
            user=request.user,
            type='Expense',
            amount=parsed['amount'],
            category=parsed['category'],
            description=parsed['description'],
            payment_method='UPI',
            is_auto_logged=True,
            status=parsed.get('status', 'Paid'),
            date_time=timezone.now()
        )
        return Response(TransactionSerializer(transaction).data)

    return Response({'error': 'Could not parse SMS'}, status=400)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def suggest_budget(request):
    user = request.user
    now = timezone.now()
    expenses = Transaction.objects.filter(
        user=user, type='Expense',
        date_time__year=now.year,
        date_time__month=now.month
    )

    category_totals = {}
    for tx in expenses:
        category_totals[tx.category] = category_totals.get(tx.category, 0) + float(tx.amount)

    suggestions = [
        {'category': cat, 'suggested_budget': round(total * 1.1, 2)}
        for cat, total in category_totals.items()
    ]

    return Response({'suggestions': suggestions})


def detect_recurring(user, merchant, amount):
    similar = Transaction.objects.filter(user=user, description__icontains=merchant).order_by('-date_time')[:3]
    if similar.count() >= 3:
        avg_amount = sum(tx.amount for tx in similar) / len(similar)
        gap = (similar[0].date_time - similar[1].date_time).days
        freq = 'Monthly' if 25 <= gap <= 35 else 'Weekly' if 6 <= gap <= 8 else 'Irregular'
        RecurringExpense.objects.update_or_create(
            user=user, merchant=merchant,
            defaults={
                'average_amount': avg_amount,
                'frequency': freq,
                'next_due_date': timezone.now().date() + timedelta(days=gap)
            }
        )


from django.views.decorators.csrf import csrf_exempt
import random  # For mock score

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def voice_transaction(request):
    transcript = request.data.get('transcript')
    if not transcript:
        return Response({"error": "Transcript missing"}, status=400)

    # Mock response — you can later integrate speech-to-text NLP logic
    Transaction.objects.create(
        user=request.user,
        type='Expense',
        amount=100,  # Placeholder
        category='Voice Entry',
        description=f"Voice log: {transcript}",
        payment_method='Cash',
        is_auto_logged=True
    )

    return Response({"message": "Voice transaction logged", "transcript": transcript})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def scan_bill(request):
    bill_text = request.data.get('bill_text')
    if not bill_text:
        return Response({"error": "Bill text missing"}, status=400)

    # Mock parsing
    Transaction.objects.create(
        user=request.user,
        type='Expense',
        amount=250,  # Placeholder
        category='Bills',
        description=f"Scanned Bill: {bill_text}",
        payment_method='Card',
        is_auto_logged=True
    )

    return Response({"message": "Bill scanned", "bill_text": bill_text})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def financial_health_score(request):
    score = random.randint(50, 95)  # Simulated logic
    return Response({"score": score})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def private_mode_toggle(request):
    # Toggle based on current session
    status = request.session.get('private_mode', False)
    new_status = not status
    request.session['private_mode'] = new_status
    return Response({"private_mode": new_status})
