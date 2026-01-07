#!/usr/bin/env python3
"""
Simple Phone Number Test for M-Pesa
"""

def test_your_number():
    """Test and fix your phone number"""
    your_number = "25411458760"
    print(f"Your current number: {your_number}")
    print(f"Length: {len(your_number)} digits")
    print()
    
    print("Issue: Kenyan mobile numbers need 12 digits total (254 + 9 digits)")
    print("Your number has only 11 digits, missing 1 digit")
    print()
    
    print("Possible corrections:")
    
    # Common fixes
    fixes = [
        "254114587601",  # Added 1 at the end
        "254714587601",  # Changed to 07 format (most common)
        "254111458760",  # Added 1 after 254
        "254011458760",  # Added 0 after 254
    ]
    
    for i, fix in enumerate(fixes, 1):
        print(f"{i}. {fix} (Length: {len(fix)})")
    
    print()
    print("Most likely correct format: 254714587601")
    print("This converts 0714587601 to international format")
    print()
    
    # Test M-Pesa test numbers
    print("For testing M-Pesa, you can also use these test numbers:")
    test_numbers = [
        "254700000000",  # Success after 10 seconds
        "254711111111",  # Cancelled after 15 seconds  
        "254722222222",  # Failed after 20 seconds
    ]
    
    for test_num in test_numbers:
        print(f"- {test_num}")
    
    return "254714587601"  # Most likely correct format

if __name__ == "__main__":
    corrected = test_your_number()
    print(f"\nRecommended number to use: {corrected}")