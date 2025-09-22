# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Facebook Messenger chatbot that uses GPT for intent detection and responds with predefined messages. The system processes incoming messages, analyzes user intent with OpenAI's API, and sends appropriate replies back through Facebook's Send API.

## Architecture

The project follows a modular architecture with three core components:

1. **FastAPI Server** (`main.py`) - Handles Facebook webhook events, verifies signatures, and manages the request/response flow
2. **Intent Detection** (`intent_detector.py`) - Uses OpenAI GPT to analyze user messages and map them to predefined intents
3. **Response Configuration** (`replies.json`) - Static JSON file containing intent definitions and corresponding reply messages

### Key Design Patterns

- **Intent-Based Routing**: Messages are classified into intents (greeting, price, shipping, order) with confidence thresholds
- **Fallback Handling**: Uses confidence threshold (≥ 0.55) to determine whether to use detected intent or fallback response
- **Background Processing**: Message processing happens asynchronously to avoid blocking webhook responses
- **Environment-Based Configuration**: All sensitive data (API keys, tokens) managed through `.env` files

## Development Commands

### Setup and Dependencies
```bash
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
```

### Local Testing
```bash
python test_bot.py  # Interactive testing without Facebook integration
```

### Running the Server
```bash
python main.py  # Starts FastAPI server on localhost:8000
```

### Testing API Endpoints
```bash
# Test intent detection directly
curl -X POST "http://localhost:8000/test-message" \
     -H "Content-Type: application/json" \
     -d '{"text": "สวัสดีครับ"}'
```

## Configuration Management

### Adding New Intents
Edit `replies.json` to add new intent categories:
```json
{
  "new_intent": {
    "description": "Intent description for GPT",
    "reply": "Response message to users"
  }
}
```

### Environment Variables Required
- `OPENAI_API_KEY` - For GPT intent analysis
- `PAGE_ACCESS_TOKEN` - Facebook Page access token (production)
- `VERIFY_TOKEN` - Facebook webhook verification (production)
- `APP_SECRET` - Facebook app secret for signature verification (production)

## Key Implementation Details

### Intent Detection Flow
1. User message → GPT analysis with available intents as context
2. GPT returns JSON with intent, confidence (0.0-1.0), and reasoning
3. If confidence ≥ 0.55 and intent != 'none' → use detected intent
4. Otherwise → use fallback response

### Facebook Integration
- Webhook verification at `/webhook` (GET)
- Message processing at `/webhook` (POST)
- HMAC signature verification using APP_SECRET
- Background task processing to avoid webhook timeouts

### Local Development
The `test_bot.py` script allows testing intent detection without Facebook integration, supporting both batch testing with predefined messages and interactive mode for real-time testing.