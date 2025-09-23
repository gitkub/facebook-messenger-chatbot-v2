#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Test Script for Facebook Messenger Chatbot
ทดสอบแชทบอทด้วยข้อมูลจาก CSV file
"""

import os
import csv
import json
from datetime import datetime
from intent_detector import IntentDetector

def load_test_scenarios(csv_file):
    """โหลดข้อมูลทดสอบจาก CSV"""
    scenarios = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                scenarios.append(row)
        return scenarios
    except FileNotFoundError:
        print(f"❌ Error: File {csv_file} not found")
        return []
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return []

def run_batch_test(scenarios, detector, output_file=None):
    """รันการทดสอบแบบ batch"""
    results = []
    total_tests = len(scenarios)
    passed = 0
    failed = 0

    print(f"🧪 เริ่มทดสอบ {total_tests} scenarios")
    print("=" * 80)

    for i, scenario in enumerate(scenarios, 1):
        try:
            # ทดสอบข้อความ
            message = scenario['user_message']
            expected_intent = scenario['expected_intent']
            expected_type = scenario['expected_type']
            description = scenario['description']
            category = scenario['scenario']

            # ประมวลผลข้อความ
            result = detector.process_message(message, f"test_user_{i}")

            # ตรวจสอบผลลัพธ์
            detected_intent = result['detected_intent']
            used_intent = result['used_intent']
            confidence = result['confidence']
            reply = result['reply']

            # ตัดสินผลลัพธ์
            if expected_type == 'template':
                # Template intent - ต้องตรงกับที่คาดหวัง
                test_passed = (used_intent == expected_intent)
            elif expected_type == 'ai':
                # Smart fallback - ต้องเป็น smart_fallback
                test_passed = (used_intent == 'smart_fallback')
            elif expected_type == 'manual':
                # Manual mode - confidence ต่ำหรือ none
                test_passed = (confidence < 0.45 or detected_intent == 'none')
            else:
                test_passed = False

            # นับผลลัพธ์
            if test_passed:
                passed += 1
                status = "✅ PASS"
            else:
                failed += 1
                status = "❌ FAIL"

            # แสดงผลลัพธ์
            print(f"[{i:3d}/{total_tests}] {status} | {category}")
            print(f"    Message: {message}")
            print(f"    Expected: {expected_intent} ({expected_type})")
            print(f"    Got: {detected_intent} → {used_intent} (conf: {confidence:.2f})")

            if not test_passed:
                print(f"    ❌ Expected {expected_type} but got different result")

            print(f"    Reply: {reply[:80]}{'...' if len(reply) > 80 else ''}")
            print()

            # เก็บผลลัพธ์
            test_result = {
                'scenario': category,
                'message': message,
                'description': description,
                'expected_intent': expected_intent,
                'expected_type': expected_type,
                'detected_intent': detected_intent,
                'used_intent': used_intent,
                'confidence': confidence,
                'test_passed': test_passed,
                'reply': reply
            }
            results.append(test_result)

        except Exception as e:
            failed += 1
            print(f"[{i:3d}/{total_tests}] ❌ ERROR | {category}")
            print(f"    Message: {message}")
            print(f"    Error: {e}")
            print()

            # เก็บผลลัพธ์ error
            test_result = {
                'scenario': category,
                'message': message,
                'description': description,
                'expected_intent': expected_intent,
                'expected_type': expected_type,
                'detected_intent': 'ERROR',
                'used_intent': 'ERROR',
                'confidence': 0.0,
                'test_passed': False,
                'reply': f"Error: {str(e)}"
            }
            results.append(test_result)

    # สรุปผลลัพธ์
    print("=" * 80)
    print(f"📊 สรุปผลการทดสอบ:")
    print(f"   ✅ ผ่าน: {passed}/{total_tests} ({passed/total_tests*100:.1f}%)")
    print(f"   ❌ ไม่ผ่าน: {failed}/{total_tests} ({failed/total_tests*100:.1f}%)")

    # สรุปตาม category
    print(f"\n📈 สรุปตามหมวดหมู่:")
    categories = {}
    for result in results:
        cat = result['scenario']
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if result['test_passed']:
            categories[cat]['passed'] += 1

    for cat, stats in categories.items():
        rate = stats['passed'] / stats['total'] * 100
        print(f"   {cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    # บันทึกผลลัพธ์
    if output_file:
        save_results(results, output_file)
        print(f"\n💾 บันทึกผลลัพธ์: {output_file}")

    return results

def save_results(results, output_file):
    """บันทึกผลลัพธ์เป็น JSON"""
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(results),
        'passed': sum(1 for r in results if r['test_passed']),
        'failed': sum(1 for r in results if not r['test_passed']),
        'results': results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

def main():
    """ฟังก์ชันหลัก"""
    # ตั้งค่า API key
    api_key = os.getenv('OPENAI_API_KEY', 'test-key')
    if api_key == 'test-key':
        print("⚠️  Warning: Using test API key, smart fallback will not work properly")

    # สร้าง Intent Detector
    print("🤖 กำลังโหลด Intent Detector...")
    detector = IntentDetector(api_key)

    # โหลดข้อมูลทดสอบ
    csv_file = 'test_scenarios.csv'
    scenarios = load_test_scenarios(csv_file)

    if not scenarios:
        print("❌ ไม่พบข้อมูลทดสอบ")
        return

    print(f"📋 โหลดข้อมูลทดสอบ: {len(scenarios)} scenarios")

    # รันการทดสอบ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.json"

    results = run_batch_test(scenarios, detector, output_file)

    print(f"\n🎉 การทดสอบเสร็จสิ้น!")
    print(f"📄 ผลลัพธ์ละเอียด: {output_file}")

if __name__ == "__main__":
    main()