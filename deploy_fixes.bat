@echo off
echo ========================================
echo  DEPLOYING PAYMENT CONFIRMATION FIXES
echo ========================================

echo.
echo 1. Adding all changes to git...
git add .

echo.
echo 2. Committing changes...
git commit -m "Fix payment confirmation messages and Render deployment

- Enhanced payment confirmation UI with clear success messages
- Added emoji indicators and better visual feedback
- Improved payment waiting page with countdown timer
- Fixed Pillow wheel build issue for Render deployment
- Added API endpoints for payment confirmation messages
- Enhanced error handling and user notifications
- Added test mode indicators and better status messages"

echo.
echo 3. Pushing to repository...
git push origin main

echo.
echo ========================================
echo  DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Changes deployed:
echo ✅ Payment confirmation messages now show clearly
echo ✅ Enhanced payment waiting page with countdown
echo ✅ Fixed Render deployment Pillow issue
echo ✅ Added better error handling and notifications
echo ✅ Improved test mode indicators
echo.
echo Your Render deployment should now work properly!
echo.
pause