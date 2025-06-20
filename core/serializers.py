from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User

class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username') 

    class Meta:
        model = Transaction
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')  

    class Meta:
        model = Budget
        fields = '__all__'

class GoalSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username') 

    class Meta:
        model = Goal
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(source='profile.profile_image', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile_image']


class RecurringExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringExpense
        fields = '__all__'
        read_only_fields = ['user', 'last_detected']

