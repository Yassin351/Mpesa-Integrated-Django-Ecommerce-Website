#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade build tools first
pip install --upgrade pip setuptools wheel

# Install Pillow with binary wheel to avoid compilation
pip install --only-binary=:all: Pillow==10.3.0

# Install remaining requirements
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate