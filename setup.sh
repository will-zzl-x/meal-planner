#!/bin/bash

# Meal Planner - Development Setup Script

echo "🍽️ Setting up Meal Planner development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  source venv/bin/activate"
echo "  streamlit run app.py"
echo ""
echo "To run tests:"
echo "  source venv/bin/activate"
echo "  python -m pytest src/core/services/test_*.py -v"
