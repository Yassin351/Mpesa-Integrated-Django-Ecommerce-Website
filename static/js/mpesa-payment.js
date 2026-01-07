/**
 * M-Pesa Payment Handler - Optimized for faster processing
 * Handles real-time payment status checking and UI updates
 */

class MpesaPaymentHandler {
    constructor(checkoutRequestId, statusUrl, completeUrl, checkoutUrl) {
        this.checkoutRequestId = checkoutRequestId;
        this.statusUrl = statusUrl;
        this.completeUrl = completeUrl;
        this.checkoutUrl = checkoutUrl;
        this.checkInterval = null;
        this.checkCount = 0;
        this.maxChecks = 120; // 10 minutes with faster intervals
        this.isTestMode = this.checkoutRequestId && this.checkoutRequestId.startsWith('test_');
        
        this.init();
    }
    
    init() {
        if (this.checkoutRequestId) {
            this.startStatusChecking();
        }
        
        this.setupEventListeners();
        this.showTestModeInfo();
    }
    
    startStatusChecking() {
        // Check immediately after 1 second for faster response
        setTimeout(() => this.checkPaymentStatus(), 1000);
        
        // Use different intervals based on test mode
        const interval = this.isTestMode ? 2000 : 3000; // 2s for test, 3s for real
        this.checkInterval = setInterval(() => this.checkPaymentStatus(), interval);
    }
    
