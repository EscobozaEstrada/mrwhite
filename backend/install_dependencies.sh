#!/bin/bash

# This script installs the necessary system dependencies for the backend

echo "Installing system dependencies..."

# Check the operating system
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    echo "Detected macOS"
    if command -v brew &> /dev/null; then
        echo "Installing wkhtmltopdf via Homebrew..."
        brew install wkhtmltopdf
    else
        echo "Homebrew not found. Please install Homebrew first: https://brew.sh/"
        echo "Then run: brew install wkhtmltopdf"
    fi
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    # Linux
    echo "Detected Linux"
    if command -v apt-get &> /dev/null; then
        echo "Installing wkhtmltopdf via apt-get..."
        sudo apt-get update
        sudo apt-get install -y wkhtmltopdf
    elif command -v yum &> /dev/null; then
        echo "Installing wkhtmltopdf via yum..."
        sudo yum install -y wkhtmltopdf
    else
        echo "Could not determine package manager. Please install wkhtmltopdf manually."
    fi
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ] || [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
    # Windows
    echo "Detected Windows"
    echo "Please download and install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html"
    echo "Make sure to add it to your PATH after installation."
else
    echo "Unsupported operating system. Please install wkhtmltopdf manually: https://wkhtmltopdf.org/downloads.html"
fi

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Dependencies installation completed!"
echo "If you encounter any issues with wkhtmltopdf, please install it manually from: https://wkhtmltopdf.org/downloads.html" 