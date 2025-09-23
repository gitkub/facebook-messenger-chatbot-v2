import hashlib
import hmac
import json
import os
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

from intent_detector import IntentDetector

# โหลด environment variables
load_dotenv()

app = FastAPI(title="Facebook Messenger Chatbot", version="1.0.0")

# Environment variables
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
APP_SECRET = os.getenv("APP_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ตรวจสอบว่ามี environment variables ครบถ้วน
if not all([PAGE_ACCESS_TOKEN, VERIFY_TOKEN, APP_SECRET, OPENAI_API_KEY]):
    print("Warning: Some environment variables are missing. Check your .env file.")

# สร้าง Intent Detector
intent_detector = IntentDetector(OPENAI_API_KEY) if OPENAI_API_KEY else None

class WebhookEntry(BaseModel):
    object: str
    entry: list

def verify_signature(payload: bytes, signature: str) -> bool:
    """ตรวจสอบ signature จาก Facebook"""
    if not APP_SECRET:
        return False

    expected_signature = hmac.new(
        APP_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected_signature}", signature)

async def send_message(recipient_id: str, message: str = None, image_url: str = None) -> bool:
    """ส่งข้อความหรือรูปภาพกลับไปยังผู้ใช้ผ่าน Facebook Send API"""
    if not PAGE_ACCESS_TOKEN:
        print("PAGE_ACCESS_TOKEN not found")
        return False

    url = f"https://graph.facebook.com/v18.0/me/messages"

    headers = {
        "Content-Type": "application/json"
    }

    # สร้าง message payload ตามประเภทที่ส่ง
    if image_url:
        message_content = {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True
                }
            }
        }
    else:
        message_content = {"text": message}

    data = {
        "recipient": {"id": recipient_id},
        "message": message_content,
        "access_token": PAGE_ACCESS_TOKEN
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)

            if response.status_code == 200:
                print(f"Message sent successfully to {recipient_id}")
                return True
            else:
                print(f"Failed to send message: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"Error sending message: {e}")
        return False

async def process_message(sender_id: str, message_text: str):
    """ประมวลผลข้อความและส่งกลับ"""
    print(f"Processing message from {sender_id}: {message_text}")

    if not intent_detector:
        await send_message(sender_id, "ระบบไม่พร้อมใช้งาน กรุณาลองใหม่ภายหลัง")
        return

    try:
        # วิเคราะห์ intent และได้รับข้อความตอบกลับ
        result = intent_detector.process_message(message_text, user_id=sender_id)

        # Log ผลลัพธ์
        print(f"Intent analysis result: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # ตรวจสอบ manual mode - ถ้าเป็น manual mode ไม่ต้องส่งข้อความ
        if result.get('used_intent') == 'manual_mode':
            print(f"User {sender_id} is in manual mode - bot will not respond")
            return

        # ตรวจสอบ waiting state - ถ้ากำลังรอข้อความเพิ่มเติม
        if result.get('used_intent') == 'waiting_for_more':
            print(f"User {sender_id} is sending rapid messages - waiting for more")
            return

        # ส่งข้อความตอบกลับ
        if 'image_url' in result and result['image_url']:
            # ส่งรูปภาพ
            await send_message(sender_id, image_url=result['image_url'])
            # ส่งข้อความตอบกลับ (ถ้ามี)
            if result['reply']:
                await send_message(sender_id, result['reply'])
        else:
            # ส่งเฉพาะข้อความ
            if result['reply']:
                await send_message(sender_id, result['reply'])

    except Exception as e:
        print(f"Error processing message: {e}")
        await send_message(sender_id, "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Facebook Messenger Chatbot is running"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Webhook verification สำหรับ Facebook"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return int(challenge)
    else:
        print("Webhook verification failed!")
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """รับ webhook events จาก Facebook Messenger"""

    # รับ raw body และ signature
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")

    # ตรวจสอบ signature (ในการใช้งานจริง)
    if APP_SECRET and not verify_signature(body, signature):
        print("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        # Parse JSON data
        data = json.loads(body.decode('utf-8'))

        # ประมวลผล webhook entries
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging in entry.get("messaging", []):

                    # ตรวจสอบว่าเป็นข้อความที่เข้ามา
                    if "message" in messaging and "text" in messaging["message"]:
                        sender_id = messaging["sender"]["id"]
                        message_text = messaging["message"]["text"]

                        # ประมวลผลข้อความใน background
                        background_tasks.add_task(process_message, sender_id, message_text)

        return {"status": "ok"}

    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail="Bad request")

@app.post("/test-message")
async def test_message(message: Dict[str, str]):
    """Endpoint สำหรับทดสอบการวิเคราะห์ intent โดยไม่ต้องใช้ Facebook"""
    if not intent_detector:
        raise HTTPException(status_code=500, detail="Intent detector not initialized")

    user_message = message.get("text", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message text is required")

    try:
        # ใช้ test_user_id สำหรับการทดสอบ
        test_user_id = message.get("user_id", "test_user")
        result = intent_detector.process_message(user_message, user_id=test_user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/admin/reset-manual-mode")
async def reset_manual_mode(request: Dict[str, str]):
    """Endpoint สำหรับแอดมินรีเซ็ต manual mode ของลูกค้า"""
    if not intent_detector:
        raise HTTPException(status_code=500, detail="Intent detector not initialized")

    user_id = request.get("user_id", "")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    try:
        success = intent_detector.reset_manual_mode(user_id)
        if success:
            return {"status": "success", "message": f"Manual mode reset for user {user_id}"}
        else:
            return {"status": "error", "message": f"User {user_id} not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting manual mode: {str(e)}")

@app.get("/admin/manual-mode-status/{user_id}")
async def get_manual_mode_status(user_id: str):
    """Endpoint สำหรับตรวจสอบสถานะ manual mode ของลูกค้า"""
    if not intent_detector:
        raise HTTPException(status_code=500, detail="Intent detector not initialized")

    try:
        manual_mode = intent_detector.get_manual_mode_status(user_id)
        return {
            "user_id": user_id,
            "manual_mode": manual_mode,
            "status": "manual" if manual_mode else "auto"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking manual mode status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)