    checkPaymentStatus() {
        if (this.checkCount >= this.maxChecks) {
            this.stopChecking();
            this.showTimeoutMessage();
            return;
        }
        
        this.checkCount++;
        
        // Show progress for test mode
        if (this.isTestMode) {
            this.updateTestProgress();
        }
        
        fetch(this.statusUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Payment status:', data.status);
            this.handleStatusResponse(data);
        })
        .catch(error => {
            console.error('Error checking payment status:', error);
            // Don't show error immediately, continue checking
            if (this.checkCount > 10) {
                this.showConnectionError();
            }
        });
    }
    
    handleStatusResponse(data) {
        switch(data.status) {
            case 'success':
                this.stopChecking();
                this.showSuccessMessage();
                setTimeout(() => {
                    window.location.href = this.completeUrl;
                }, 1500); // Faster redirect
                break;
                
            case 'failed':
                this.stopChecking();
                this.showFailedMessage();
                break;
                
            case 'cancelled':
                this.stopChecking();
                this.showCancelledMessage();
                break;
                
            default:
                // Continue checking for pending status
                this.updatePendingMessage();
                break;
        }
    }
    
    updateTestProgress() {
        const elapsed = this.checkCount * 2; // 2 seconds per check
        let message = 'Simulating M-Pesa payment...';
        
        if (elapsed > 8) {
            message = 'Processing payment (this may take a moment)...';
        }
        if (elapsed > 15) {
            message = 'Finalizing transaction...';
        }
        
        this.updateStatusMessage(message);
    }
    
    updatePendingMessage() {
        const elapsed = Math.floor(this.checkCount * 3 / 60); // minutes
        let message = 'Waiting for payment confirmation...';
        
        if (elapsed > 1) {
            message = `Still waiting... (${elapsed} minute${elapsed > 1 ? 's' : ''})`;
        }
        
        this.updateStatusMessage(message);
    }
    
    showTestModeInfo() {
        if (this.isTestMode) {
            const alert = document.getElementById('paymentAlert');
            if (alert) {
                alert.innerHTML = `
                    <h4><i class="fa fa-flask text-info"></i> Test Mode Active</h4>
                    <p><strong>This is a test payment - no real money will be charged.</strong></p>
                    <p>The payment will be automatically processed in a few seconds.</p>
                    <hr>
                    <p><small>
                        Test Details:<br>
                        Mode: <strong>Localhost Testing</strong><br>
                        Amount: <strong>KES ${window.testAmount || 'N/A'}</strong>
                    </small></p>
                `;
                alert.className = 'alert alert-info';
            }
        }
    }
    
    stopChecking() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }
    
    showSuccessMessage() {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-check-circle text-success"></i> Payment Successful!');
        this.updateAlert('alert-success', `
            <h4><i class="fa fa-check"></i> Payment Completed</h4>
            <p>Your ${this.isTestMode ? 'test ' : ''}M-Pesa payment has been processed successfully!</p>
            <p><strong>Redirecting to order confirmation...</strong></p>
        `);
        this.updateStatusMessage('Payment confirmed! Redirecting...');
    }
    
    showFailedMessage() {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-times-circle text-danger"></i> Payment Failed');
        this.updateAlert('alert-danger', `
            <h4><i class="fa fa-times"></i> Payment Failed</h4>
            <p>Your M-Pesa payment could not be processed.</p>
            <p><strong>Please try again or use a different payment method.</strong></p>
            ${this.isTestMode ? '<p><em>This was a test transaction.</em></p>' : ''}
        `);
        this.updateStatusMessage('Please try again or contact support if the problem persists.');
        this.showRetryButton();
    }
    
    showCancelledMessage() {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-ban text-warning"></i> Payment Cancelled');
        this.updateAlert('alert-warning', `
            <h4><i class="fa fa-ban"></i> Payment Cancelled</h4>
            <p>You cancelled the M-Pesa payment request.</p>
            <p><strong>You can try again or use a different payment method.</strong></p>
            ${this.isTestMode ? '<p><em>This was a test transaction.</em></p>' : ''}
        `);
        this.updateStatusMessage('Payment was cancelled by user.');
        this.showRetryButton();
    }
    
    showTimeoutMessage() {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-clock-o text-warning"></i> Payment Timeout');
        this.updateAlert('alert-warning', `
            <h4><i class="fa fa-clock-o"></i> Payment Timeout</h4>
            <p>The payment request has timed out.</p>
            <p><strong>Please check your M-Pesa messages or try again.</strong></p>
            ${this.isTestMode ? '<p><em>This was a test transaction.</em></p>' : ''}
        `);
        this.updateStatusMessage('Payment request timed out. Please try again.');
        this.showRetryButton();
    }
    
    showConnectionError() {
        this.updateStatusMessage('Connection issues detected. Still checking...');
    }
    
    hideSpinner() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.style.display = 'none';
    }
    
    updateTitle(html) {
        const title = document.getElementById('paymentTitle');
        if (title) title.innerHTML = html;
    }
    
    updateAlert(className, html) {
        const alert = document.getElementById('paymentAlert');
        if (alert) {
            alert.className = `alert ${className}`;
            alert.innerHTML = html;
        }
    }
    
    updateStatusMessage(text) {
        const message = document.getElementById('statusMessage');
        if (message) message.textContent = text;
    }
    
    showRetryButton() {
        const retryBtn = document.getElementById('retryPayment');
        if (retryBtn) retryBtn.style.display = 'inline-block';
    }
    
    setupEventListeners() {
        const retryBtn = document.getElementById('retryPayment');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                window.location.href = this.checkoutUrl;
            });
        }
        
        // Handle page visibility changes to pause/resume checking
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, reduce check frequency
                if (this.checkInterval) {
                    clearInterval(this.checkInterval);
                    this.checkInterval = setInterval(() => this.checkPaymentStatus(), 10000);
                }
            } else {
                // Page is visible, resume normal frequency
                if (this.checkInterval) {
                    clearInterval(this.checkInterval);
                    const interval = this.isTestMode ? 2000 : 3000;
                    this.checkInterval = setInterval(() => this.checkPaymentStatus(), interval);
                }
            }
        });
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const checkoutRequestId = window.checkoutRequestId;
    const statusUrl = window.statusUrl;
    const completeUrl = window.completeUrl;
    const checkoutUrl = window.checkoutUrl;
    
    if (checkoutRequestId && statusUrl) {
        new MpesaPaymentHandler(checkoutRequestId, statusUrl, completeUrl, checkoutUrl);
    }
});