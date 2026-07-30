#!/usr/bin/env python3
"""Analyze impact of 'last notification only' rule on test cases"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.logic.system_executor.ocr_text_processor import process_ocr_text

def analyze_last_notification_rule():
    print("🔍 ANALYZE IMPACT OF 'LAST NOTIFICATION ONLY' RULE")
    print("=" * 70)
    
    # Test cases that will be affected
    affected_cases = [
        {
            "name": "Test 13 - Real-world OCR with Multiple Notifications",
            "input": "kiện Imperial Guardian sẽ bát dầu sau 15 phút nữa QLTK: hk mugamethuvn info, hk gamethuvn com illiiiilll Đă thoát khỏi hội ChipY3u Đã gia nhập hội Cap nhat giá tai sàn giao dich: 1b 150 10s 2 bac, 1 tý Zen 200 bac Su bac.",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "market_price"  # Last notification
        },
        {
            "name": "Test 14 - Complex OCR with Multiple Countdowns",
            "input": "Còn 3 phút dể tham gia trong Hỗn Nguyên Lau kiện Imperial Guardian se bát đau sau 1Olphút nữa Còn 2 phút đẻ tham gia trong Hỗn Nguyên Lau Còn 1 phút để tham gia trong Hỗn Nguyên Lâu Cap nhat giá tai sàn giao dich: 1b 149 10s 2 bac, 1 tý Zen 200 bac Sự bac.",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "market_price"  # Last notification
        },
        {
            "name": "Test 15 - Verify No Started + Has Countdown",
            "input": "Còn 3 phút dể tham gia trong Hỗn Nguyên Lau kiện Imperial Guardian se bát đau sau 1Olphút nữa Còn 2 phút đẻ tham gia trong Hỗn Nguyên Lau Còn 1 phút để tham gia trong Hỗn Nguyên Lâu Cap nhat giá tai sàn giao dich: 1b 149 10s 2 bac, 1 tý Zen 200 bac Sự bac.",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "market_price"  # Last notification
        },
        {
            "name": "Test 16 - Multiple Events - Red Dragon + Imperial Guardian",
            "input": "kiện Rồng Đỏ tấn công sẽ bắt dầu sau 15 phút nữa 4 minutes are lell to enter the welcome staff. kiện Imperial Guardian sẽ bắt đằu sau 1 phút nữa 3 minutes are left to enter the welcome staff. kiện Imperial Guardian dã bát dầu 2 minutes are lell to enter the welcome staff. Su Sự Su",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "welcome_staff"  # Last notification
        },
        {
            "name": "Test 17 - Both Started and Countdown Events",
            "input": "kiện Đò tan công sẽ băt đàu sau 15 phút nữa 4 minutes are left to enter the welcome staff. Sự kiện Imperial Guardian sẽ bát đầu sau 1 phút nữa 3 minutes are left to enter the welcome staff. Sự kiện Imperial Guardian đà bắt đầu 2 minutes are left to enter the welcome staff. Ps 1c 6 45 Sự Róng A 6",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "welcome_staff"  # Last notification
        }
    ]
    
    print("📋 TEST CASES THAT WILL BE AFFECTED:")
    print("=" * 70)
    
    for i, case in enumerate(affected_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   Input: '{case['input'][:100]}...'")
        print(f"   Current expected: {case['current_expected']}")
        print(f"   New expected: {case['new_expected']}")
        
        # Process to see current results
        results = process_ocr_text(case['input'])
        print(f"   Current results ({len(results)} notifications):")
        for j, result in enumerate(results, 1):
            last_marker = " (LAST)" if j == len(results) else ""
            print(f"     #{j} {result['type']}{last_marker}")
        
        if len(results) > 1:
            print(f"   ⚠️  WILL CHANGE: Will return {results[-1]['type']} instead of {results[0]['type']}")
        else:
            print(f"   ✅ NO CHANGE: Only one notification")
    
    print(f"\n" + "=" * 70)
    print("📊 SUMMARY OF CHANGES NEEDED:")
    print("=" * 70)
    
    total_affected = len(affected_cases)
    print(f"📈 Total test cases affected: {total_affected}")
    
    changes_needed = []
    for case in affected_cases:
        results = process_ocr_text(case['input'])
        if len(results) > 1:
            changes_needed.append(case['name'])
    
    print(f"🔧 Test cases needing updates: {len(changes_needed)}")
    for name in changes_needed:
        print(f"   - {name}")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"1. Update test expectations to match last notification")
    print(f"2. Implement 'last notification only' logic in processor")
    print(f"3. Re-run all tests to verify new behavior")
    print(f"4. Consider if this rule aligns with business requirements")

if __name__ == "__main__":
    analyze_last_notification_rule()
