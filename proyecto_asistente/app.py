
from fastapi import FastAPI
from routes.whatsapp import whatsapp_webhook

app = FastAPI()

app.include_router(whatsapp_webhook, prefix="/webhook", tags=["WhatsApp"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
