### core/models.py
from django.db import models
from django.contrib.auth.models import User

TRANSACTION_TYPES = (
    ('Income', 'Income'),
    ('Expense', 'Expense'),
)

CATEGORIES = (
    ('Food', 'Food'),
    ('Transport', 'Transport'),
    ('Rent', 'Rent'),
    ('Shopping', 'Shopping'),
    ('Health', 'Health'),
    ('Other', 'Other'),
)

STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Paid', 'Paid'),
)

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(choices=TRANSACTION_TYPES, max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(choices=CATEGORIES, max_length=50)
    description = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, default='UPI')
    date_time = models.DateTimeField(auto_now_add=True)
    is_auto_logged = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default='Paid')

    def __str__(self):
        return f'{self.type} - ₹{self.amount} - {self.category}'

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(choices=CATEGORIES, max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.IntegerField()
    year = models.IntegerField()

    def __str__(self):
        return f'{self.user.username} - {self.category} - {self.month}/{self.year}'

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deadline = models.DateField()

    def __str__(self):
        return f'{self.title} - Target: ₹{self.target_amount}'