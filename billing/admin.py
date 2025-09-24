from django.contrib import admin
from .mpesa.models import AccessToken, AllMpesaTransactions

# Register your models here.
@admin.register(AllMpesaTransactions)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'merchant_request_id',
        'checkout_request_id',
        'response_code',
        'response_description',
        'customer_message',
        'created_at',
        'Amount',  # Note: field name is capital 'A'
    ]
    search_fields = [
        'merchant_request_id',
        'checkout_request_id',
        'response_code',
        'Amount',
    ]