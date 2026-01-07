class PaymentHandler {
    constructor() {
        this.phonePattern = /^(254[17][0-9]{8}|0[17][0-9]{8})$/;
        this.paymentCheckInterval = null;
        this.maxRetries = 30; // 5 minutes with 10-second intervals
        this.currentRetries = 0;
        
        this.init();
    }
    
    init() {
        this.setupPhoneValidation();
        this.setupPaymentMethodHandlers();
        this.setupFormSubmission();
        this.setupAutoFill();
    }
    
    setupPhoneValidation() {
        const phoneInputs = document.querySelectorAll('#phone, #mpesa_phone');
        
        phoneInputs.forEach(input => {
            input.addEventListener('input', (e) => this.handlePhoneInput(e));
            input.addEventListener('blur', (e) => this.validatePhone(e.target));
            input.addEventListener('focus', (e) => this.clearPhoneErrors(e.target));
        });
    }
    
    handlePhoneInput(event) {
        const input = event.target;
        let value = input.value.replace(/\D/g, '');
        
        // Auto-format based on input
        if (value.startsWith('0') && value.length <= 10) {
            input.value = this.formatPhoneDisplay(value, '0');
        } else if (value.startsWith('254') && value.length <= 12) {
            input.value = this.formatPhoneDisplay(value, '254');
        } else if ((value.startsWith('7') || value.startsWith('1')) && value.length <= 9) {
            input.value = this.formatPhoneDisplay('0' + value, '0');
        }
        
        // Real-time validation feedback
        this.validatePhone(input, false);
    }
    
    formatPhoneDisplay(phone, format) {
        if (format === '0' && phone.length > 3) {
            return phone.substring(0, 4) + ' ' + phone.substring(4);
        } else if (format === '254' && phone.length > 6) {
            return phone.substring(0, 6) + ' ' + phone.substring(6);
        }
        return phone;
    }
    
    validatePhone(input, showSuccess = true) {
        const value = input.value.replace(/\D/g, '');
        const isValid = this.phonePattern.test(value);
        
        this.clearPhoneErrors(input);
        
        if (value.length > 0) {
            if (isValid) {
                if (showSuccess) {
                    this.showPhoneSuccess(input);
                }
                this.triggerPhoneConfirmed(input, value);
                return true;
            } else {
                this.showPhoneError(input, 'Invalid phone format. Use 0712345678 or 254712345678');
                return false;
            }
        }
        return false;
    }
    
    showPhoneError(input, message) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        
        let errorDiv = input.parentNode.querySelector('.phone-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'phone-error text-danger small mt-1';
            input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }
    
    showPhoneSuccess(input) {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
        
        let successDiv = input.parentNode.querySelector('.phone-success');
        if (!successDiv) {
            successDiv = document.createElement('div');
            successDiv.className = 'phone-success text-success small mt-1';
            input.parentNode.appendChild(successDiv);
        }
        successDiv.innerHTML = '<i class="fa fa-check"></i> Phone number confirmed';
    }
    
    clearPhoneErrors(input) {
        input.classList.remove('is-invalid', 'is-valid');
        const errorDiv = input.parentNode.querySelector('.phone-error');
        const successDiv = input.parentNode.querySelector('.phone-success');
        if (errorDiv) errorDiv.remove();
        if (successDiv) successDiv.remove();
    }
    
    triggerPhoneConfirmed(input, phoneNumber) {
        // Auto-send confirmation message
        this.sendPhoneConfirmationMessage(phoneNumber);
        
        // Enable payment button if all validations pass
        this.checkFormValidity();
    }
    
    async sendPhoneConfirmationMessage(phoneNumber) {
        try {
            const response = await fetch('/api/send-phone-confirmation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ phone: phoneNumber })
            });
            
            if (response.ok) {
                this.showNotification('Phone number confirmed! You will receive payment instructions.', 'success');
            }
        } catch (error) {
            console.log('Phone confirmation message failed:', error);
        }
    }
    
    setupPaymentMethodHandlers() {
        const paymentMethods = document.querySelectorAll('input[name="payment_method"]');
        const mpesaDetails = document.getElementById('mpesa-details');
        const mpesaPhone = document.getElementById('mpesa_phone');
        const phoneInput = document.getElementById('phone');
        
        paymentMethods.forEach(method => {
            method.addEventListener('change', (e) => {
                if (e.target.value === 'mpesa') {
                    mpesaDetails.style.display = 'block';
                    mpesaPhone.required = true;
                    
                    // Auto-fill from main phone if valid
                    const phoneValue = phoneInput.value.replace(/\D/g, '');
                    if (this.phonePattern.test(phoneValue) && !mpesaPhone.value) {
                        mpesaPhone.value = phoneInput.value;
                        this.validatePhone(mpesaPhone);
                    }
                } else {
                    mpesaDetails.style.display = 'none';
                    mpesaPhone.required = false;
                }
            });
        });
    }
    
    setupAutoFill() {
        const phoneInput = document.getElementById('phone');
        const mpesaPhone = document.getElementById('mpesa_phone');
        
        phoneInput.addEventListener('input', () => {
            const selectedMethod = document.querySelector('input[name="payment_method"]:checked');
            if (selectedMethod && selectedMethod.value === 'mpesa' && !mpesaPhone.value) {
                const phoneValue = phoneInput.value.replace(/\D/g, '');
                if (this.phonePattern.test(phoneValue)) {
                    mpesaPhone.value = phoneInput.value;
                    this.validatePhone(mpesaPhone);
                }
            }
        });
    }
    
    setupFormSubmission() {
        const form = document.getElementById('checkout-form');
        const submitBtn = document.getElementById('place-order-btn');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!this.validateForm()) {
                return;
            }
            
            this.showLoadingState(submitBtn);
            
            const selectedMethod = document.querySelector('input[name="payment_method"]:checked').value;
            
            if (selectedMethod === 'mpesa') {
                await this.handleMpesaPayment(form);
            } else {
                form.submit(); // Regular form submission for other methods
            }
        });
    }
    
    validateForm() {
        const phoneInput = document.getElementById('phone');
        const mpesaPhone = document.getElementById('mpesa_phone');
        const selectedMethod = document.querySelector('input[name="payment_method"]:checked').value;
        
        // Validate main phone
        if (!this.validatePhone(phoneInput)) {
            this.showNotification('Please enter a valid phone number', 'error');
            phoneInput.focus();
            return false;
        }
        
        // Validate M-Pesa phone if selected
        if (selectedMethod === 'mpesa') {
            if (!mpesaPhone.value) {
                this.showNotification('Please enter your M-Pesa phone number', 'error');
                mpesaPhone.focus();
                return false;
            }
            
            if (!this.validatePhone(mpesaPhone)) {
                this.showNotification('Please enter a valid M-Pesa phone number', 'error');
                mpesaPhone.focus();
                return false;
            }
        }
        
        return true;
    }
    
    async handleMpesaPayment(form) {
        try {
            const formData = new FormData(form);
            
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.text();
                
                // Check if we got a payment waiting page
                if (result.includes('payment-waiting') || result.includes('checkout_request_id')) {
                    // Extract checkout request ID from response
                    const checkoutMatch = result.match(/checkout_request_id['"]\s*:\s*['"]([^'"]+)['"]/);
                    if (checkoutMatch) {
                        this.startPaymentStatusCheck(checkoutMatch[1]);
                    }
                    
                    // Show payment waiting interface
                    document.body.innerHTML = result;
                    this.showPaymentWaitingInterface();
                } else {
                    // Handle other responses
                    document.body.innerHTML = result;
                }
            } else {
                throw new Error('Payment request failed');
            }
        } catch (error) {
            this.hideLoadingState();
            this.showNotification('Payment failed. Please try again.', 'error');
            console.error('Payment error:', error);
        }
    }
    
    showPaymentWaitingInterface() {
        // Enhanced payment waiting interface
        const waitingDiv = document.querySelector('.payment-waiting');
        if (waitingDiv) {
            // Add countdown timer
            this.addCountdownTimer(waitingDiv);
            
            // Add manual refresh button
            this.addManualRefreshButton(waitingDiv);
            
            // Show payment instructions notification
            this.showNotification('Payment prompt sent to your phone. Please check your M-Pesa messages.', 'info', 10000);
        }
    }
    
    addCountdownTimer(container) {
        const timerDiv = document.createElement('div');
        timerDiv.className = 'payment-timer mt-3';
        timerDiv.innerHTML = `
            <div class="alert alert-warning">
                <i class="fa fa-clock-o"></i> 
                Payment expires in: <span id="countdown">5:00</span>
                <br><small>Please complete payment within 5 minutes</small>
            </div>
        `;
        container.appendChild(timerDiv);
        
        this.startCountdown(300); // 5 minutes
    }
    
    startCountdown(seconds) {
        const countdownElement = document.getElementById('countdown');
        
        const timer = setInterval(() => {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            countdownElement.textContent = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
            
            if (seconds <= 0) {
                clearInterval(timer);
                this.showNotification('Payment timeout. Please try again.', 'error');
                setTimeout(() => {
                    window.location.href = '/checkout/';
                }, 3000);
            }
            
            seconds--;
        }, 1000);
    }
    
    addManualRefreshButton(container) {
        const refreshDiv = document.createElement('div');
        refreshDiv.className = 'manual-refresh mt-3';
        refreshDiv.innerHTML = `
            <button class="btn btn-outline-primary" onclick="paymentHandler.checkPaymentStatusNow()">
                <i class="fa fa-refresh"></i> Check Payment Status
            </button>
        `;
        container.appendChild(refreshDiv);
    }
    
    startPaymentStatusCheck(checkoutRequestId) {
        this.currentRetries = 0;
        
        this.paymentCheckInterval = setInterval(async () => {
            await this.checkPaymentStatus(checkoutRequestId);
        }, 10000); // Check every 10 seconds
    }
    
    async checkPaymentStatus(checkoutRequestId) {
        try {
            const response = await fetch(`/api/check-payment-status/${checkoutRequestId}/`, {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.status === 'success') {
                    this.handlePaymentSuccess();
                } else if (result.status === 'failed' || result.status === 'cancelled') {
                    this.handlePaymentFailure(result.message);
                } else if (result.status === 'pending') {
                    this.currentRetries++;
                    if (this.currentRetries >= this.maxRetries) {
                        this.handlePaymentTimeout();
                    }
                }
            }
        } catch (error) {
            console.error('Payment status check failed:', error);
        }
    }
    
    async checkPaymentStatusNow() {
        const checkoutRequestId = this.extractCheckoutRequestId();
        if (checkoutRequestId) {
            await this.checkPaymentStatus(checkoutRequestId);
        }
    }
    
    extractCheckoutRequestId() {
        // Extract from current page or URL
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('checkout_request_id');
    }
    
    handlePaymentSuccess() {
        clearInterval(this.paymentCheckInterval);
        
        this.showNotification('Payment successful! Redirecting to confirmation page...', 'success');
        
        // Send success message
        this.sendPaymentSuccessMessage();
        
        setTimeout(() => {
            window.location.href = '/order-complete/';
        }, 2000);
    }
    
    handlePaymentFailure(message) {
        clearInterval(this.paymentCheckInterval);
        
        this.showNotification(`Payment failed: ${message}`, 'error');
        
        setTimeout(() => {
            window.location.href = '/checkout/';
        }, 3000);
    }
    
    handlePaymentTimeout() {
        clearInterval(this.paymentCheckInterval);
        
        this.showNotification('Payment timeout. Please try again.', 'warning');
        
        setTimeout(() => {
            window.location.href = '/checkout/';
        }, 3000);
    }
    
    async sendPaymentSuccessMessage() {
        try {
            await fetch('/api/send-payment-success/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
        } catch (error) {
            console.log('Success message failed:', error);
        }
    }
    
    checkFormValidity() {
        const form = document.getElementById('checkout-form');
        const submitBtn = document.getElementById('place-order-btn');
        
        if (form && submitBtn) {
            const isValid = form.checkValidity();
            submitBtn.disabled = !isValid;
            
            if (isValid) {
                submitBtn.classList.add('btn-success');
                submitBtn.classList.remove('btn-primary');
            } else {
                submitBtn.classList.add('btn-primary');
                submitBtn.classList.remove('btn-success');
            }
        }
    }
    
    showLoadingState(button) {
        if (button) {
            button.disabled = true;
            const btnText = button.querySelector('.btn-text');
            const btnLoading = button.querySelector('.btn-loading');
            
            if (btnText) btnText.style.display = 'none';
            if (btnLoading) btnLoading.style.display = 'inline';
        }
    }
    
    hideLoadingState() {
        const button = document.getElementById('place-order-btn');
        if (button) {
            button.disabled = false;
            const btnText = button.querySelector('.btn-text');
            const btnLoading = button.querySelector('.btn-loading');
            
            if (btnText) btnText.style.display = 'inline';
            if (btnLoading) btnLoading.style.display = 'none';
        }
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // Remove existing notifications
        const existing = document.querySelectorAll('.payment-notification');
        existing.forEach(el => el.remove());
        
        const notification = document.createElement('div');
        notification.className = `payment-notification alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}

// Initialize payment handler when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.paymentHandler = new PaymentHandler();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PaymentHandler;
}