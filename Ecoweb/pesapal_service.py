import hashlib
import hmac
import base64
import urllib.parse
import requests
from django.conf import settings
from django.urls import reverse
import uuid
import json
import re

class PesapalService:
    def __init__(self):
        self.consumer_key = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')
        self.is_sandbox = getattr(settings, 'PESAPAL_IS_SANDBOX', True)
        self.base_url = "https://cybqa.pesapal.com/pesapalv3" if self.is_sandbox else "https://pay.pesapal.com/v3"
        self.callback_url = getattr(settings, 'PESAPAL_CALLBACK_URL', '')
        self.ipn_url = getattr(settings, 'PESAPAL_IPN_URL', '')
    
    def format_phone_number(self, phone):
        """Format phone number to proper Kenyan format (starting with 254)"""
        phone = re.sub(r'\D', '', phone)
        
        if phone.startswith('0'):
            if not (phone.startswith('07') or phone.startswith('01')):
                raise ValueError("Phone number must start with 07 or 01")
            phone = '254' + phone[1:]
        elif phone.startswith('254'):
            if not (phone.startswith('2547') or phone.startswith('2541')):
                raise ValueError("Phone number must be a valid Kenyan mobile number (7... or 1...)")
        elif phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        else:
            raise ValueError("Phone number must start with 07, 01 or 254")
        
        if len(phone) != 12:
            raise ValueError(f"Invalid phone number length. Expected 10 digits (07...) or 12 digits (254...)")
        
        return phone
        
    def get_access_token(self):
        """Get access token from Pesapal"""
        url = f"{self.base_url}/api/Auth/RequestToken"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        data = {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.json().get('token')
        return None
    
    def register_ipn_url(self, token):
        """Register IPN URL with Pesapal"""
        url = f"{self.base_url}/api/URLSetup/RegisterIPN"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        data = {
            'url': self.ipn_url,
            'ipn_notification_type': 'GET'
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json() if response.status_code == 200 else None
    
    def submit_order_request(self, order_data, token):
        """Submit order to Pesapal for payment"""
        url = f"{self.base_url}/api/Transactions/SubmitOrderRequest"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        # Generate unique order ID
        order_id = f"ORDER_{uuid.uuid4().hex[:8].upper()}"
        
        # Format and validate phone number
        try:
            formatted_phone = self.format_phone_number(order_data['phone'])
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        
        pesapal_data = {
            'id': order_id,
            'currency': 'KES',
            'amount': float(order_data['amount']),
            'description': f"Payment for Order #{order_data['order_number']}",
            'callback_url': self.callback_url,
            'notification_id': order_data.get('ipn_id', ''),
            'billing_address': {
                'email_address': order_data['email'],
                'phone_number': formatted_phone,
                'country_code': 'KE',
                'first_name': order_data['first_name'],
                'last_name': order_data['last_name'],
                'line_1': order_data.get('address', ''),
                'city': order_data.get('city', 'Nairobi'),
                'state': order_data.get('state', 'Nairobi'),
                'postal_code': order_data.get('postal_code', '00100'),
                'zip_code': order_data.get('zip_code', '00100')
            },
            'account_number': '0840182413804'
        }
        
        response = requests.post(url, json=pesapal_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return {
                'order_tracking_id': result.get('order_tracking_id'),
                'merchant_reference': result.get('merchant_reference'),
                'redirect_url': result.get('redirect_url'),
                'status': 'success'
            }
        
        return {'status': 'error', 'message': 'Failed to submit order'}
    
    def get_transaction_status(self, order_tracking_id, token):
        """Get transaction status from Pesapal"""
        url = f"{self.base_url}/api/Transactions/GetTransactionStatus"
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        params = {'orderTrackingId': order_tracking_id}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        return None