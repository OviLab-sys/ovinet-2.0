# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class AccessToken(models.Model):
	token = models.CharField(max_length=30)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		get_latest_by = 'created_at'

	def __str__(self):
		return self.token

class AllMpesaTransactions(models.Model):
    merchant_request_id = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    response_code = models.CharField(max_length=10)
    response_description = models.TextField()
    customer_message = models.TextField() 
    created_at = models.DateTimeField(auto_now_add=True)
    Amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # DecimalField()

    def __str__(self):
        return f"Transaction {self.merchant_request_id} - {self.response_code}"