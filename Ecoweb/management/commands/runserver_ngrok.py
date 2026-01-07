import os
import sys
import threading
import time
from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from Ecoweb.ngrok_utils import ngrok_manager

class Command(BaseCommand):
    help = 'Start Django development server with ngrok tunnel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to run the server on (default: 8000)'
        )
        parser.add_argument(
            '--ngrok-token',
            type=str,
            help='Ngrok auth token (optional, can also use NGROK_AUTH_TOKEN env var)'
        )

    def handle(self, *args, **options):
        port = options['port']
        auth_token = options.get('ngrok_token')
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting Django server with ngrok tunnel on port {port}...')
        )
        
        # Start ngrok tunnel in a separate thread
        def start_ngrok():
            time.sleep(2)  # Wait for Django to start
            public_url = ngrok_manager.start_tunnel(port=port, auth_token=auth_token)
            if public_url:
                ngrok_manager.update_callback_urls()
                self.stdout.write(
                    self.style.SUCCESS(f'\n🌐 Public URL: {public_url}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'📱 M-Pesa Callback: {public_url}/mpesa/callback/')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'💳 Pesapal Callback: {public_url}/payment/callback/')
                )
                self.stdout.write(
                    self.style.WARNING('\n⚠️  Use this public URL for M-Pesa webhook configuration')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to start ngrok tunnel')
                )
        
        # Start ngrok in background
        ngrok_thread = threading.Thread(target=start_ngrok)
        ngrok_thread.daemon = True
        ngrok_thread.start()
        
        try:
            # Start Django development server
            sys.argv = ['manage.py', 'runserver', f'0.0.0.0:{port}']
            execute_from_command_line(sys.argv)
        except KeyboardInterrupt:
            self.stdout.write('\n🛑 Shutting down...')
            ngrok_manager.stop_tunnel()
            self.stdout.write(self.style.SUCCESS('✅ Server and tunnel stopped'))