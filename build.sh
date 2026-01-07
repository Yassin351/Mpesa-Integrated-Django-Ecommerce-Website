#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade build tools first
pip install --upgrade pip setuptools wheel

# Install requirements with binary wheels when possible
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate