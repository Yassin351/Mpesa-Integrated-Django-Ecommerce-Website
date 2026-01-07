#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade build tools first
pip install --upgrade pip setuptools wheel

# Install Pillow with binary wheel to avoid compilation issues
pip install --only-binary=:all: Pillow==10.3.0

# Install remaining requirements (excluding Pillow since we installed it above)
grep -v "^Pillow" requirements.txt > temp_requirements.txt || cp requirements.txt temp_requirements.txt
pip install -r temp_requirements.txt
rm -f temp_requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate