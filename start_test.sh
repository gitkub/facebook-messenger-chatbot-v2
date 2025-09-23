#!/bin/bash

echo "🚀 Starting Local Chatbot Test..."
echo

# Load environment variables from .env file
if [ -f .env ]; then
    echo "🔑 Loading API key from .env file..."
    export $(grep -v '^#' .env | grep -v '^$' | xargs)

    if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
        echo "✅ API key loaded successfully"
    else
        echo "⚠️  Warning: API key not found or not set properly in .env"
        echo "   Smart fallback will show error messages"
    fi
else
    echo "⚠️  .env file not found"
    echo "   Smart fallback will show error messages"
fi

echo
echo "▶️  Starting interactive test..."
python3 local_test.py