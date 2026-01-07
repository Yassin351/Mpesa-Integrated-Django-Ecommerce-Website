"""
WSGI entry point for Render deployment.
This file provides the 'app' module that Gunicorn expects.
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Ecoweb.settings')

# Create the WSGI application
app = get_wsgi_application()