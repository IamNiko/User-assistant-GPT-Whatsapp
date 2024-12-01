# WhatsApp GPT Assistant Bot

Integration between Twilio WhatsApp and OpenAI's GPT for an automated customer support system.

## Features
- Customer and staff support flows
- Auto-response system
- Payment and refund handling
- Technical troubleshooting
- State management for conversations

## Technologies
- FastAPI
- Twilio API
- OpenAI API
- Python 3.x
- SQLAlchemy

## Setup
1. Install requirements: `pip install -r requirements.txt`
2. Configure environment variables in `.env`:
  ```
  OPENAI_API_KEY=your_key
  TWILIO_ACCOUNT_SID=your_sid
  TWILIO_AUTH_TOKEN=your_token
  ```
3. Run server: `uvicorn main:app --reload`

## Authors
- Nicolas Gentile
