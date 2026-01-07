#!/usr/bin/env python3
"""
Phone Number Validation Test Script
This script tests phone number formatting for M-Pesa integration
"""

import re

def format_phone_number(phone):
    """Format phone number to proper Kenyan format"""
    print(f"Input phone: {phone}")
    
    # Remove all non-digits
    phone = re.sub(r'\D', '', phone)
    print(f"Digits only: {phone}")
    
    # Handle different formats
    if phone.startswith('0'):
        phone = '254' + phone[1:]
        print(f"Converted from 0 format: {phone}")
    elif phone.startswith('254'):
        print(f"Already in 254 format: {phone}")
    elif phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone
        print(f"Added 254 prefix: {phone}")
    
    # Validate length (should be 12 digits: 254 + 9 digits)
    if len(phone) != 12:
        raise ValueError(f"Invalid phone number format. Expected 12 digits, got {len(phone)}. Phone: {phone}")
    
    # Validate it's a valid Kenyan number
    if not phone.startswith('254'):
        raise ValueError("Phone number must be a Kenyan number starting with 254")
    
    # Additional validation for Kenyan mobile networks
    valid_prefixes = ['2547', '2541']  # Safaricom (07xx) and Airtel (01xx)
    if not any(phone.startswith(prefix) for prefix in valid_prefixes):
        print(f"Warning: Phone number {phone} may not be a valid Kenyan mobile number")
    
    return phone

def test_phone_numbers():
    """Test various phone number formats"""
    test_numbers = [
        "25411458760",  # Your number (missing digit)
        "254114587601", # Your number with extra digit
        "0714587601",   # Standard Kenyan format
        "254714587601", # International format
        "714587601",    # Without country code
        "+254714587601" # With plus sign
    ]
    
    print("=== Phone Number Validation Test ===\n")
    
    for number in test_numbers:
        print(f"Testing: {number}")
        try:
            formatted = format_phone_number(number)
            print(f"✅ Valid: {formatted}")
        except ValueError as e:
            print(f"❌ Error: {e}")
        print("-" * 50)

if __name__ == "__main__":
    test_phone_numbers()
    
    print("\n=== Your Phone Number Analysis ===")
    your_number = "25411458760"
    print(f"Your number: {your_number}")
    print(f"Length: {len(your_number)} digits")
    print("Issue: Kenyan phone numbers should be 12 digits when including country code (254)")
    print("Expected format: 254 + 9 digits = 12 digits total")
    print("\nPossible corrections:")
    print("1. If missing a digit: 254114587601 (added '1')")
    print("2. If it's a landline: Use mobile number for M-Pesa")
    print("3. Check with your network provider for correct format")