### core/views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Transaction, Budget, Goal
from .serializers import TransactionSerializer, BudgetSerializer, GoalSerializer
from django.contrib.auth.models import User
from django.utils import timezone
from .utils import generate_upi_link, parse_sms_data
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import logout

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]

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
@permission_classes([permissions.AllowAny])
def sms_parser(request):
    sms_text = request.data.get('sms')
    username = request.data.get('username')

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    parsed = parse_sms_data(sms_text)
    if parsed:
        transaction = Transaction.objects.create(
            user=user,
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
def logout_user(request):
    request.user.auth_token.delete()
    logout(request)
    return Response({'success': 'Logged out'})
