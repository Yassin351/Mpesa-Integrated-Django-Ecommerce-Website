import os
import logging
from pyngrok import ngrok, conf
from django.conf import settings

logger = logging.getLogger(__name__)

class NgrokManager:
    """Manages ngrok tunnels for local development"""
    
    def __init__(self):
        self.tunnel = None
        self.public_url = None
        
    def start_tunnel(self, port=8000, auth_token=None):
        """Start ngrok tunnel and return public URL"""
        try:
            # Set auth token if provided
            if auth_token:
                ngrok.set_auth_token(auth_token)
            elif os.environ.get('NGROK_AUTH_TOKEN'):
                ngrok.set_auth_token(os.environ.get('NGROK_AUTH_TOKEN'))
            
            # Kill existing tunnels
            ngrok.kill()
            
            # Start new tunnel
            self.tunnel = ngrok.connect(port, "http")
            self.public_url = self.tunnel.public_url
            
            logger.info(f"Ngrok tunnel started: {self.public_url}")
            return self.public_url
            
        except Exception as e:
            logger.error(f"Failed to start ngrok tunnel: {e}")
            return None
    
    def stop_tunnel(self):
        """Stop the ngrok tunnel"""
        try:
            if self.tunnel:
                ngrok.disconnect(self.tunnel.public_url)
                self.tunnel = None
                self.public_url = None
                logger.info("Ngrok tunnel stopped")
        except Exception as e:
            logger.error(f"Error stopping tunnel: {e}")
    
    def get_public_url(self):
        """Get the current public URL"""
        return self.public_url
    
    def update_callback_urls(self):
        """Update M-Pesa callback URLs with ngrok URL"""
        if not self.public_url:
            return False
            
        try:
            # Update environment variables for current session
            os.environ['MPESA_CALLBACK_URL'] = f"{self.public_url}/mpesa/callback/"
            os.environ['PESAPAL_CALLBACK_URL'] = f"{self.public_url}/payment/callback/"
            os.environ['PESAPAL_IPN_URL'] = f"{self.public_url}/payment/ipn/"
            
            # Update Django settings if they exist
            if hasattr(settings, 'MPESA_CALLBACK_URL'):
                settings.MPESA_CALLBACK_URL = f"{self.public_url}/mpesa/callback/"
            if hasattr(settings, 'PESAPAL_CALLBACK_URL'):
                settings.PESAPAL_CALLBACK_URL = f"{self.public_url}/payment/callback/"
            if hasattr(settings, 'PESAPAL_IPN_URL'):
                settings.PESAPAL_IPN_URL = f"{self.public_url}/payment/ipn/"
            
            logger.info(f"Updated callback URLs with ngrok URL: {self.public_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update callback URLs: {e}")
            return False

# Global instance
ngrok_manager = NgrokManager()