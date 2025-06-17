from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth import logout

from .models import Transaction, Budget, Goal
from .serializers import TransactionSerializer, BudgetSerializer, GoalSerializer
from .utils import generate_upi_link, parse_sms_data

from .models import RecurringExpense
from datetime import timedelta


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_upi(request):
    upi_id = request.data.get('upi_id')
    name = request.data.get('name')
    amount = request.data.get('amount')
    note = request.data.get('note', '')

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

    return Response({'upi_link': link})


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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    token = Token.objects.create(user=user)
    return Response({'token': token.key, 'username': user.username})


class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        return Response({'token': token.key, 'username': token.user.username})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    request.user.auth_token.delete()
    logout(request)
    return Response({'success': 'Logged out'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def suggest_budget(request):
    user = request.user
    current_month = timezone.now().month
    current_year = timezone.now().year

    expenses = Transaction.objects.filter(
        user=user, type='Expense',
        date_time__year=current_year,
        date_time__month=current_month
    )

    category_totals = {}
    for tx in expenses:
        category_totals[tx.category] = category_totals.get(tx.category, 0) + float(tx.amount)

    suggestions = []
    for category, total in category_totals.items():
        suggested = round(total * 1.1, 2)  # 10% buffer
        suggestions.append({'category': category, 'suggested_budget': suggested})

    return Response({'suggestions': suggestions})


def detect_recurring(user, merchant, amount):
    similar = Transaction.objects.filter(user=user, description__icontains=merchant).order_by('-date_time')[:3]
    if similar.count() >= 3:
        avg_amount = sum(tx.amount for tx in similar) / len(similar)
        gap = (similar[0].date_time - similar[1].date_time).days
        freq = 'Monthly' if 25 <= gap <= 35 else 'Weekly' if 6 <= gap <= 8 else 'Irregular'
        RecurringExpense.objects.update_or_create(
            user=user, merchant=merchant,
            defaults={'average_amount': avg_amount, 'frequency': freq, 'next_due_date': timezone.now().date() + timedelta(days=gap)}
        )

# Call it in perform_create of TransactionViewSet
def perform_create(self, serializer):
    transaction = serializer.save(user=self.request.user)
    detect_recurring(self.request.user, transaction.description, transaction.amount)
