from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import Order, MpesaTransaction
from .mpesa_service import MpesaService
import json
import re
import requests
from django.conf import settings

class PhoneConfirmationAPI(View):
    """API for phone number confirmation and messaging"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
            
            if not phone:
                return JsonResponse({'error': 'Phone number required'}, status=400)
            
            # Validate and format phone number
            formatted_phone = self.format_phone_number(phone)
            if not formatted_phone:
                return JsonResponse({'error': 'Invalid phone number format'}, status=400)
            
            # Send confirmation message
            message_sent = self.send_confirmation_sms(formatted_phone)
            
            return JsonResponse({
                'success': True,
                'phone': formatted_phone,
                'message_sent': message_sent,
                'message': 'Phone number confirmed successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def format_phone_number(self, phone):
        """Format and validate Kenyan phone number"""
        phone = re.sub(r'\D', '', phone)
        
        if phone.startswith('0') and len(phone) == 10:
            return '254' + phone[1:]
        elif phone.startswith('254') and len(phone) == 12:
            return phone
        elif (phone.startswith('7') or phone.startswith('1')) and len(phone) == 9:
            return '254' + phone
        
        return None
    
    def send_confirmation_sms(self, phone):
        """Send SMS confirmation message"""
        try:
            message = (
                "Thank you for confirming your phone number with our store! "
                "You will receive payment instructions shortly. "
                "For support, contact us at support@yourstore.com"
            )
            
            # Use Africa's Talking or any SMS service
            return self.send_sms_via_africas_talking(phone, message)
            
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return False
    
    def send_sms_via_africas_talking(self, phone, message):
        """Send SMS using Africa's Talking API"""
        try:
            # Replace with your Africa's Talking credentials
            api_key = getattr(settings, 'AFRICAS_TALKING_API_KEY', '')
            username = getattr(settings, 'AFRICAS_TALKING_USERNAME', '')
            
            if not api_key or not username:
                return False
            
            url = "https://api.africastalking.com/version1/messaging"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'apiKey': api_key
            }
            
            data = {
                'username': username,
                'to': phone,
                'message': message,
                'from': getattr(settings, 'SMS_SENDER_ID', 'YourStore')
            }
            
            response = requests.post(url, headers=headers, data=data)
            return response.status_code == 201
            
        except Exception as e:
            print(f"Africa's Talking SMS failed: {e}")
            return False


