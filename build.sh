#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."

# Upgrade build tools first
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install system dependencies for Pillow if needed
echo "Installing Pillow with binary wheel..."
pip install --only-binary=:all: Pillow==10.3.0

# Install remaining requirements (excluding Pillow since we installed it above)
echo "Installing remaining requirements..."
if grep -q "^Pillow" requirements.txt; then
    grep -v "^Pillow" requirements.txt > temp_requirements.txt
    pip install -r temp_requirements.txt
    rm -f temp_requirements.txt
else
    pip install -r requirements.txt
fi

echo "Collecting static files..."
# Collect static files
python manage.py collectstatic --no-input

echo "Running database migrations..."
# Run database migrations
python manage.py migrate

echo "Build completed successfully!"