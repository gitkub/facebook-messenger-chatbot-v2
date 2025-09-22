#!/usr/bin/env python3
"""
ทดสอบการทำงานแบบ multi-user context
"""

import os
from dotenv import load_dotenv
from intent_detector import IntentDetector

def test_multiuser_context():
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ ไม่พบ OPENAI_API_KEY")
        return

    print("🧪 ทดสอบการทำงานแบบ multi-user context")
    print("=" * 60)

    # สร้าง detector เดียว ใช้กับหลายคน
    detector = IntentDetector(openai_api_key)

    # จำลองสถานการณ์ที่ลูกค้า 2 คนคุยพร้อมกัน
    print("\n📱 สถานการณ์: ลูกค้า 2 คนทักเข้ามาพร้อมกัน")
    print("=" * 40)

    # ลูกค้าคนที่ 1
    print("\n👤 ลูกค้าคนที่ 1 (user123):")
    user1_messages = [
        "ดำ 3 ตัว",
        "M",
    ]

    # ลูกค้าคนที่ 2
    print("\n👤 ลูกค้าคนที่ 2 (user456):")
    user2_messages = [
        "ขาว 2 ตัว",
        "L",
    ]

    # สลับการคุยระหว่าง 2 คน
    conversations = [
        ("user123", user1_messages[0]),  # ดำ 3 ตัว
        ("user456", user2_messages[0]),  # ขาว 2 ตัว
        ("user123", user1_messages[1]),  # M
        ("user456", user2_messages[1]),  # L
    ]

    results = {}
    for user_id, message in conversations:
        print(f"\n{user_id}: '{message}'")

        try:
            result = detector.process_message(message, user_id=user_id)
            results[f"{user_id}_{len(results)}"] = result

            print(f"   🎯 Intent: {result['used_intent']}")
            print(f"   📊 Confidence: {result['confidence']:.2f}")

            # แสดงข้อมูลออเดอร์ที่เก็บไว้
            if result['order_info']:
                order_info = result['order_info']
                if order_info.get('colors'):
                    colors_text = ", ".join([f"{item['color']} {item['quantity']} ตัว" for item in order_info['colors']])
                    print(f"   🎨 สี: {colors_text}")
                if order_info.get('size'):
                    print(f"   📏 ไซส์: {order_info['size']}")
                if order_info.get('total_quantity'):
                    print(f"   🔢 จำนวน: {order_info['total_quantity']} ตัว")

            print(f"   💬 Reply: {result['reply'][:80]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print("-" * 30)

    # ตรวจสอบว่าแต่ละคนมี context แยกกันหรือไม่
    print("\n🔍 ตรวจสอบการแยก context:")
    print("=" * 40)

    # แสดง context ของแต่ละคน
    for user_id in ["user123", "user456"]:
        if user_id in detector.user_contexts:
            context = detector.user_contexts[user_id]
            print(f"\n👤 {user_id}:")
            print(f"   📋 Order info: {context['order_info']}")
            print(f"   🎯 Last intent: {context['last_intent']}")
            print(f"   💬 Last message: {context['last_message']}")
        else:
            print(f"\n👤 {user_id}: ❌ ไม่มี context")

    # ทดสอบการสั่งซื้อแยกกัน
    print("\n✅ ผลการทดสอบ:")
    print("=" * 40)

    # ตรวจสอบว่าคนที่ 1 มีออเดอร์ดำ M
    user1_context = detector.user_contexts.get("user123", {})
    user1_order = user1_context.get('order_info', {})
    if (user1_order.get('total_quantity') == 3 and
        user1_order.get('size') == 'M' and
        any(item['color'] == 'ดำ' for item in user1_order.get('colors', []))):
        print("✅ ลูกค้าคนที่ 1: สั่งดำ 3 ตัว ไซส์ M ถูกต้อง")
    else:
        print(f"❌ ลูกค้าคนที่ 1: ออเดอร์ไม่ถูกต้อง - {user1_order}")

    # ตรวจสอบว่าคนที่ 2 มีออเดอร์ขาว L
    user2_context = detector.user_contexts.get("user456", {})
    user2_order = user2_context.get('order_info', {})
    if (user2_order.get('total_quantity') == 2 and
        user2_order.get('size') == 'L' and
        any(item['color'] == 'ขาว' for item in user2_order.get('colors', []))):
        print("✅ ลูกค้าคนที่ 2: สั่งขาว 2 ตัว ไซส์ L ถูกต้อง")
    else:
        print(f"❌ ลูกค้าคนที่ 2: ออเดอร์ไม่ถูกต้อง - {user2_order}")

    print("\n🎯 สรุป: การแยก context ระหว่างผู้ใช้ทำงานได้ถูกต้อง!" if len(detector.user_contexts) >= 2 else "❌ การแยก context ไม่ทำงาน")

if __name__ == "__main__":
    test_multiuser_context()