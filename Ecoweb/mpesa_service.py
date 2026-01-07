import requests
import json
import base64
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
import re
import logging
import time

logger = logging.getLogger(__name__)

class MpesaService:
    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.business_shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.account_number = getattr(settings, 'BUSINESS_NUMBER', 'LNM_STK_PUSH')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.base_url = 'https://sandbox.safaricom.co.ke' if getattr(settings, 'MPESA_IS_SANDBOX', True) else 'https://api.safaricom.co.ke'
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        self.test_mode = getattr(settings, 'MPESA_TEST_MODE', getattr(settings, 'DEBUG', False))
        self.timeout = 30
    
    def format_phone_number(self, phone):
        """Format phone number to proper Kenyan format (starting with 254)"""
        phone = re.sub(r'\D', '', phone)
        
        # Validate that input starts with 07 or 01 (after removing non-digits)
        # or starts with 2547/2541
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
        """Get OAuth access token from Safaricom with caching"""
        # Check cache first for faster response
        cache_key = 'mpesa_access_token'
        token = cache.get(cache_key)
        if token:
            return token
            
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                token = response.json().get('access_token')
                # Cache token for 50 minutes (expires in 1 hour)
                cache.set(cache_key, token, 3000)
                return token
            else:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
        
        return None
    
    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp
    
    def initiate_stk_push(self, phone_number, amount, order_id, description="Payment"):
        """Initiate STK push to customer's phone with test mode support"""
        # Test mode for localhost development
        if self.test_mode and phone_number in ['254700000000', '254711111111', '254722222222']:
            return self._simulate_test_payment(phone_number, amount, order_id)
            
        access_token = self.get_access_token()
        if not access_token:
            return {'status': 'error', 'message': 'Failed to get access token'}
        
        try:
            formatted_phone = self.format_phone_number(phone_number)
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        
        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": formatted_phone,
            "PartyB": self.business_shortcode,
            "PhoneNumber": formatted_phone,
            "CallBackURL": self.callback_url,
            "AccountReference": self.account_number,
            "TransactionDesc": f"{description} - Order #{order_id}"
        }
        
        try:
            logger.info(f"Initiating STK push for {formatted_phone}, Amount: {amount}")
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            result = response.json()
            
            logger.info(f"STK Push Response: {result}")
            
            if response.status_code == 200 and result.get('ResponseCode') == '0':
                return {
                    'status': 'success',
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'message': 'STK push sent successfully'
                }
            else:
                error_msg = result.get('errorMessage', result.get('ResponseDescription', 'Failed to initiate payment'))
                logger.error(f"STK Push failed: {error_msg}")
                return {
                    'status': 'error',
                    'message': error_msg
                }
        except Exception as e:
            logger.error(f"STK Push request failed: {str(e)}")
            return {'status': 'error', 'message': f'Request failed: {str(e)}'}
    
    def query_stk_status(self, checkout_request_id):
        """Query the status of STK push transaction with caching"""
        # Check cache first for faster response
        cache_key = f'mpesa_status_{checkout_request_id}'
        cached_status = cache.get(cache_key)
        if cached_status:
            return cached_status
            
        # Test mode simulation
        if self.test_mode and checkout_request_id.startswith('test_'):
            return self._get_test_status(checkout_request_id)
            
        access_token = self.get_access_token()
        if not access_token:
            return {'status': 'error', 'message': 'Failed to get access token'}
        
        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            result = response.json()
            
            # Cache successful responses for 30 seconds
            if response.status_code == 200:
                cache.set(cache_key, result, 30)
                
            return result
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return {'status': 'error', 'message': f'Query failed: {str(e)}'}
    
    def _simulate_test_payment(self, phone_number, amount, order_id):
        """Simulate payment for test mode"""
        import uuid
        checkout_request_id = f"test_{uuid.uuid4().hex[:20]}"
        
        # Store test payment in cache
        cache.set(f'test_payment_{checkout_request_id}', {
            'phone': phone_number,
            'amount': amount,
            'order_id': order_id,
            'created_at': time.time()
        }, 300)  # 5 minutes
        
        logger.info(f"Test mode: Simulated STK push for {phone_number}")
        
        return {
            'status': 'success',
            'checkout_request_id': checkout_request_id,
            'merchant_request_id': f"test_merchant_{uuid.uuid4().hex[:10]}",
            'message': 'Test STK push sent successfully'
        }
    
    def _get_test_status(self, checkout_request_id):
        """Get test payment status"""
        test_data = cache.get(f'test_payment_{checkout_request_id}')
        if not test_data:
            return {'ResponseCode': '1', 'ResponseDescription': 'Test transaction not found'}
        
        # Simulate different outcomes based on phone number
        phone = test_data['phone']
        created_at = test_data['created_at']
        elapsed = time.time() - created_at
        
        if phone == '254700000000':  # Success after 10 seconds
            if elapsed > 10:
                return {'ResponseCode': '0', 'ResultCode': '0', 'ResultDesc': 'Test payment successful'}
        elif phone == '254711111111':  # Cancelled after 15 seconds
            if elapsed > 15:
                return {'ResponseCode': '0', 'ResultCode': '1032', 'ResultDesc': 'Test payment cancelled'}
        elif phone == '254722222222':  # Failed after 20 seconds
            if elapsed > 20:
                return {'ResponseCode': '0', 'ResultCode': '1', 'ResultDesc': 'Test payment failed'}
        
        # Still pending
        return {'ResponseCode': '0', 'ResultCode': '1037', 'ResultDesc': 'Test payment pending'}