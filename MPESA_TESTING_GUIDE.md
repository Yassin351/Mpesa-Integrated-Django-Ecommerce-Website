# M-Pesa Localhost Testing Guide

## 🚀 Quick Start

### 1. Test Mode (Localhost Only)
For localhost development, the system automatically enables test mode with simulated payments.

**Test Phone Numbers:**
- `254700000000` or `0700000000` - ✅ Success after 10 seconds
- `254711111111` or `0711111111` - ❌ Cancelled after 15 seconds  
- `254722222222` or `0722222222` - ⚠️ Failed after 20 seconds

### 2. Start Development Server

**Option A: Regular Django Server**
```bash
python manage.py runserver
```

**Option B: With Ngrok (for webhook testing)**
```bash
python manage.py runserver_ngrok
```

### 3. Testing Process

1. **Add items to cart** and proceed to checkout
2. **Fill billing details** and select "M-Pesa" as payment method
3. **Use a test phone number** from the list above
4. **Submit the form** - you'll be redirected to payment waiting page
5. **Watch the real-time updates** as the payment processes
6. **Payment completes automatically** based on the test phone number used

### 4. Features

✨ **Fast Processing**: 2-3 second status checks  
🧪 **Test Mode**: No real API calls on localhost  
⚡ **Real-time Updates**: Live payment status monitoring  
🔄 **Auto Retry**: Built-in error handling and retry mechanisms  
📱 **Responsive UI**: Works on mobile and desktop  

### 5. Production Setup

When ready for production:

1. **Set environment variables:**
   ```bash
   MPESA_TEST_MODE=False
   MPESA_CALLBACK_URL=https://yourdomain.com/mpesa/callback/
   ```

2. **Use ngrok for webhook testing:**
   ```bash
   python manage.py runserver_ngrok
   ```

3. **Configure Safaricom with your webhook URL**

### 6. Troubleshooting

**Payment stuck on "Processing"?**
- Check browser console for errors
- Verify test phone number format
- Ensure Django server is running

**Ngrok not working?**
- Install ngrok: https://ngrok.com/download
- Set NGROK_AUTH_TOKEN environment variable (optional)

**Real API not responding?**
- Check your M-Pesa credentials in settings.py
- Verify callback URL is accessible from internet
- Check Safaricom API status

### 7. API Credentials (Already Configured)

The following sandbox credentials are pre-configured:
- **Consumer Key**: `Idhdf8LGK7uh4gcJxuea7rSVIj564vGUPEjlVUQWBh68LIaz`
- **Consumer Secret**: `UTS83VvF48J9CNJXIg9YFPPOyl0s8xP2EksvRoLECLBJ9d4yl7JoRaOei9WxOdHo`
- **Passkey**: `bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919`
- **Business Shortcode**: `247247`

### 8. Test Script

Run the test script to verify setup:
```bash
python test_mpesa_localhost.py
```

---

**Happy Testing! 🎉**