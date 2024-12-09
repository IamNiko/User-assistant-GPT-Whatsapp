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
- ngrok (for local development)

## Setup

1. Install requirements: `pip install -r requirements.txt`

2. Configure environment variables in `.env`:

```
OPENAI_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

3. Initialize ngrok:

   - Download and install ngrok from https://ngrok.com/download
   - If you haven't already, create an account and get your auth token
   - Authenticate ngrok: `ngrok config add-authtoken YOUR_AUTH_TOKEN`
   - Start ngrok on port 8000 (FastAPI default port):
     ```
     ngrok http 8000
     ```
   - Copy the HTTPS URL provided by ngrok (e.g., https://xxxx-xx-xx-xxx-xx.ngrok.io)
   - Configure this URL in your Twilio WhatsApp Sandbox settings as the webhook URL

4. Run server: `uvicorn main:app --reload`

## Authors

- Nicolas Gentile
