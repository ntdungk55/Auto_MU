#!/usr/bin/env python3
"""Test specific OCR case for Imperial Guardian detection"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.logic.system_executor.ocr_text_processor import process_ocr_text

def test_specific_case():
    print("🔍 TEST CASE SPECIFIC - IMPERIAL GUARDIAN DETECTION")
    print("=" * 70)
    
    # Specific test case
    test_input = "kiện Imperial Guardian sẽ bát dầu sau 15 phút nữa QLTK: hk mugamethuvn info, hk gamethuvn com illiiiilll Đă thoát khỏi hội ChipY3u Đã gia nhập hội Cap nhat giá tai sàn giao dich: 1b 150 10s 2 bac, 1 tý Zen 200 bac Su bac."
    
    print(f"📝 Input: '{test_input}'")
    print(f"📏 Length: {len(test_input)} characters")
    
    # Process OCR text
    results = process_ocr_text(test_input)
    
    print(f"\n🎯 RESULTS: {len(results)} notifications found")
    
    # Analyze results
    imperial_guardian_started = None
    imperial_guardian_countdown = None
    other_notifications = []
    
    for result in results:
        print(f"\n📢 {result['type'].upper()}")
        print(f"   Text: '{result['text']}'")
        print(f"   Score: {result['score']}%")
        if result['vars']:
            print(f"   Variables: {result['vars']}")
        
        if result['type'] == 'imperial_guardian_started':
            imperial_guardian_started = result
        elif result['type'] == 'imperial_guardian_countdown':
            imperial_guardian_countdown = result
        else:
            other_notifications.append(result)
    
    print(f"\n" + "=" * 70)
    print("📊 EXPECTATION ANALYSIS")
    print("=" * 70)
    
    print(f"\n🎯 EXPECTED:")
    print(f"   ❌ NO 'imperial_guardian_started' notification")
    print(f"   ✅ YES 'imperial_guardian_countdown' notification")
    print(f"   📦 Variable x = '15'")
    
    print(f"\n🔍 ACTUAL:")
    print(f"   {'❌' if imperial_guardian_started else '✅'} 'imperial_guardian_started': {'FOUND' if imperial_guardian_started else 'NOT FOUND'}")
    print(f"   {'✅' if imperial_guardian_countdown else '❌'} 'imperial_guardian_countdown': {'FOUND' if imperial_guardian_countdown else 'NOT FOUND'}")
    
    if imperial_guardian_countdown:
        x_value = imperial_guardian_countdown['vars'].get('x', 'NOT_FOUND')
        print(f"   {'✅' if x_value == '15' else '❌'} Variable x: '{x_value}'")
    
    print(f"\n📋 Other notifications: {len(other_notifications)}")
    for other in other_notifications:
        print(f"   - {other['type']}: '{other['text'][:50]}...'")
    
    # Evaluate
    success = (
        imperial_guardian_started is None and
        imperial_guardian_countdown is not None and
        imperial_guardian_countdown['vars'].get('x') == '15'
    )
    
    print(f"\n🎉 TEST RESULT: {'✅ PASSED' if success else '❌ FAILED'}")
    
    if not success:
        print(f"\n❌ ISSUES:")
        if imperial_guardian_started:
            print(f"   - Unexpected 'imperial_guardian_started' detected")
        if not imperial_guardian_countdown:
            print(f"   - Missing 'imperial_guardian_countdown' detection")
        elif imperial_guardian_countdown['vars'].get('x') != '15':
            print(f"   - Wrong variable x: '{imperial_guardian_countdown['vars'].get('x')}' (expected '15')")
    
    return success

if __name__ == "__main__":
    test_specific_case()
