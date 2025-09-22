#!/usr/bin/env python3
"""
ทดสอบการจำจำนวนข้ามข้อความ
"""

import os
from dotenv import load_dotenv
from intent_detector import IntentDetector

def test_quantity_memory():
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ ไม่พบ OPENAI_API_KEY")
        return

    print("🧪 ทดสอบการจำจำนวนข้ามข้อความ")
    print("=" * 60)

    test_cases = [
        {
            'name': 'แจ้งจำนวน -> ถามไซส์ -> ตอบไซส์',
            'conversation': [
                "ดำ โกโก้ะ",  # เป็นสีหลายตัว
                "ไดรับรายการแล้วคะ",
                "กรุณาแจ้งไซส์ที่ต้องการด้วยคะ",
                "เอา 33 ไซส์ไหนดีคะ",  # แจ้งจำนวน 33 และถามไซส์
                "L คะ"  # ตอบไซส์
            ]
        },
        {
            'name': 'แจ้งจำนวนพร้อมสี -> ถามความสูง -> ตอบไซส์',
            'conversation': [
                "เอา 2 ตัว",  # แจ้งจำนวนก่อน
                "สูง 165 ใส่ไซส์ไหนดีคะ",  # ถามเรื่องความสูง
                "M"  # ตอบไซส์
            ]
        },
        {
            'name': 'แจ้งสี+จำนวน -> ถามแนะนำไซส์ -> ตอบไซส์',
            'conversation': [
                "ดำ 3 ตัว",  # แจ้งสี+จำนวน
                "แนะนำไซส์หน่อย",  # ขอคำแนะนำ
                "L"  # ตอบไซส์
            ]
        }
    ]

    for case in test_cases:
        print(f"\n📋 {case['name']}:")
        print("=" * 40)

        detector = IntentDetector(openai_api_key)

        for i, message in enumerate(case['conversation'], 1):
            print(f"\n{i}. ลูกค้า: '{message}'")

            try:
                result = detector.process_message(message)
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

                print(f"\n   💬 Reply: {result['reply'][:100]}...")

                # ตรวจสอบว่าไม่ควรถามจำนวนซ้ำ
                if "จำนวนที่ต้องการ" in result['reply'] and result['order_info'].get('total_quantity', 0) > 0:
                    print(f"   ❌ ไม่ควรถามจำนวนซ้ำ! (มีจำนวน {result['order_info']['total_quantity']} ตัวแล้ว)")

                # ตรวจสอบว่าควรสรุปออเดอร์เมื่อมีข้อมูลครบ
                if i == len(case['conversation']) and result['order_info'].get('total_quantity', 0) > 0 and result['order_info'].get('size'):
                    if result['used_intent'] != 'order_confirm':
                        print(f"   ❌ ควรสรุปออเดอร์แล้ว! (มีทั้งจำนวนและไซส์)")
                    else:
                        print(f"   ✅ สรุปออเดอร์ถูกต้อง")

            except Exception as e:
                print(f"   ❌ Error: {e}")

            print("-" * 30)

        print("=" * 60)

if __name__ == "__main__":
    test_quantity_memory()