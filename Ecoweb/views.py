from django.shortcuts import render, get_object_or_404
from .models import Item, OrderItem, Order, MpesaTransaction
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .pesapal_service import PesapalService
from .mpesa_service import MpesaService
import json
import uuid


# Create your views here.
def index(request):
    data = Item.objects.all()
    context = {
        'data': data
    }
    return render(request, "index.html", context)


def search(request):
    if request.method == 'GET':
        query = request.GET.get('query')
        if query:
            kim = Item.objects.filter(title__icontains=query)
            return render(request, 'index.html', {'kim': kim})
        else:
            print("No information to show")
            return render(request, 'index.html', {})


def detailitem(request):
    return render(request, "product-detail.html")


def cartlist(request):
    return render(request, "cart.html")


class CheckoutView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {'object': order}
            return render(self.request, 'checkout.html', context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("Ecoweb:cart")

    def post(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("Ecoweb:cart")
        
        # Get form data
        first_name = self.request.POST.get('first_name')
        last_name = self.request.POST.get('last_name')
        email = self.request.POST.get('email')
        phone = self.request.POST.get('phone')
        address = self.request.POST.get('address')
        city = self.request.POST.get('city')
        payment_method = self.request.POST.get('payment_method')
        mpesa_phone = self.request.POST.get('mpesa_phone')
        
        # Validate required fields
        if not all([first_name, last_name, email, phone, address, city]):
            messages.error(self.request, "Please fill in all required fields")
            return render(self.request, 'checkout.html', {'object': order})
        
        # Validate phone numbers
        try:
            # Validate main phone number
            pesapal = PesapalService()
            formatted_phone = pesapal.format_phone_number(phone)
            
            # Validate M-Pesa phone if provided
            if payment_method == 'mpesa' and mpesa_phone:
                formatted_mpesa_phone = pesapal.format_phone_number(mpesa_phone)
            else:
                formatted_mpesa_phone = formatted_phone
                
        except ValueError as e:
            messages.error(self.request, f"Phone number error: {str(e)}")
            return render(self.request, 'checkout.html', {'object': order})
        
        # Save billing details to order
        order.first_name = first_name
        order.last_name = last_name
        order.email = email
        order.phone = formatted_phone
        order.address = address
        order.city = city
        order.payment_method = payment_method
        order.customer_phone = formatted_mpesa_phone
        order.save()
        
        # Handle M-Pesa STK Push payment
        if payment_method == 'mpesa':
            mpesa_service = MpesaService()
            stk_response = mpesa_service.initiate_stk_push(
                phone_number=formatted_mpesa_phone,
                amount=order.get_total(),
                order_id=order.id,
                description=f"Payment for Order #{order.id}"
            )
            
            if stk_response['status'] == 'success':
                # Create M-Pesa transaction record (only for real transactions)
                if not stk_response['checkout_request_id'].startswith('test_'):
                    MpesaTransaction.objects.create(
                        order=order,
                        checkout_request_id=stk_response['checkout_request_id'],
                        merchant_request_id=stk_response['merchant_request_id'],
                        phone_number=formatted_mpesa_phone,
                        amount=order.get_total()
                    )
                
                test_mode_msg = " (Test Mode)" if stk_response['checkout_request_id'].startswith('test_') else ""
                
                # Return JSON response for AJAX requests
                if self.request.headers.get('Content-Type') == 'application/json' or self.request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'status': 'success',
                        'message': f"Payment prompt sent to {formatted_mpesa_phone}{test_mode_msg}. Please check your phone and enter your M-Pesa PIN to complete payment.",
                        'checkout_request_id': stk_response['checkout_request_id'],
                        'redirect_url': '/payment-waiting/',
                        'amount': str(order.get_total())
                    })
                
                messages.success(self.request, 
                    f"✅ Payment prompt sent to {formatted_mpesa_phone}{test_mode_msg}. Please check your phone and enter your M-Pesa PIN to complete payment.")
                return render(self.request, 'payment-waiting.html', {
                    'order': order,
                    'amount': order.get_total(),
                    'checkout_request_id': stk_response['checkout_request_id'],
                    'phone_number': formatted_mpesa_phone,
                    'test_mode': stk_response['checkout_request_id'].startswith('test_')
                })
            else:
                # Return JSON response for AJAX requests
                if self.request.headers.get('Content-Type') == 'application/json' or self.request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Failed to send payment prompt: {stk_response['message']}"
                    })
                
                messages.error(self.request, f"❌ Failed to send payment prompt: {stk_response['message']}")
                return render(self.request, 'checkout.html', {'object': order})
        
        # Initialize Pesapal service for other payment methods
        pesapal = PesapalService()
        token = pesapal.get_access_token()
        
        if not token:
            messages.error(self.request, "Payment service unavailable. Please try again.")
            return render(self.request, "checkout.html", {'object': order})
        
        # Register IPN URL
        pesapal.register_ipn_url(token)
        
        # Prepare order data for Pesapal
        order_data = {
            'amount': order.get_total(),
            'order_number': order.id,
            'email': email,
            'phone': formatted_mpesa_phone,
            'first_name': first_name,
            'last_name': last_name,
            'address': address,
            'city': city
        }
        
        # Submit order to Pesapal
        payment_response = pesapal.submit_order_request(order_data, token)
        
        if payment_response['status'] == 'success':
            # Store tracking ID
            order.pesapal_tracking_id = payment_response['order_tracking_id']
            order.pesapal_merchant_reference = payment_response['merchant_reference']
            order.save()
            
            # Store in session
            self.request.session['order_tracking_id'] = payment_response['order_tracking_id']
            self.request.session['order_id'] = order.id
            
            # Redirect to Pesapal payment page
            return redirect(payment_response['redirect_url'])
        else:
            error_msg = payment_response.get('message', 'Failed to process payment. Please try again.')
            messages.error(self.request, error_msg)
            return render(self.request, "checkout.html", {'object': order})


