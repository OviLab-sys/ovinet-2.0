import requests
from django.conf import settings
import base64
from .exceptions import MpesaInvalidParameterException, MpesaConnectionError
from datetime import datetime
from .utils import mpesa_access_token, format_phone, api_base_url, mpesa_response, mpesa_config, encrypt_security_credential
import json
from tenants.models import MpesaTransaction
from .models import AllMpesaTransactions

class MpesaAPI:
    """
    This is the core MPESA client.
    The MPESA client will access all interractions with the MPESA Daraja API.
    """
    
    auth_token = ''
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY

    def get_access_token(self):
        return mpesa_access_token()
    
    def parse_stk_result(self, result):
        """Parse the result of Lipa na MPESA ONLINE Payment (STK PUSH)
        Returns the result data as a dict."""
        payload = json.loads(result)
        data = {}
        callback = payload['Body']['stkCallback']
        data['ResultCode'] = callback['ResultCode']
        data['ResultDesc'] = callback['ResultDesc']
        data['MerchantRequestID'] = callback['MerchantRequestID']
        data['CheckoutRequestID'] = callback['CheckoutRequestID']
        metadata = callback.get('CallbackMetadata')
        if metadata:
            metadata_items = metadata.get('Item')
            for item in metadata_items:
                data[item['Name']] = item.get('Value')
        return data
    
    
    def save_mpesa_transaction(data):
        """
        Save Mpesa transaction details to the database.
        Expects a dict with keys: MerchantRequestID, CheckoutRequestID, ResultCode, ResultDesc, CustomerMessage
        """
        MpesaTransaction.objects.create(
            merchant_request_id=data.get('MerchantRequestID', ''),
            checkout_request_id=data.get('CheckoutRequestID', ''),
            response_code=str(data.get('ResultCode', '')),
            response_description=data.get('ResultDesc', ''),
            customer_message=data.get('CustomerMessage', ''),
            amount=data.get('Amount')
            )
        
        AllMpesaTransactions.objects.create(
            merchant_request_id=data.get('MerchantRequestID', ''),
            checkout_request_id=data.get('CheckoutRequestID', ''),
            response_code=str(data.get('ResultCode', '')),
            response_description=data.get('ResultDesc', ''),
            customer_message=data.get('CustomerMessage', ''),
            amount=data.get('Amount')
            )
  
    
    def stk_push(self, phone_number, amount, account_reference,
                 transaction_desc, callback_url, 
                 transaction_type = "CustomerPayBillOnline"):
        phone_number = format_phone(phone_number)
        access_token = self.get_access_token()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": transaction_type,
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        url = api_base_url() + "mpesa/stkpush/v1/processrequest"
        try:
            r = requests.post(url, json=payload, headers=headers)
            resp_data = mpesa_response(r)
            # Save transaction if response contains required fields
            if 'MerchantRequestID' in resp_data and 'CheckoutRequestID' in resp_data:
                save_mpesa_transaction({
                    'MerchantRequestID': resp_data.get('MerchantRequestID'),
                    'CheckoutRequestID': resp_data.get('CheckoutRequestID'),
                    'ResultCode': resp_data.get('ResponseCode', resp_data.get('ResultCode', '')),
                    'ResultDesc': resp_data.get('ResponseDescription', resp_data.get('ResultDesc', '')),
                    'CustomerMessage': resp_data.get('CustomerMessage', ''),
                    'Amount': resp_data.get('Amount')
                    })
            return resp_data
        except requests.exceptions.ConnectionError:
            raise MpesaConnectionError('Connection failed')
        except Exception as ex:
            raise MpesaConnectionError(str(ex))
    
    def b2c_payment(self, phone_number, amount, transaction_desc, callback_url, occassion, command_id):
        """
        Attempt to perform a business payment transaction
        Args:
            phone_number (str): The Mobile Number to receive the payment.
            amount (int): Amount transacted (whole number).
            transaction_desc (str): Additional info/comment (max 13 chars).
            callback_url (str): Secure URL for API notifications.
            occassion (str): Additional info for the transaction.
            command_id (str): Type of B2C transaction.
        Returns:
            MpesaResponse: MpesaResponse object containing the details of the API response
        Raises:
            MpesaInvalidParameterException: Invalid parameter passed
            MpesaConnectionError: Connection error
        """
        if str(transaction_desc).strip() == '':
            raise MpesaInvalidParameterException('Transaction description cannot be blank')
        if not isinstance(amount, int):
            raise MpesaInvalidParameterException('Amount must be an integer')
        phone_number = format_phone(phone_number)
        url = api_base_url() + 'mpesa/b2c/v1/paymentrequest'
        business_short_code = mpesa_config('MPESA_SHORTCODE')
        party_a = business_short_code
        party_b = phone_number
        initiator_username = mpesa_config('MPESA_INITIATOR_USERNAME')
        initiator_security_credential = encrypt_security_credential(mpesa_config('MPESA_INITIATOR_SECURITY_CREDENTIAL'))
        data = {
            'InitiatorName': initiator_username,
            'SecurityCredential': initiator_security_credential,
            'CommandID': command_id,
            'Amount': amount,
            'PartyA': party_a,
            'PartyB': party_b,
            'Remarks': transaction_desc,
            'QueueTimeOutURL': callback_url,
            'ResultURL': callback_url,
            'Occassion': occassion
        }
        headers = {
            'Authorization': 'Bearer ' + mpesa_access_token(),
            'Content-type': 'application/json'
        }
        try:
            r = requests.post(url, json=data, headers=headers)
            response = mpesa_response(r)
            if 'MerchantRequestID' in response and 'CheckoutRequestID' in response:
                save_mpesa_transaction({
                    'MerchantRequestID': response.get('MerchantRequestID'),
                    'CheckoutRequestID': response.get('CheckoutRequestID'),
                    'ResultCode': response.get('ResponseCode', response.get('ResultCode', '')),
                    'ResultDesc': response.get('ResponseDescription', response.get('ResultDesc', '')),
                    'CustomerMessage': response.get('CustomerMessage', '')
                })
            return response
        except requests.exceptions.ConnectionError:
            raise MpesaConnectionError('Connection failed')
        except Exception as ex:
            raise MpesaConnectionError(str(ex))

    def business_payment(self, phone_number, amount, transaction_desc, callback_url, occassion):
        command_id = 'BusinessPayment'
        return self.b2c_payment(phone_number, amount, transaction_desc, callback_url, occassion, command_id)

    def customer_refund(self, phone_number, amount, transaction_desc, callback_url, occassion):
        command_id = 'CustomerRefund'
        return self.b2c_payment(phone_number, amount, transaction_desc, callback_url, occassion, command_id)

    def promotion_payment(self, phone_number, amount, transaction_desc, callback_url, occassion):
        command_id = 'PromotionPayment'
        return self.b2c_payment(phone_number, amount, transaction_desc, callback_url, occassion, command_id)
