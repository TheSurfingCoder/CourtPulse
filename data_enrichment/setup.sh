#!/bin/bash

# CourtPulse Data Enrichment Pipeline Setup Script

echo "CourtPulse Data Enrichment Pipeline Setup"
echo "=========================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    echo "Please install pip3 and try again."
    exit 1
fi

echo "✅ pip3 found"

# Create and activate virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env file with your database credentials"
else
    echo "✅ .env file already exists"
fi

# Check if PostgreSQL is installed (optional check)
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL found: $(psql --version)"
else
    echo "⚠️  PostgreSQL not found in PATH"
    echo "   Make sure PostgreSQL with PostGIS is installed and running"
fi

# Run setup test
echo ""
echo "Running setup tests..."
python test_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your database credentials"
    echo "2. Ensure PostgreSQL with PostGIS is running"
    echo "3. Activate virtual environment: source venv/bin/activate"
    echo "4. Run: python example_usage.py"
    echo "5. Or run: python data_enrichment.py"
else
    echo ""
    echo "❌ Setup tests failed. Please check the errors above."
    exit 1
fi