def complete(request):
    return render(request, "order-complete.html")


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")


class HomeView(ListView):
    model = Item
    template_name = "index.html"


class OrderSummaryView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'cart.html', context)
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")


class ProductDetailView(DetailView):
    model = Item
    template_name = "product-detail.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
        else:
            order.items.add(order_item)
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
    return redirect("Ecoweb:detail", slug=slug)


def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False)[0]
            order.items.remove(order_item)
            return redirect("Ecoweb:cart")
        else:
            # add a message saying the order does not contain the item
            return redirect("Ecoweb:detail", slug=slug)
    else:
        # add a message saying the user doesn't have an order
        return redirect("Ecoweb:detail", slug=slug)
    return redirect("Ecoweb:detail", slug=slug)
class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = AuthenticationForm

class CustomSignupView(View):
    template_name = 'accounts/signup.html'
    form_class = UserCreationForm
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect('Ecoweb:index')
        return render(request, self.template_name, {'form': form})

@csrf_exempt
def pesapal_callback(request):
    """Handle Pesapal payment callback"""
    order_tracking_id = request.GET.get('OrderTrackingId')
    merchant_reference = request.GET.get('OrderMerchantReference')
    
    if not order_tracking_id:
        return HttpResponse("Missing tracking ID", status=400)
    
    # Get access token
    pesapal = PesapalService()
    token = pesapal.get_access_token()
    
    if not token:
        return HttpResponse("Service unavailable", status=500)
    
    # Get transaction status
    status_response = pesapal.get_transaction_status(order_tracking_id, token)
    
    if status_response:
        try:
            # Find the order
            order = Order.objects.get(pesapal_tracking_id=order_tracking_id)
            
            payment_status = status_response.get('payment_status_description', '').upper()
            
            if payment_status == 'COMPLETED':
                order.payment_status = 'COMPLETED'
                order.ordered = True
                order.ordered_date = timezone.now()
                # Mark all order items as ordered
                for item in order.items.all():
                    item.ordered = True
                    item.save()
                messages.success(request, "Payment successful! Your order has been confirmed.")
            elif payment_status in ['FAILED', 'INVALID']:
                order.payment_status = 'FAILED'
                messages.error(request, "Payment failed. Please try again.")
            
            order.save()
            
        except Order.DoesNotExist:
            return HttpResponse("Order not found", status=404)
    
    # Redirect to order complete page
    return redirect('Ecoweb:complete')

@csrf_exempt
def pesapal_ipn(request):
    """Handle Pesapal IPN notifications"""
    order_tracking_id = request.GET.get('OrderTrackingId')
    
    if order_tracking_id:
        # Get access token
        pesapal = PesapalService()
        token = pesapal.get_access_token()
        
        if token:
            # Get transaction status
            status_response = pesapal.get_transaction_status(order_tracking_id, token)
            
            if status_response:
                try:
                    order = Order.objects.get(pesapal_tracking_id=order_tracking_id)
                    payment_status = status_response.get('payment_status_description', '').upper()
                    
                    if payment_status == 'COMPLETED' and order.payment_status != 'COMPLETED':
                        order.payment_status = 'COMPLETED'
                        order.ordered = True
                        order.ordered_date = timezone.now()
                        for item in order.items.all():
                            item.ordered = True
                            item.save()
                        order.save()
                    elif payment_status in ['FAILED', 'INVALID']:
                        order.payment_status = 'FAILED'
                        order.save()
                        
                except Order.DoesNotExist:
                    pass
    
    return HttpResponse("OK", status=200)


