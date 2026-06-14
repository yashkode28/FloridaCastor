#!/bin/bash
# Setup script for FloridaCastor project

echo "Installing required packages..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Verifying installation..."
python3 -c "import requests; import bs4; print('✓ All packages installed successfully!')"
