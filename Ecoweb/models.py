from django.conf import settings
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from decimal import Decimal

SHOE_SIZES = (
    ('seven', '7'),
    ('eight', '8'),
    ('nine', '9'),
    ('ten', '10'),
    ('eleven', '11'),
    ('twelve', '12'),
    ('thirteen', '13'),
    ('fourteen', '14'),

)

PAYMENT_STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('COMPLETED', 'Completed'),
    ('FAILED', 'Failed'),
    ('CANCELLED', 'Cancelled'),
)

MPESA_TRANSACTION_STATUS = (
    ('PENDING', 'Pending'),
    ('SUCCESS', 'Success'),
    ('FAILED', 'Failed'),
    ('CANCELLED', 'Cancelled'),
)


class Item(models.Model):
    title = models.CharField(max_length=200)
    price = models.FloatField()
    photo = models.ImageField(upload_to='pics')
    shoe_size = models.CharField(choices=SHOE_SIZES, max_length=15, null=True)
    slug = models.SlugField()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("detail", kwargs={'slug': self.slug})

    def get_add_cart_url(self):
        return reverse("add-to-cart", kwargs={'slug': self.slug})

    def get_remove_from_cart_url(self):
        return reverse("remove-from-cart", kwargs={'slug': self.slug})


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField(null=True, blank=True)
    ordered = models.BooleanField(default=False)
    
    # Payment fields
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    pesapal_tracking_id = models.CharField(max_length=100, blank=True, null=True)
    pesapal_merchant_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Billing details
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_total_item_price()
        return total


class MpesaTransaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='mpesa_transactions')
    checkout_request_id = models.CharField(max_length=100, unique=True)
    merchant_request_id = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=MPESA_TRANSACTION_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"M-Pesa Transaction {self.checkout_request_id} - {self.status}"
