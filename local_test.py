#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Interactive Testing for Facebook Messenger Chatbot
ทดสอบแชทบอทแบบ interactive บนเครื่อง
"""

import os
from intent_detector import IntentDetector

def main():
    """ฟังก์ชันหลัก - เริ่มทดสอบแบบ interactive"""

    # Load API key from environment or .env file
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key or api_key == 'test-key':
        print("⚠️  Warning: No valid OpenAI API key found.")
        print("   Please set OPENAI_API_KEY environment variable or update .env file")
        print("   Smart fallback responses will show error messages.")
        api_key = 'test-key'
        print()

    # Initialize chatbot
    print("🤖 Loading chatbot...")
    detector = IntentDetector(api_key)
    print("✅ Chatbot ready!")
    print()

    # Welcome message
    print("=" * 60)
    print("🧪 Facebook Messenger Chatbot - Local Testing")
    print("=" * 60)
    print("คำสั่ง:")
    print("  - พิมพ์ข้อความปกติเพื่อทดสอบ")
    print("  - พิมพ์ 'reset' เพื่อล้างประวัติการสนทนา")
    print("  - พิมพ์ 'quit' หรือ 'exit' เพื่อออก")
    print("=" * 60)
    print()

    user_id = "local_test_user"

    try:
        while True:
            # Get user input
            try:
                user_input = input("👤 คุณ: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 ออกจากโปรแกรม")
                break

            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'ออก', 'q']:
                print("👋 ออกจากโปรแกรม")
                break

            if user_input.lower() in ['reset', 'ล้าง', 'เริ่มใหม่']:
                # Reset user context
                if hasattr(detector, 'user_contexts') and user_id in detector.user_contexts:
                    del detector.user_contexts[user_id]
                print("🔄 ล้างประวัติการสนทนาแล้ว")
                print()
                continue

            if not user_input:
                continue

            # Process message
            try:
                result = detector.process_message(user_input, user_id)

                # Show response
                reply = result.get('reply')
                if reply:
                    print(f"🤖 บอท: {reply}")
                else:
                    print("🤖 บอท: [ไม่มีการตอบกลับ - อาจอยู่ใน manual mode]")

                # Show debug info
                detected_intent = result.get('detected_intent', 'unknown')
                used_intent = result.get('used_intent', 'unknown')
                confidence = result.get('confidence', 0.0)

                print(f"🔍 Debug: detected='{detected_intent}' → used='{used_intent}' (conf: {confidence:.2f})")

                # Show order info if available
                order_info = result.get('order_info', {})
                if order_info and any(order_info.values()):
                    print(f"📋 Order: {order_info}")

                print()

            except Exception as e:
                print(f"❌ Error: {e}")
                print()

    except KeyboardInterrupt:
        print("\n\n👋 ออกจากโปรแกรม")

if __name__ == "__main__":
    main()