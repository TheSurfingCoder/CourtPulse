#!/bin/bash

# Activate the virtual environment for CourtPulse Data Enrichment

echo "🏀 Activating CourtPulse Data Enrichment Environment"
echo "=================================================="

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run ./setup.sh first to create the environment"
    exit 1
fi

echo "✅ Activating virtual environment..."
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo ""
echo "Available commands:"
echo "  python test_setup.py          - Test your setup"
echo "  python data_enrichment.py     - Run the main pipeline"
echo "  python example_usage.py       - See usage examples"
echo "  python test_my_geojson.py <file> - Test your GeoJSON file"
echo ""
echo "To deactivate, run: deactivate"

