@echo off
echo ========================================
echo    M-Pesa Django E-commerce Testing
echo ========================================
echo.
echo Starting optimized M-Pesa integration...
echo.
echo Features:
echo - Fast 2-3 second status checks
echo - Test mode for localhost development  
echo - Real-time payment monitoring
echo - Auto-retry mechanisms
echo.
echo Test Phone Numbers (Localhost Only):
echo - 0700000000 : Success after 10 seconds
echo - 0711111111 : Cancelled after 15 seconds
echo - 0722222222 : Failed after 20 seconds
echo.
echo Starting Django development server...
echo.
python manage.py runserver
pause