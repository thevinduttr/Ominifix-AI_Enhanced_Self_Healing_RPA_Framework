#!/bin/bash

# Run SLIIT PDP RPA Bot from Terminal
# This bot connects to the Docker-based orchestrator for self-healing

echo "=========================================="
echo "SLIIT PDP RPA Bot - Terminal Mode"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✅ Python is available"
python3 --version
echo ""

# Navigate to bot directory
cd "$(dirname "$0")/sliit_pdp_rpa"

# Check if venv exists, if not create it
if [ ! -d venv ]; then
    echo "🔨 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "⚙️  Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt --upgrade
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies installed"
echo ""

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install Playwright browsers"
    exit 1
fi
echo "✅ Playwright browsers installed"
echo ""

# Display configuration info
echo "⚙️  Configuration:"
echo "   Bot ID: sliit_pdp_rpa_bot"
echo "   Orchestrator: http://localhost:8000"
echo "   Config File: config/settings.yml"
echo ""

# Run the bot
echo "🚀 Starting bot..."
echo "=========================================="
echo ""

python3 src/main.py

# If we get here, bot exited
echo ""
echo "=========================================="
echo "⚠️  Bot exited"