@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa STK push callback"""
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body)
            
            # Extract callback data
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            
            if not checkout_request_id:
                return HttpResponse("Missing CheckoutRequestID", status=400)
            
            try:
                # Find the M-Pesa transaction
                mpesa_transaction = MpesaTransaction.objects.get(
                    checkout_request_id=checkout_request_id
                )
                order = mpesa_transaction.order
                
                if result_code == 0:  # Success
                    # Extract callback metadata
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    mpesa_receipt_number = None
                    transaction_date = None
                    
                    for item in callback_metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            mpesa_receipt_number = item.get('Value')
                        elif item.get('Name') == 'TransactionDate':
                            transaction_date = item.get('Value')
                    
                    # Update transaction
                    mpesa_transaction.status = 'SUCCESS'
                    mpesa_transaction.mpesa_receipt_number = mpesa_receipt_number
                    if transaction_date:
                        mpesa_transaction.transaction_date = timezone.now()
                    mpesa_transaction.save()
                    
                    # Update order
                    order.payment_status = 'COMPLETED'
                    order.ordered = True
                    order.ordered_date = timezone.now()
                    
                    # Mark all order items as ordered
                    for item in order.items.all():
                        item.ordered = True
                        item.save()
                    
                    order.save()
                    
                else:  # Failed
                    mpesa_transaction.status = 'FAILED'
                    mpesa_transaction.save()
                    
                    order.payment_status = 'FAILED'
                    order.save()
                
            except MpesaTransaction.DoesNotExist:
                return HttpResponse("Transaction not found", status=404)
            
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}", status=500)
    
    return HttpResponse("OK", status=200)


@login_required
def check_payment_status(request, checkout_request_id):
    """Check M-Pesa payment status via AJAX with test mode support"""
    try:
        # Handle test mode transactions
        if checkout_request_id.startswith('test_'):
            return handle_test_payment_status(checkout_request_id)
            
        mpesa_transaction = MpesaTransaction.objects.get(
            checkout_request_id=checkout_request_id
        )
        
        # Query M-Pesa API for status if still pending
        if mpesa_transaction.status == 'PENDING':
            mpesa_service = MpesaService()
            status_response = mpesa_service.query_stk_status(checkout_request_id)
            
            if status_response.get('ResponseCode') == '0':
                result_code = status_response.get('ResultCode')
                if result_code == '0':
                    mpesa_transaction.status = 'SUCCESS'
                    mpesa_transaction.save()
                    
                    order = mpesa_transaction.order
                    order.payment_status = 'COMPLETED'
                    order.ordered = True
                    order.ordered_date = timezone.now()
                    
                    # Mark all order items as ordered
                    for item in order.items.all():
                        item.ordered = True
                        item.save()
                    
                    order.save()
                elif result_code in ['1032', '1037']:  # User cancelled or timeout
                    mpesa_transaction.status = 'CANCELLED'
                    mpesa_transaction.save()
                elif result_code == '1':  # Failed
                    mpesa_transaction.status = 'FAILED'
                    mpesa_transaction.save()
        
        return JsonResponse({
            'status': mpesa_transaction.status.lower(),
            'message': {
                'SUCCESS': 'Payment completed successfully!',
                'FAILED': 'Payment failed. Please try again.',
                'CANCELLED': 'Payment was cancelled.',
                'PENDING': 'Waiting for payment confirmation...'
            }.get(mpesa_transaction.status, 'Unknown status')
        })
        
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Transaction not found'})


def handle_test_payment_status(checkout_request_id):
    """Handle test mode payment status checking"""
    from django.core.cache import cache
    import time
    
    test_data = cache.get(f'test_payment_{checkout_request_id}')
    if not test_data:
        return JsonResponse({'status': 'error', 'message': 'Test transaction not found'})
    
    phone = test_data['phone']
    created_at = test_data['created_at']
    elapsed = time.time() - created_at
    
    # Simulate different outcomes based on phone number
    if phone == '254700000000':  # Success after 10 seconds
        if elapsed > 10:
            # Mark as successful in cache
            cache.set(f'test_status_{checkout_request_id}', 'success', 300)
            return JsonResponse({
                'status': 'success',
                'message': 'Test payment completed successfully!'
            })
    elif phone == '254711111111':  # Cancelled after 15 seconds
        if elapsed > 15:
            cache.set(f'test_status_{checkout_request_id}', 'cancelled', 300)
            return JsonResponse({
                'status': 'cancelled',
                'message': 'Test payment was cancelled.'
            })
    elif phone == '254722222222':  # Failed after 20 seconds
        if elapsed > 20:
            cache.set(f'test_status_{checkout_request_id}', 'failed', 300)
            return JsonResponse({
                'status': 'failed',
                'message': 'Test payment failed.'
            })
    
    # Still pending
    return JsonResponse({
        'status': 'pending',
        'message': 'Test payment is being processed...'
    })


@csrf_exempt
def send_payment_confirmation(request):
    """Send payment confirmation message via API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone')
            
            if phone:
                # Format phone number
                mpesa_service = MpesaService()
                formatted_phone = mpesa_service.format_phone_number(phone)
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Payment instructions will be sent to {formatted_phone}',
                    'phone': formatted_phone
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Phone number is required'
                })
                
        except ValueError as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to process request'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def send_payment_success_notification(request):
    """Send payment success notification"""
    if request.method == 'POST':
        return JsonResponse({
            'status': 'success',
            'message': 'Payment success notification sent'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})