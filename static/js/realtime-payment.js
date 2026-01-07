/**
 * Real-time M-Pesa Payment Handler
 * Supports WebSocket and Server-Sent Events for instant payment updates
 */

class RealTimePaymentHandler {
    constructor(checkoutRequestId, statusUrl, completeUrl, checkoutUrl) {
        this.checkoutRequestId = checkoutRequestId;
        this.statusUrl = statusUrl;
        this.completeUrl = completeUrl;
        this.checkoutUrl = checkoutUrl;
        this.eventSource = null;
        this.websocket = null;
        this.fallbackInterval = null;
        
        this.init();
    }
    
    init() {
        if (!this.checkoutRequestId) return;
        
        // Try WebSocket first, then SSE, then fallback to polling
        this.connectWebSocket() || this.connectSSE() || this.startPolling();
        this.setupEventListeners();
        this.sendPaymentPrompt();
    }
    
    // Send payment prompt event to localhost
    sendPaymentPrompt() {
        const promptData = {
            type: 'payment_prompt',
            checkoutRequestId: this.checkoutRequestId,
            timestamp: new Date().toISOString(),
            amount: document.querySelector('[data-amount]')?.dataset.amount || 'N/A'
        };
        
        // Send to localhost endpoint
        fetch('http://localhost:8000/api/payment-prompt/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(promptData)
        }).catch(error => console.log('Prompt event sent:', error));
        
        // Also trigger custom event
        window.dispatchEvent(new CustomEvent('paymentPromptSent', { detail: promptData }));
    }
    
    // WebSocket connection
    connectWebSocket() {
        try {
            const wsUrl = `ws://localhost:8000/ws/payment/${this.checkoutRequestId}/`;
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.showConnectionStatus('Connected via WebSocket');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handlePaymentUpdate(data);
            };
            
            this.websocket.onerror = () => {
                console.log('WebSocket failed, trying SSE...');
                return false;
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket closed');
                this.connectSSE() || this.startPolling();
            };
            
            return true;
        } catch (error) {
            return false;
        }
    }
    
    // Server-Sent Events connection
    connectSSE() {
        try {
            const sseUrl = `/api/payment-stream/${this.checkoutRequestId}/`;
            this.eventSource = new EventSource(sseUrl);
            
            this.eventSource.onopen = () => {
                console.log('SSE connected');
                this.showConnectionStatus('Connected via Server-Sent Events');
            };
            
            this.eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handlePaymentUpdate(data);
            };
            
            this.eventSource.onerror = () => {
                console.log('SSE failed, falling back to polling...');
                this.eventSource.close();
                return false;
            };
            
            return true;
        } catch (error) {
            return false;
        }
    }
    
    // Fallback polling
    startPolling() {
        console.log('Using polling fallback');
        this.showConnectionStatus('Connected via Polling');
        
        setTimeout(() => this.checkPaymentStatus(), 2000);
        this.fallbackInterval = setInterval(() => this.checkPaymentStatus(), 3000);
    }
    
    checkPaymentStatus() {
        fetch(this.statusUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => this.handlePaymentUpdate(data))
        .catch(error => console.error('Polling error:', error));
    }
    
    handlePaymentUpdate(data) {
        // Trigger custom event for external listeners
        window.dispatchEvent(new CustomEvent('paymentStatusUpdate', { detail: data }));
        
        switch(data.status) {
            case 'success':
                this.cleanup();
                this.showSuccess(data);
                setTimeout(() => window.location.href = this.completeUrl, 2000);
                break;
                
            case 'failed':
                this.cleanup();
                this.showFailure(data);
                break;
                
            case 'cancelled':
                this.cleanup();
                this.showCancelled(data);
                break;
                
            case 'timeout':
                this.cleanup();
                this.showTimeout(data);
                break;
                
            default:
                this.updateProgress(data);
                break;
        }
    }
    
    showSuccess(data) {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-check-circle text-success"></i> Payment Successful!');
        this.updateAlert('alert-success', `
            <h4><i class="fa fa-check"></i> Payment Completed</h4>
            <p>Transaction ID: <strong>${data.transaction_id || 'N/A'}</strong></p>
            <p>Your M-Pesa payment has been processed successfully!</p>
        `);
        this.updateStatus('Payment confirmed! Redirecting...');
        this.playNotificationSound('success');
    }
    
    showFailure(data) {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-times-circle text-danger"></i> Payment Failed');
        this.updateAlert('alert-danger', `
            <h4><i class="fa fa-times"></i> Payment Failed</h4>
            <p>Error: ${data.error_message || 'Unknown error'}</p>
            <p>Please try again or use a different payment method.</p>
        `);
        this.updateStatus('Payment failed. Please try again.');
        this.showRetryButton();
        this.playNotificationSound('error');
    }
    
    showCancelled(data) {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-ban text-warning"></i> Payment Cancelled');
        this.updateAlert('alert-warning', `
            <h4><i class="fa fa-ban"></i> Payment Cancelled</h4>
            <p>You cancelled the M-Pesa payment request.</p>
        `);
        this.updateStatus('Payment cancelled by user.');
        this.showRetryButton();
        this.playNotificationSound('warning');
    }
    
    showTimeout(data) {
        this.hideSpinner();
        this.updateTitle('<i class="fa fa-clock-o text-warning"></i> Payment Timeout');
        this.updateAlert('alert-warning', `
            <h4><i class="fa fa-clock-o"></i> Payment Timeout</h4>
            <p>The payment request has timed out.</p>
        `);
        this.updateStatus('Payment request timed out.');
        this.showRetryButton();
        this.playNotificationSound('warning');
    }
    
    updateProgress(data) {
        if (data.message) {
            this.updateStatus(data.message);
        }
    }
    
    // UI Helper Methods
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
    
    updateStatus(text) {
        const message = document.getElementById('statusMessage');
        if (message) message.textContent = text;
    }
    
    showRetryButton() {
        const retryBtn = document.getElementById('retryPayment');
        if (retryBtn) retryBtn.style.display = 'inline-block';
    }
    
    showConnectionStatus(status) {
        const statusEl = document.getElementById('connectionStatus');
        if (statusEl) statusEl.textContent = status;
    }
    
    playNotificationSound(type) {
        try {
            const audio = new Audio(`/static/sounds/${type}.mp3`);
            audio.volume = 0.3;
            audio.play().catch(() => {}); // Ignore if sound fails
        } catch (error) {
            // Ignore sound errors
        }
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.content || '';
    }
    
    setupEventListeners() {
        // Retry button
        const retryBtn = document.getElementById('retryPayment');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                window.location.href = this.checkoutUrl;
            });
        }
        
        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.websocket?.readyState === WebSocket.CLOSED) {
                this.connectWebSocket() || this.connectSSE() || this.startPolling();
            }
        });
        
        // Custom event listeners for external integration
        window.addEventListener('paymentPromptSent', (event) => {
            console.log('Payment prompt sent:', event.detail);
        });
        
        window.addEventListener('paymentStatusUpdate', (event) => {
            console.log('Payment status update:', event.detail);
        });
    }
    
    cleanup() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        if (this.fallbackInterval) {
            clearInterval(this.fallbackInterval);
            this.fallbackInterval = null;
        }
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const checkoutRequestId = window.checkoutRequestId;
    const statusUrl = window.statusUrl;
    const completeUrl = window.completeUrl;
    const checkoutUrl = window.checkoutUrl;
    
    if (checkoutRequestId && statusUrl) {
        window.paymentHandler = new RealTimePaymentHandler(
            checkoutRequestId, 
            statusUrl, 
            completeUrl, 
            checkoutUrl
        );
    }
});