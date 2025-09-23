import json
import openai
from typing import Dict, Any
from pydantic import BaseModel

class IntentResult(BaseModel):
    intent: str
    confidence: float
    reason: str

class IntentDetector:
    def __init__(self, openai_api_key: str, replies_file: str = "replies.json", context_file: str = "business_context.json"):
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.replies = self._load_replies(replies_file)
        self.business_context = self._load_business_context(context_file)
        self.product_images = self._load_product_images("product_images.json")
        self.user_contexts = {}  # เก็บ context แยกตาม user_id

    def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """ดึงหรือสร้าง context สำหรับ user"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                'last_intent': None,
                'last_message': None,
                'order_info': {},
                'manual_mode': False
            }
        return self.user_contexts[user_id]

    def _load_replies(self, file_path: str) -> Dict[str, Any]:
        """โหลดข้อมูล intents และ replies จากไฟล์ JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {file_path} not found. Using empty replies.")
            return {}

    def _load_business_context(self, file_path: str) -> Dict[str, Any]:
        """โหลดข้อมูลธุรกิจจากไฟล์ JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Info: {file_path} not found. Running without business context.")
            return {}

    def _load_product_images(self, file_path: str) -> Dict[str, Any]:
        """โหลดข้อมูลรูปภาพสินค้าจากไฟล์ JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Info: {file_path} not found. Running without product images.")
            return {}

    def detect_intent(self, message: str, user_context: Dict[str, Any]) -> IntentResult:
        """วิเคราะห์ intent จากข้อความของผู้ใช้"""

        # สร้าง prompt สำหรับ GPT
        available_intents = list(self.replies.keys())
        available_intents.remove('fallback')  # ไม่ต้องให้ GPT เลือก fallback

        # เพิ่มข้อมูลธุรกิจเข้าไปใน context
        business_info = ""
        if self.business_context and "business_info" in self.business_context:
            business_info = f"""
ข้อมูลธุรกิจ:
{json.dumps(self.business_context['business_info'], ensure_ascii=False, indent=2)}

สีที่มีจำหน่าย: ดำ, ขาว, ครีม, ชมพู, ฟ้า, เทา, โกโก้, กรม
ไซส์ที่มี: M, L, XL, XXL
"""

        # เพิ่ม context จากการสนทนาก่อนหน้า
        conversation_context = ""
        if user_context.get('last_intent') in ["color_with_quantity", "color_multiple"]:
            conversation_context = f"""
🚨 บริบทสำคัญ: ลูกค้าเพิ่งแจ้งสี+จำนวนในข้อความก่อนหน้านี้แล้ว (intent: {user_context.get('last_intent')})
ดังนั้นถ้าข้อความปัจจุบันเป็นไซส์เดียว (M, L, XL, XXL) ต้องเลือก size_after_color_quantity
ห้ามเลือก size_only เด็ดขาด เพราะลูกค้าแจ้งจำนวนไปแล้ว
"""

        prompt = f"""
คุณเป็น AI ที่ช่วยวิเคราะห์ความตั้งใจ (intent) ของข้อความลูกค้าในร้านกางเกงคนท้อง
{business_info}{conversation_context}
ข้อความจากลูกค้า: "{message}"

Intent ที่มีอยู่:
{json.dumps({k: v['description'] for k, v in self.replies.items() if k != 'fallback'}, ensure_ascii=False, indent=2)}

หลักเกณฑ์พิเศษสำหรับการสั่งซื้อ:
- order_confirm: ใช้เมื่อลูกค้าแจ้งครบ สี + ไซส์ + จำนวน (เช่น "เอาสีดำ L 2 ตัว", "ดำ M 3 ตัว")
- color_with_quantity: ใช้เมื่อลูกค้าแจ้งสีพร้อมจำนวน แต่ไม่มีไซส์ (เช่น "ดำ 3 ตัว", "ดำ2 ครีม1", "ขาว 2", "ดำ 3 ตัวค่ะ")
- color_multiple: ใช้เมื่อลูกค้าแจ้งหลายสี แต่ไม่ระบุจำนวน เช่น "ดำ ขาว ครีม", "ชมพู เทา" (หลายสี = หลายตัว)
- size_multiple: ใช้เมื่อลูกค้าแจ้งไซส์หลายตัว เช่น "M L XL", "M M L", "L L L", "XL XXL"
- size_after_color_quantity: ใช้เมื่อลูกค้าแจ้งไซส์เดียวในบริบทที่เพิ่งแจ้งสี+จำนวนไปแล้ว (เช่น "M" หลังจาก "ดำ 3 ตัว")
- color: ใช้เมื่อลูกค้าแจ้งเพียงสีเดียวไม่มีจำนวน (เช่น "ดำ", "เอาสีดำ")
- size_only: ใช้เมื่อลูกค้าแจ้งเพียงไซส์เดียวในบริบทเริ่มต้น (เช่น "M", "L", "XL", "XXL")
- quantity_only: ใช้เมื่อลูกค้าแจ้งเพียงจำนวน (เช่น "1 ตัว", "2 ตัว", "3 ตัว")
- payment_transfer: ใช้เมื่อลูกค้าเลือกโอนเงิน (เช่น "โอน", "ธนาคาร", "PromptPay")
- payment_cod: ใช้เมื่อลูกค้าเลือกเก็บเงินปลายทาง (เช่น "ปลายทาง", "เก็บปลายทาง", "COD")
- address_received: ใช้เมื่อลูกค้าส่งข้อมูลที่อยู่ครบถ้วน (ชื่อ ที่อยู่ เบอร์โทร)
- address_incomplete: ใช้เมื่อลูกค้าส่งข้อมูลที่อยู่ไม่ครบถ้วน

สำคัญ:
- ⚠️ ถ้าข้อความมีสี + ตัวเลข ให้เลือก color_with_quantity เสมอ (ดำ 3, ขาว2, ดำ2ครีม1, ดำ 3 ตัวค่ะ)
- ⚠️ ถ้าข้อความมีหลายสีไม่มีตัวเลข ให้เลือก color_multiple เสมอ (ดำ ขาว ครีม = 3 ตัว, ชมพู เทา = 2 ตัว)
- ⚠️ ห้ามเลือก order_confirm เมื่อข้อความไม่มีไซส์ (M, L, XL, XXL) แม้จะมีคำว่า "ค่ะ" หรือ "ครับ"
- ถ้าข้อความมีไซส์หลายตัว (M L XL, M M L) ให้เลือก size_multiple เสมอ
- ⚠️ ถ้ามีบริบทว่าลูกค้าเพิ่งแจ้งสี+จำนวน และข้อความปัจจุบันเป็นไซส์เดียว ให้เลือก size_after_color_quantity
- ⚠️ ห้ามเลือก size_only เมื่อมีบริบทการแจ้งสี+จำนวนก่อนหน้า
- 💳 คำที่เกี่ยวกับการชำระเงิน: "ปลายทาง", "โอน", "ธนาคาร", "COD", "เก็บปลายทาง" ให้เลือก payment_cod หรือ payment_transfer
- color_with_quantity และ color_multiple มีลำดับความสำคัญสูงกว่า order_confirm เมื่อยังไม่มีไซส์

กรุณาวิเคราะห์และตอบกลับในรูปแบบ JSON เท่านั้น:
{{
  "intent": "ชื่อ intent ที่ตรงที่สุด หรือ 'none' ถ้าไม่ตรงอะไรเลย",
  "confidence": ระดับความมั่นใจ 0.0-1.0,
  "reason": "เหตุผลสั้นๆ ที่เลือก intent นี้"
}}

หลักเกณฑ์:
- confidence ≥ 0.55 ถึงจะถือว่าตรง
- ถ้าไม่แน่ใจให้ใส่ "none" และ confidence ต่ำ
- วิเคราะห์จากความหมายโดยรวม ไม่ใช่แค่คำเดียว
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "คุณเป็น AI ที่ช่วยวิเคราะห์ intent ของข้อความ ตอบเป็น JSON เท่านั้น"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )

            # Parse JSON response
            result_text = response.choices[0].message.content.strip()

            # ลบ markdown code block ถ้ามี
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]
            elif result_text.startswith('```'):
                result_text = result_text[3:-3]

            result_data = json.loads(result_text)

            return IntentResult(
                intent=result_data.get('intent', 'none'),
                confidence=float(result_data.get('confidence', 0.0)),
                reason=result_data.get('reason', 'No reason provided')
            )

        except Exception as e:
            print(f"Error in intent detection: {e}")
            return IntentResult(
                intent='none',
                confidence=0.0,
                reason=f'Error: {str(e)}'
            )

    def _extract_color_quantity(self, message: str) -> Dict[str, Any]:
        """แยกข้อมูลสีและจำนวนจากข้อความ"""
        import re

        colors = ["โกโก้", "โกโก", "ดำ", "ขาว", "ครีม", "ชมพู", "ฟ้า", "เทา", "กรม"]
        result = {'colors': [], 'total_quantity': 0}

        # ใช้ regex pattern เดียวที่ครอบคลุมทั้งมีและไม่มีช่องว่าง
        for color in colors:
            # หาตัวเลขที่ตามหลังสี รองรับ: "ดำ 2", "ดำ2"
            pattern = rf"{color}\s*(\d+)"
            matches = re.findall(pattern, message)

            for match in matches:
                quantity = int(match)
                result['colors'].append({'color': color, 'quantity': quantity})
                result['total_quantity'] += quantity

        # กรณีพิเศษ: "เอา 33" หรือ "รับ 2 ตัว" ที่ไม่มีสีระบุ
        if result['total_quantity'] == 0:
            numbers = re.findall(r'\d+', message)
            if numbers and not any(color in message for color in colors):
                # ถ้ามีตัวเลขแต่ไม่มีสี ให้เก็บเฉพาะจำนวน
                qty = int(numbers[0])  # ใช้ตัวเลขตัวแรก
                result['total_quantity'] = qty
                return result

        # ถ้าไม่เจอตัวเลขเลย แต่มีสี ให้นับสีที่มี (1 สี = 1 ตัว)
        if result['total_quantity'] == 0:
            found_colors = []
            message_remaining = message

            # ใช้ลำดับจากยาวไปสั้น และลบสีที่เจอออกจากข้อความ
            for color in colors:
                if color in message_remaining:
                    found_colors.append(color)
                    message_remaining = message_remaining.replace(color, '', 1)  # ลบเฉพาะครั้งแรก

            if found_colors:
                for color in found_colors:
                    result['colors'].append({'color': color, 'quantity': 1})
                result['total_quantity'] = len(found_colors)

        return result

    def _suggest_size_by_waist(self, waist_size: int) -> str:
        """แนะนำไซส์ตามรอบเอว"""
        if waist_size <= 36:
            if waist_size <= 32:
                return "🎯 แนะนำไซส์ M (เอว 28-36) เหมาะสำหรับคุณค่ะ"
            else:
                return "🎯 แนะนำไซส์ M หรือ L ก็ได้ค่ะ\n• M (เอว 28-36) - พอดี\n• L (เอว 32-40) - หลวมสบาย"
        elif waist_size <= 40:
            if waist_size <= 36:
                return "🎯 แนะนำไซส์ L (เอว 32-40) เหมาะสำหรับคุณค่ะ"
            else:
                return "🎯 แนะนำไซส์ L หรือ XL ก็ได้ค่ะ\n• L (เอว 32-40) - พอดี\n• XL (เอว 36-42) - หลวมสบาย"
        elif waist_size <= 42:
            return "🎯 แนะนำไซส์ XL (เอว 36-42) เหมาะสำหรับคุณค่ะ"
        elif waist_size <= 50:
            return "🎯 แนะนำไซส์ XXL (เอว 40-50) เหมาะสำหรับคุณค่ะ"
        else:
            return "🎯 รอบเอวของคุณใหญ่กว่าไซส์ที่มี (XXL เอว 40-50)\nแนะนำให้ปรึกษาแอดมินก่อนสั่งค่ะ"

    def _analyze_address(self, message: str) -> Dict[str, Any]:
        """วิเคราะห์ข้อมูลที่อยู่ว่าครบถ้วนหรือไม่"""
        import re

        result = {
            'has_name': False,
            'has_address': False,
            'has_phone': False,
            'extracted_name': '',
            'extracted_address': '',
            'extracted_phone': ''
        }

        # ตรวจสอบเบอร์โทร (10-11 หลัก)
        phone_patterns = [
            r'0\d{8,9}',  # 081234567, 0812345678
            r'\d{10,11}',  # 1234567890, 12345678901
        ]

        for pattern in phone_patterns:
            phone_match = re.search(pattern, message)
            if phone_match:
                result['has_phone'] = True
                result['extracted_phone'] = phone_match.group()
                break

        # ตรวจสอบที่อยู่ (มีตัวเลข + คำที่เกี่ยวกับที่อยู่)
        address_keywords = ['บ้าน', 'ถนน', 'ซอย', 'ตำบล', 'อำเภอ', 'จังหวัด', 'หมู่', 'ม.', 'ต.', 'อ.', 'จ.']
        has_number = bool(re.search(r'\d+', message))
        has_address_keyword = any(keyword in message for keyword in address_keywords)

        if has_number and has_address_keyword:
            result['has_address'] = True
            # แยกที่อยู่ออกมา (ลบเบอร์โทรออก)
            address_text = re.sub(r'0\d{8,9}', '', message).strip()
            result['extracted_address'] = address_text

        # ตรวจสอบชื่อ (คำ 2-3 คำแรกที่ไม่ใช่ address keywords)
        words = message.split()
        name_words = []
        for word in words[:3]:  # ดูเฉพาะ 3 คำแรก
            if not any(keyword in word for keyword in address_keywords) and not re.search(r'\d{3,}', word):
                name_words.append(word)

        if len(name_words) >= 1:  # มีอย่างน้อย 1 คำที่เป็นชื่อ
            result['has_name'] = True
            result['extracted_name'] = ' '.join(name_words)

        return result

    def _calculate_price(self, quantity: int) -> Dict[str, Any]:
        """คำนวณราคาตามจำนวน"""
        if quantity >= 3:
            price = 490
            shipping = 0
            total = 490
            note = f"ตัวละ {490//quantity} บาท + ส่งฟรี"
        elif quantity == 2:
            price = 340
            shipping = 30
            total = 370
            note = f"ตัวละ {340//quantity} บาท"
        else:
            price = 180
            shipping = 30
            total = 210
            note = "ตัวละ 180 บาท"

        return {
            'price': price,
            'shipping': shipping,
            'total': total,
            'note': note
        }

    def get_reply(self, intent: str, message: str = '', user_context: Dict[str, Any] = None) -> str:
        """ดึงข้อความตอบกลับตาม intent"""
        if intent in self.replies and intent != 'fallback':
            reply = self.replies[intent]['reply']

            # ถ้าเป็น size_after_color_quantity หรือ order_confirm ให้แทนที่ข้อมูลออเดอร์
            if intent in ['size_after_color_quantity', 'order_confirm'] and user_context and user_context.get('order_info'):
                order_info = user_context['order_info']
                colors_text = ", ".join([f"{item['color']} {item['quantity']} ตัว" for item in order_info.get('colors', [])])
                size = order_info.get('size', '')
                total_quantity = order_info.get('total_quantity', 0)
                price_info = self._calculate_price(total_quantity)

                reply = reply.replace('[สี]', colors_text)
                reply = reply.replace('[ไซส์]', size)
                reply = reply.replace('[จำนวน]', str(total_quantity))
                reply = reply.replace('[ยอด]', str(price_info['total']))

            # ถ้าเป็น address_received ให้แทนที่ข้อมูลที่อยู่
            elif intent == 'address_received' and user_context and user_context.get('order_info', {}).get('address_info'):
                addr_info = user_context['order_info']['address_info']
                reply = reply.replace('[ชื่อ]', addr_info.get('extracted_name', ''))
                reply = reply.replace('[ที่อยู่]', addr_info.get('extracted_address', ''))
                reply = reply.replace('[เบอร์]', addr_info.get('extracted_phone', ''))

            # ถ้าเป็น size_recommendation ให้แทนที่คำแนะนำไซส์
            elif intent == 'size_recommendation':
                import re
                waist_match = re.search(r'เอว\s*(\d+)', message)
                if waist_match:
                    waist_size = int(waist_match.group(1))
                    size_suggestion = self._suggest_size_by_waist(waist_size)
                    reply = reply.replace('[size_suggestion]', size_suggestion)
                else:
                    # ถ้าไม่มีข้อมูลรอบเอว ให้คำแนะนำทั่วไป
                    reply = reply.replace('[size_suggestion]', "💡 กรุณาแจ้งรอบเอวปัจจุบันของคุณ จะได้แนะนำไซส์ที่เหมาะสมค่ะ")

            return reply
        else:
            return self.replies.get('fallback', {}).get('reply', 'ขอบคุณที่ติดต่อค่ะ')

    def process_message(self, message: str, user_id: str = "default", confidence_threshold: float = 0.55) -> Dict[str, Any]:
        """ประมวลผลข้อความและคืนค่าผลลัพธ์พร้อมข้อความตอบกลับ"""
        # ดึง context ของ user นี้
        user_context = self._get_user_context(user_id)

        # ตรวจสอบ manual mode - ถ้าเป็น manual mode ให้หยุดตอบ
        if user_context.get('manual_mode', False):
            return {
                'detected_intent': 'manual_mode',
                'confidence': 1.0,
                'reason': 'User is in manual mode - admin handling required',
                'used_intent': 'manual_mode',
                'reply': None,  # ไม่ส่งข้อความตอบกลับ
                'original_message': message,
                'order_info': user_context['order_info'].copy(),
                'manual_mode': True
            }

        intent_result = self.detect_intent(message, user_context)

        # ตัดสินใจว่าจะใช้ intent ที่ตรวจจับได้หรือใช้ fallback
        if intent_result.confidence >= confidence_threshold and intent_result.intent != 'none':
            used_intent = intent_result.intent
        else:
            used_intent = 'fallback'
            # เมื่อเข้า fallback intent ให้เปิด manual mode
            user_context['manual_mode'] = True

        # แก้ไข intent ตาม business logic หากจำเป็น
        if user_context.get('last_intent') in ["color_with_quantity", "color_multiple"] and used_intent == "size_only":
            # ถ้าเพิ่งแจ้งสี+จำนวน และตอนนี้แจ้งไซส์ ให้เปลี่ยนเป็น size_after_color_quantity
            sizes = ["M", "L", "XL", "XXL"]
            if any(size in message.upper() for size in sizes):
                used_intent = "size_after_color_quantity"

        # แก้ไข intent สำหรับข้อความที่มีสี+จำนวน+ไซส์ครบ
        if used_intent in ["color_with_quantity", "order_confirm"]:
            # ตรวจสอบว่ามีไซส์ในข้อความหรือไม่
            sizes = ["M", "L", "XL", "XXL"]
            has_size = any(size in message.upper() for size in sizes)

            # ตรวจสอบว่ามีสีและจำนวนหรือไม่
            color_info = self._extract_color_quantity(message)
            has_color_quantity = color_info.get('total_quantity', 0) > 0

            if has_color_quantity and has_size:
                # มีครบทั้งสี จำนวน และไซส์ ให้เป็น order_confirm
                used_intent = "order_confirm"
                # เก็บข้อมูลทั้งสีและไซส์
                user_context['order_info'].update(color_info)
                # ค้นหาไซส์ (เรียงจากยาวไปสั้นเพื่อไม่ให้ XXL ถูกจับเป็น XL)
                sizes_ordered = ["XXL", "XL", "M", "L"]
                for size in sizes_ordered:
                    if size in message.upper():
                        user_context['order_info']['size'] = size
                        break
            elif has_color_quantity and not has_size:
                # มีเฉพาะสี+จำนวน ไม่มีไซส์ ให้เป็น color_with_quantity
                used_intent = "color_with_quantity"

        # ตรวจสอบคำถามเกี่ยวกับความสูง รอบเอว หรือคำแนะนำไซส์
        size_recommendation_patterns = [
            "สูง", "ความสูง", "ตัวสูง", "165", "160", "170", "175", "180",
            "ซม", "cm", "เซนติเมตร", "ไซส์ไหนดี", "ใส่ไซส์ไหน", "แนะนำไซส์",
            "เอว", "รอบเอว"
        ]
        has_size_rec_keyword = any(keyword in message for keyword in size_recommendation_patterns)

        if has_size_rec_keyword:
            # ถ้าพูดถึงความสูง รอบเอว หรือขอคำแนะนำไซส์ ให้เป็น size_recommendation
            used_intent = "size_recommendation"

            # สำหรับเอว ไม่ต้องเก็บเป็นจำนวนสินค้า เพราะเป็นรอบเอว
            # แต่ถ้าเป็นการสั่งซื้อจริงๆ ต้องดูบริบท
            import re
            waist_match = re.search(r'เอว\s*(\d+)', message)
            if waist_match:
                # เป็นการบอกรอบเอว ไม่ใช่จำนวนสินค้า
                pass
            else:
                # ตรวจสอบว่ามีจำนวนในข้อความหรือไม่ (สำหรับกรณีอื่น)
                color_info = self._extract_color_quantity(message)
                if color_info.get('total_quantity', 0) > 0:
                    # ถ้ามีจำนวนในข้อความ ให้เก็บไว้
                    user_context['order_info'].update(color_info)

        # ตรวจสอบ price inquiry patterns แม้ GPT จะมั่นใจ
        price_patterns = [
            "รับ", "เอา", "ซื้อ", "180", "210", "490", "ค่าส่ง", "บาท",
            "ตัว", "โปร", "ส่วนลด"
        ]
        # ตรวจสอบว่ามีคำที่เกี่ยวกับราคาหรือการซื้อขาย และมีตัวเลข และไม่มีสีหรือไซส์
        has_price_keyword = any(keyword in message for keyword in price_patterns)
        has_number = any(char.isdigit() for char in message)

        # ตรวจสอบว่าไม่มีสีหรือไซส์ในข้อความ (เพื่อไม่ให้ชนกับ order_confirm)
        colors = ["โกโก้", "โกโก", "ดำ", "ขาว", "ครีม", "ชมพู", "ฟ้า", "เทา", "กรม"]
        sizes = ["M", "L", "XL", "XXL"]
        has_color = any(color in message for color in colors)
        has_size = any(size in message.upper() for size in sizes)

        if has_price_keyword and has_number and not has_color and not has_size and not has_size_rec_keyword:
            used_intent = "price_inquiry"

            # ถ้ามีจำนวนในข้อความ ให้เก็บไว้
            color_info = self._extract_color_quantity(message)
            if color_info.get('total_quantity', 0) > 0:
                user_context['order_info'].update(color_info)

        # ตรวจสอบ COD inquiry patterns (ลำดับความสำคัญสูง)
        cod_inquiry_patterns = [
            "บวกเพิ่ม", "ค่าธรรมเนียม", "ค่าบวก", "เพิ่มค่า", "บวกค่า",
            "เพิ่ม", "บวก", "ค่าส่งเพิ่ม"
        ]
        cod_words = ["ปลายทาง", "COD", "เก็บปลายทาง"]

        has_cod_inquiry = any(pattern in message for pattern in cod_inquiry_patterns)
        has_cod_word = any(word in message for word in cod_words)

        # ตรวจสอบ greeting patterns ก่อน
        greeting_patterns = [
            "สวัสดี", "หวัดดี", "hello", "hi", "ดี", "สนใจ",
            "เฮ้ย", "ฮาย", "ฮัลโหล", "สบายดี"
        ]
        has_greeting = any(pattern in message.lower() for pattern in greeting_patterns)

        if has_greeting and len(message) < 20:  # คำทักทายสั้นๆ
            used_intent = "greeting"

        # ตรวจสอบ image request intents
        image_patterns = {
            "show_product_image": [
                "ขอดูสี", "ดูสี", "ดูรูป", "ขอดูรูป", "รูปสี", "รูปกางเกง"
            ],
            "show_size_chart": [
                "ตารางไซส์", "ตารางขนาด", "ดูไซส์", "ขอดูไซส์"
            ],
            "show_catalog": [
                "แคตตาล็อก", "แคตาล็อค", "แคตตะล็อก", "ดูสินค้าทั้งหมด", "สินค้าทั้งหมด"
            ]
        }

        # ตรวจสอบ image patterns
        image_intent_found = False
        for intent_name, patterns in image_patterns.items():
            if any(pattern in message for pattern in patterns):
                used_intent = intent_name
                image_intent_found = True
                break

        # ตรวจสอบ product info inquiry patterns ถ้ายังไม่พบ image intent
        if not image_intent_found:
            product_info_patterns = [
                "มีสีไหนบ้าง", "สีไหนบ้าง", "มีสีอะไรบ้าง", "สีอะไรบ้าง",
                "มีไซส์ไหนบ้าง", "ไซส์ไหนบ้าง", "มีไซส์อะไรบ้าง", "ไซส์อะไรบ้าง",
                "มีอะไรบ้าง", "สีและไซส์", "รายการสี", "รายการไซส์"
            ]
            has_product_info_inquiry = any(pattern in message for pattern in product_info_patterns)

            if has_product_info_inquiry:
                used_intent = "product_info"

        # ตรวจสอบ payment response patterns ก่อน (ลำดับความสำคัญสูง)
        payment_cod_response_patterns = [
            "ปลายทางค่ะ", "ปลายทางจ้า", "ปลายทางครับ", "ปลายทางคะ",
            "เก็บปลายทางค่ะ", "เก็บปลายทางจ้า", "เก็บปลายทางครับ",
            "CODค่ะ", "CODจ้า", "codค่ะ", "codจ้า"
        ]
        payment_transfer_response_patterns = [
            "โอนค่ะ", "โอนจ้า", "โอนครับ", "โอนคะ",
            "ธนาคารค่ะ", "ธนาคารจ้า", "ธนาคารครับ"
        ]

        if any(pattern in message for pattern in payment_cod_response_patterns):
            used_intent = "payment_cod"
        elif any(pattern in message for pattern in payment_transfer_response_patterns):
            used_intent = "payment_transfer"

        # ให้ COD inquiry มีลำดับความสำคัญสูงกว่า payment intents อื่น
        elif has_cod_inquiry and has_cod_word:
            used_intent = "cod_inquiry"

        # ตรวจสอบ payment intents หาก GPT ไม่จับได้ และยังไม่เป็น cod_inquiry
        elif used_intent == "fallback" or intent_result.confidence < 0.5:
            payment_cod_keywords = ["ปลายทาง", "เก็บปลายทาง", "COD", "cod"]
            payment_transfer_keywords = ["โอน", "ธนาคาร", "PromptPay", "promptpay", "บัญชี"]

            message_lower = message.lower()
            if any(keyword in message for keyword in payment_cod_keywords):
                used_intent = "payment_cod"
            elif any(keyword in message_lower for keyword in payment_transfer_keywords):
                used_intent = "payment_transfer"

        # ตรวจสอบ address intents หลังจากเลือก payment_cod
        if user_context.get('last_intent') == "payment_cod":
            address_info = self._analyze_address(message)
            if address_info['has_phone'] or address_info['has_address'] or address_info['has_name']:
                # มีข้อมูลที่อยู่บางส่วน ตรวจสอบว่าครบหรือไม่
                if address_info['has_name'] and address_info['has_address'] and address_info['has_phone']:
                    used_intent = "address_received"
                    user_context['order_info']['address_info'] = address_info
                else:
                    used_intent = "address_incomplete"

        # เก็บข้อมูลออเดอร์
        if used_intent == 'color_with_quantity':
            # แยกข้อมูลสีและจำนวน
            color_info = self._extract_color_quantity(message)
            user_context['order_info'].update(color_info)
        elif used_intent == 'color_multiple':
            # แยกข้อมูลหลายสี (1 สี = 1 ตัว)
            color_info = self._extract_color_quantity(message)
            user_context['order_info'].update(color_info)
        elif used_intent == 'size_after_color_quantity':
            # เก็บไซส์ (ค้นหาไซส์ที่ยาวที่สุดก่อน เพื่อไม่ให้ XXL ถูกจับเป็น XL)
            sizes = ["XXL", "XL", "M", "L"]  # เรียงจากยาวไปสั้น
            for size in sizes:
                if size in message.upper():
                    user_context['order_info']['size'] = size
                    break
        elif used_intent == 'size_only':
            # ตรวจสอบว่ามีจำนวนจากข้อความก่อนหน้าหรือไม่
            if user_context['order_info'].get('total_quantity', 0) > 0:
                # ถ้ามีจำนวนอยู่แล้ว ให้เก็บไซส์และเปลี่ยนเป็น order_confirm
                sizes = ["XXL", "XL", "M", "L"]
                for size in sizes:
                    if size in message.upper():
                        user_context['order_info']['size'] = size
                        used_intent = "order_confirm"
                        break
            else:
                # ถ้าไม่มีจำนวน ให้เก็บไซส์ไว้
                sizes = ["XXL", "XL", "M", "L"]
                for size in sizes:
                    if size in message.upper():
                        user_context['order_info']['size'] = size
                        break
        elif used_intent == 'address_received' and 'address_info' not in user_context['order_info']:
            # เก็บข้อมูลที่อยู่หากยังไม่ได้เก็บ
            address_info = self._analyze_address(message)
            user_context['order_info']['address_info'] = address_info

        # ดึงข้อความตอบกลับ
        reply = self.get_reply(used_intent, message, user_context)

        # ตรวจสอบว่าต้องส่งรูปภาพหรือไม่
        image_url = None
        if used_intent in self.replies and self.replies[used_intent].get('image_required', False):
            image_url = self._get_image_url(used_intent, message)

        # เก็บ intent และข้อความล่าสุดเพื่อใช้ในการวิเคราะห์ครั้งต่อไป
        user_context['last_intent'] = used_intent
        user_context['last_message'] = message

        result = {
            'detected_intent': intent_result.intent,
            'confidence': intent_result.confidence,
            'reason': intent_result.reason,
            'used_intent': used_intent,
            'reply': reply,
            'original_message': message,
            'order_info': user_context['order_info'].copy()
        }

        # เพิ่ม image_url ถ้ามี
        if image_url:
            result['image_url'] = image_url

        return result

    def _get_image_url(self, intent: str, message: str) -> str:
        """ดึง URL รูปภาพตาม intent และข้อความ"""
        if not self.product_images:
            return None

        # ตรวจสอบว่า intent มี image_type กำหนดไว้หรือไม่
        intent_config = self.replies.get(intent, {})
        image_type = intent_config.get("image_type")

        if image_type:
            # ใช้ image_type ที่กำหนดใน replies.json
            if image_type == "product_catalog":
                return self.product_images.get("product_catalog")
            elif image_type == "size_chart":
                return self.product_images.get("size_chart")

        # สำหรับ show_product_image - หาสีที่ขอดู
        if intent == "show_product_image":
            colors = ["โกโก้", "โกโก", "ดำ", "ขาว", "ครีม", "ชมพู", "ฟ้า", "เทา", "กรม"]
            for color in colors:
                if color in message:
                    return self.product_images.get("product_images", {}).get(color)
            # ถ้าไม่พบสี ให้ส่งรูปแรก
            return list(self.product_images.get("product_images", {}).values())[0] if self.product_images.get("product_images") else None

        # สำหรับ show_size_chart
        elif intent == "show_size_chart":
            return self.product_images.get("size_chart")

        # สำหรับ show_catalog
        elif intent == "show_catalog":
            return self.product_images.get("product_catalog")

        return None

    def reset_manual_mode(self, user_id: str) -> bool:
        """รีเซ็ต manual mode สำหรับ user คืนค่า True ถ้าสำเร็จ"""
        if user_id in self.user_contexts:
            self.user_contexts[user_id]['manual_mode'] = False
            return True
        return False

    def get_manual_mode_status(self, user_id: str) -> bool:
        """ตรวจสอบสถานะ manual mode ของ user"""
        user_context = self._get_user_context(user_id)
        return user_context.get('manual_mode', False)