class PaymentStatusAPI(View):
    """API for checking M-Pesa payment status"""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, checkout_request_id):
        try:
            # Find the M-Pesa transaction
            mpesa_transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id,
                order__user=request.user
            )
            
            # If still pending, query M-Pesa API
            if mpesa_transaction.status == 'PENDING':
                self.update_payment_status(mpesa_transaction)
            
            # Return current status
            status_map = {
                'SUCCESS': 'success',
                'FAILED': 'failed',
                'CANCELLED': 'cancelled',
                'PENDING': 'pending'
            }
            
            response_data = {
                'status': status_map.get(mpesa_transaction.status, 'pending'),
                'message': self.get_status_message(mpesa_transaction.status),
                'transaction_id': mpesa_transaction.mpesa_receipt_number or '',
                'amount': str(mpesa_transaction.amount)
            }
            
            # Send success message if payment completed
            if mpesa_transaction.status == 'SUCCESS':
                self.send_payment_success_message(mpesa_transaction)
            
            return JsonResponse(response_data)
            
        except MpesaTransaction.DoesNotExist:
            return JsonResponse({'error': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def update_payment_status(self, mpesa_transaction):
        """Query M-Pesa API for latest status"""
        try:
            mpesa_service = MpesaService()
            status_response = mpesa_service.query_stk_status(
                mpesa_transaction.checkout_request_id
            )
            
            if status_response.get('ResponseCode') == '0':
                result_code = status_response.get('ResultCode')
                
                if result_code == '0':  # Success
                    mpesa_transaction.status = 'SUCCESS'
                    mpesa_transaction.save()
                    
                    # Update order
                    order = mpesa_transaction.order
                    order.payment_status = 'COMPLETED'
                    order.ordered = True
                    order.save()
                    
                    # Mark order items as ordered
                    for item in order.items.all():
                        item.ordered = True
                        item.save()
                        
                elif result_code in ['1032', '1037']:  # Cancelled/Timeout
                    mpesa_transaction.status = 'CANCELLED'
                    mpesa_transaction.save()
                    
                elif result_code == '1':  # Failed
                    mpesa_transaction.status = 'FAILED'
                    mpesa_transaction.save()
                    
        except Exception as e:
            print(f"Status update failed: {e}")
    
    def get_status_message(self, status):
        """Get user-friendly status message"""
        messages = {
            'SUCCESS': 'Payment completed successfully! Your order is confirmed.',
            'FAILED': 'Payment failed. Please try again or contact support.',
            'CANCELLED': 'Payment was cancelled. You can try again.',
            'PENDING': 'Waiting for payment confirmation. Please check your phone.'
        }
        return messages.get(status, 'Unknown payment status')
    
    def send_payment_success_message(self, mpesa_transaction):
        """Send success SMS after payment completion"""
        try:
            order = mpesa_transaction.order
            message = (
                f"Payment successful! Your order #{order.id} for KES {mpesa_transaction.amount} "
                f"has been confirmed. Receipt: {mpesa_transaction.mpesa_receipt_number}. "
                f"Thank you for shopping with us!"
            )
            
            phone_api = PhoneConfirmationAPI()
            phone_api.send_sms_via_africas_talking(
                mpesa_transaction.phone_number, 
                message
            )
            
        except Exception as e:
            print(f"Success message failed: {e}")


class PaymentSuccessMessageAPI(View):
    """API for sending payment success messages"""
    
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            # Find the user's latest completed order
            order = Order.objects.filter(
                user=request.user,
                payment_status='COMPLETED'
            ).order_by('-ordered_date').first()
            
            if not order:
                return JsonResponse({'error': 'No completed order found'}, status=404)
            
            # Send success email and SMS
            email_sent = self.send_success_email(order)
            sms_sent = self.send_success_sms(order)
            
            return JsonResponse({
                'success': True,
                'email_sent': email_sent,
                'sms_sent': sms_sent,
                'order_id': order.id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def send_success_email(self, order):
        """Send order confirmation email"""
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            
            subject = f'Order Confirmation #{order.id}'
            
            # Render email template
            html_message = render_to_string('emails/order_confirmation.html', {
                'order': order,
                'customer_name': f"{order.first_name} {order.last_name}"
            })
            
            plain_message = f"""
            Dear {order.first_name},
            
            Thank you for your order! Your payment has been confirmed.
            
            Order Details:
            Order Number: #{order.id}
            Total Amount: KES {order.get_total()}
            Payment Method: {order.payment_method}
            
            Your order is being processed and you will receive shipping updates soon.
            
            Thank you for shopping with us!
            """
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [order.email],
                html_message=html_message,
                fail_silently=False
            )
            
            return True
            
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def send_success_sms(self, order):
        """Send order confirmation SMS"""
        try:
            message = (
                f"Order #{order.id} confirmed! "
                f"Total: KES {order.get_total()}. "
                f"We'll notify you when your order ships. "
                f"Thank you for choosing us!"
            )
            
            phone_api = PhoneConfirmationAPI()
            return phone_api.send_sms_via_africas_talking(
                order.customer_phone, 
                message
            )
            
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return False


# Function-based views for backward compatibility
@csrf_exempt
@require_http_methods(["POST"])
def send_phone_confirmation(request):
    """Function-based view for phone confirmation"""
    api = PhoneConfirmationAPI()
    return api.post(request)


@login_required
@require_http_methods(["GET"])
def check_payment_status(request, checkout_request_id):
    """Function-based view for payment status checking"""
    api = PaymentStatusAPI()
    return api.get(request, checkout_request_id)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def send_payment_success(request):
    """Function-based view for payment success messaging"""
    api = PaymentSuccessMessageAPI()
    return api.post(request)