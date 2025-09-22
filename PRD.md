# 📄 PRD: Facebook Messenger Chatbot with GPT-based Intent Routing

## 1. บทนำ (Introduction)
ระบบแชตบอทสำหรับ **Facebook Page (Messenger)** ที่สามารถรับข้อความจากผู้ใช้ วิเคราะห์ความตั้งใจ (intent) ด้วย GPT และตอบกลับด้วย **ข้อความสำเร็จรูป** ที่ตั้งค่าไว้ในชุดข้อมูล (JSON/Dict) โดยไม่พึ่งพาฐานข้อมูลภายนอก

**เป้าหมาย:**  
- ลดภาระการตอบคำถามซ้ำ ๆ ของแอดมินเพจ  
- ตอบคำถามได้อย่างรวดเร็วและเป็นมาตรฐาน  
- ขยาย/แก้ไขข้อความตอบกลับได้ง่ายในอนาคต  

---

## 2. ขอบเขต (Scope)
- **In-scope:**
  - รองรับข้อความ **ข้อความตัวอักษร (text message)** บน Messenger
  - วิเคราะห์ข้อความด้วย GPT เพื่อหา intent
  - ตอบกลับด้วยข้อความที่กำหนดไว้ล่วงหน้า (predefined replies)
  - เก็บชุดข้อความในไฟล์ JSON/Dict (เช่น `intents_config.py` หรือ `replies.json`)
  - Deploy ได้บน Render / Railway / Fly.io / Google Cloud Run (HTTPS endpoint)

- **Out-of-scope (ไม่ทำในเวอร์ชันแรก):**
  - การส่งวิดีโอ, ปุ่ม (quick replies, carousel)
  - ระบบ admin/backoffice สำหรับแก้ไขข้อความผ่าน UI
  - การเก็บ log/statistics ลง database
  - การ integrate กับ payment หรือ order tracking API

---

## 3. User Story
- **ผู้ใช้ (Customer):**  
  - เป็นลูกค้าที่ทักข้อความมาที่ Facebook Page  
  - คาดหวังคำตอบทันทีเกี่ยวกับสินค้า ราคา การสั่งซื้อ และการจัดส่ง  

- **แอดมินเพจ (Page Admin):**  
  - อยากลดงานตอบคำถามเดิม ๆ  
  - ต้องการมั่นใจว่าลูกค้าได้รับคำตอบมาตรฐาน  
  - สามารถแก้ไขไฟล์ `replies.json` เพื่อเปลี่ยนข้อความได้เอง  

---

## 4. Functional Requirements
1. **รับข้อความจาก Facebook Page (Messenger Webhook)**  
   - ระบบต้องสามารถรับ Event `messages` จาก Facebook Messenger  

2. **Intent Detection (GPT-based)**  
   - ใช้ GPT วิเคราะห์ข้อความผู้ใช้  
   - คืนค่า `{ intent, confidence, reason }`  
   - ถ้า confidence ≥ 0.55 และ intent != none → ตอบด้วยข้อความที่กำหนด  
   - ถ้าไม่มั่นใจ → ตอบ fallback message  

3. **Predefined Replies (Static JSON/Dict)**  
   - เก็บในไฟล์ `replies.json` หรือ `intents_config.py`  
   - สามารถเพิ่ม intent ใหม่ได้ง่ายโดยการแก้ไฟล์  

4. **Reply to User**  
   - ตอบข้อความกลับไปยังผู้ใช้ผ่าน Facebook Send API (รองรับทั้งข้อความตัวอักษรและรูปภาพ)  

5. **Fallback Message**  
   - ถ้า GPT ไม่สามารถแมป intent ได้ → ส่งข้อความ fallback  
   - เช่น `"ขอบคุณที่ติดต่อค่ะ ทีมงานจะรีบตอบกลับโดยเร็วที่สุด"`  

---

## 5. Non-Functional Requirements
- **Latency:** ตอบกลับไม่เกิน 3–5 วินาที  
- **Scalability:** รองรับอย่างน้อย 1000 ข้อความ/วัน  
- **Security:**  
  - ตรวจสอบ `X-Hub-Signature-256` ด้วย `APP_SECRET`  
  - ซ่อน API Key (OpenAI, Facebook Page Token) ไว้ใน `.env`  
- **Maintainability:** ง่ายต่อการแก้ไข intent/reply โดยไม่ต้องแก้โค้ดหลัก  

---

## 6. System Design (High-level)
```
Messenger User → Facebook Page → Messenger Webhook → FastAPI Server
   |                                                      |
   |                        1. รับข้อความ                 |
   |                        2. วิเคราะห์ intent (GPT)     |
   |                        3. เลือกข้อความจาก JSON       |
   |                        4. ส่งกลับผ่าน Send API       |
```

---

## 7. Data Structure ตัวอย่าง (`replies.json`)
```json
{
  "greeting": {
    "description": "คำทักทายทั่วไป",
    "reply": "สวัสดีค่ะ ยินดีต้อนรับสู่เพจของเรา 🙏"
  },
  "price": {
    "description": "ถามเกี่ยวกับราคา โปรโมชัน",
    "reply": "สินค้าของเรามีหลายราคา เริ่มต้นที่ 299 บาทค่ะ"
  },
  "shipping": {
    "description": "ถามเรื่องการจัดส่ง",
    "reply": "เราจัดส่งทุกวันจันทร์-เสาร์ ผ่าน Kerry/Flash ค่ะ"
  },
  "order": {
    "description": "ถามเรื่องวิธีสั่งซื้อ",
    "reply": "คุณสามารถสั่งซื้อได้ทาง Inbox หรือกดที่ปุ่ม Shop Now ค่ะ"
  }
}
```

---

## 8. Environment Variables (`.env`)
```
PAGE_ACCESS_TOKEN=<FB_PAGE_TOKEN>
VERIFY_TOKEN=<FB_VERIFY_TOKEN>
APP_SECRET=<FB_APP_SECRET>
OPENAI_API_KEY=<OPENAI_API_KEY>
```

---

## 9. Success Metrics
- 🎯 บอทสามารถตอบถูก intent ≥ 80% ของข้อความที่ตรงกับ use case  
- 🎯 ลดเวลาที่แอดมินต้องมาตอบเองลง ≥ 50%  
- 🎯 ลูกค้าได้รับข้อความตอบกลับอัตโนมัติ ≤ 5 วินาที  

---

## 10. Future Enhancements
- เพิ่ม **Quick Reply / Buttons / Carousel**
- รองรับการส่งไฟล์ประเภทอื่น ๆ (เช่น วิดีโอ/ไฟล์เอกสาร)  
- ต่อ database สำหรับเก็บ log และทำ analytics  
- UI สำหรับแอดมินแก้ไข replies โดยไม่ต้องแก้ไฟล์  
- รองรับหลายภาษา (เช่น ไทย + อังกฤษ)  
