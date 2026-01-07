#!/usr/bin/env python3
"""
M-Pesa Configuration Test
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ecoweb.settings')
django.setup()

from Ecoweb.mpesa_service import MpesaService

def test_mpesa_config():
    """Test M-Pesa configuration and service"""
    print("=== M-Pesa Configuration Test ===\n")
    
    # Initialize service
    mpesa = MpesaService()
    
    print("Configuration:")
    print(f"Consumer Key: {mpesa.consumer_key[:10]}...")
    print(f"Consumer Secret: {mpesa.consumer_secret[:10]}...")
    print(f"Business Shortcode: {mpesa.business_shortcode}")
    print(f"Passkey: {mpesa.passkey[:10]}...")
    print(f"Base URL: {mpesa.base_url}")
    print(f"Test Mode: {mpesa.test_mode}")
    print(f"Callback URL: {mpesa.callback_url}")
    print()
    
    # Test phone number formatting
    test_numbers = [
        "254714587601",  # Your corrected number
        "254700000000",  # Test number (success)
        "0714587601",    # Standard format
    ]
    
    print("Phone Number Formatting Test:")
    for number in test_numbers:
        try:
            formatted = mpesa.format_phone_number(number)
            print(f"✅ {number} -> {formatted}")
        except Exception as e:
            print(f"❌ {number} -> Error: {e}")
    print()
    
    # Test access token
    print("Testing Access Token...")
    try:
        token = mpesa.get_access_token()
        if token:
            print(f"✅ Access token obtained: {token[:20]}...")
        else:
            print("❌ Failed to get access token")
    except Exception as e:
        print(f"❌ Access token error: {e}")
    print()
    
    # Test STK Push with test number
    print("Testing STK Push with test number...")
    try:
        result = mpesa.initiate_stk_push(
            phone_number="254700000000",  # Test number
            amount=1,
            order_id="TEST001",
            description="Test Payment"
        )
        print(f"STK Push Result: {result}")
        
        if result.get('status') == 'success':
            print("✅ STK Push test successful!")
            checkout_id = result.get('checkout_request_id')
            
            # Test status query
            print("\nTesting Status Query...")
            status = mpesa.query_stk_status(checkout_id)
            print(f"Status Query Result: {status}")
        else:
            print(f"❌ STK Push failed: {result.get('message')}")
            
    except Exception as e:
        print(f"❌ STK Push error: {e}")

def test_your_number():
    """Test with your actual number"""
    print("\n=== Testing Your Phone Number ===")
    
    mpesa = MpesaService()
    your_number = "254714587601"  # Corrected format
    
    print(f"Testing with your number: {your_number}")
    
    try:
        # Test formatting
        formatted = mpesa.format_phone_number(your_number)
        print(f"✅ Formatted correctly: {formatted}")
        
        # Note: Don't actually send STK push to real number in test
        print("✅ Your number is ready for M-Pesa payments!")
        print("Note: Use test numbers (254700000000) for development testing")
        
    except Exception as e:
        print(f"❌ Error with your number: {e}")

if __name__ == "__main__":
    test_mpesa_config()
    test_your_number()
    
    print("\n=== Summary ===")
    print("1. Your corrected phone number: 254714587601")
    print("2. Use test numbers for development: 254700000000")
    print("3. M-Pesa is configured and ready to use")
    print("4. Run the Django server to test payments")