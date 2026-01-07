@echo off
echo Starting Django server with ngrok tunnel...
echo.
echo Make sure you have:
echo 1. Installed ngrok: https://ngrok.com/download
echo 2. Set NGROK_AUTH_TOKEN environment variable (optional but recommended)
echo.
python manage.py runserver_ngrok
pause