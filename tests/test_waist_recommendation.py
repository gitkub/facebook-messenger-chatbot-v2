#!/usr/bin/env python3
"""
ทดสอบการแนะนำไซส์ตามรอบเอว
"""

import os
from dotenv import load_dotenv
from intent_detector import IntentDetector

def test_waist_recommendation():
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ ไม่พบ OPENAI_API_KEY")
        return

    print("🧪 ทดสอบการแนะนำไซส์ตามรอบเอว")
    print("=" * 60)

    test_cases = [
        ("เอว 28 ไซส์ไหนดีคะ", "M"),
        ("เอว 33 ไซส์ไหนดีคะ", "M หรือ L"),
        ("เอว 35 ใส่ไซส์อะไร", "M หรือ L"),
        ("เอว 38 ควรเลือกไซส์ไหน", "L หรือ XL"),
        ("เอว 42 แนะนำไซส์หน่อย", "XL"),
        ("เอว 45 ไซส์ไหนดี", "XXL"),
        ("เอว 55 ใส่ได้ไหม", "ใหญ่กว่าไซส์ที่มี"),
        ("รอบเอว 30 ใส่ไซส์ไหน", "M"),
    ]

    for i, (message, expected_suggestion) in enumerate(test_cases, 1):
        print(f"\n{i}. ลูกค้า: '{message}'")

        detector = IntentDetector(openai_api_key)

        try:
            result = detector.process_message(message)
            print(f"   🎯 Intent: {result['used_intent']}")
            print(f"   📊 Confidence: {result['confidence']:.2f}")

            if result['used_intent'] == 'size_recommendation':
                print(f"   💬 Reply:")
                print(f"   {result['reply']}")

                # ตรวจสอบว่าคำแนะนำถูกต้อง
                if expected_suggestion in result['reply']:
                    print(f"   ✅ แนะนำไซส์ถูกต้อง: {expected_suggestion}")
                else:
                    print(f"   ❌ แนะนำไซส์ไม่ถูกต้อง: ควรเป็น {expected_suggestion}")
            else:
                print(f"   ❌ ควรเป็น size_recommendation แต่ได้ {result['used_intent']}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print("-" * 60)

if __name__ == "__main__":
    test_waist_recommendation()