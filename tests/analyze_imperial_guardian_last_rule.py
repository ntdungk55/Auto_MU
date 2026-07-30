#!/usr/bin/env python3
"""Analyze impact of 'last Imperial Guardian notification only' rule on test cases"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.logic.system_executor.ocr_text_processor import process_ocr_text

def analyze_imperial_guardian_last_rule():
    print("🔍 ANALYZE IMPACT OF 'LAST IMPERIAL GUARDIAN NOTIFICATION ONLY' RULE")
    print("=" * 80)
    
    # Test cases that will be affected
    affected_cases = [
        {
            "name": "Test 16 - Multiple Events - Red Dragon + Imperial Guardian",
            "input": "kiện Rồng Đỏ tấn công sẽ bắt dầu sau 15 phút nữa 4 minutes are lell to enter the welcome staff. kiện Imperial Guardian sẽ bắt đằu sau 1 phút nữa 3 minutes are left to enter the welcome staff. kiện Imperial Guardian dã bát dầu 2 minutes are lell to enter the welcome staff. Su Sự Su",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "imperial_guardian_started",  # Last Imperial Guardian
        },
        {
            "name": "Test 17 - Both Started and Countdown Events",
            "input": "kiện Đò tan công sẽ băt đàu sau 15 phút nữa 4 minutes are left to enter the welcome staff. Sự kiện Imperial Guardian sẽ bát đầu sau 1 phút nữa 3 minutes are left to enter the welcome staff. Sự kiện Imperial Guardian đà bắt đầu 2 minutes are left to enter the welcome staff. Ps 1c 6 45 Sự Róng A 6",
            "current_expected": "imperial_guardian_countdown",
            "new_expected": "imperial_guardian_started",  # Last Imperial Guardian
        }
    ]
    
    print("📋 TEST CASES THAT WILL BE AFFECTED:")
    print("=" * 80)
    
    for i, case in enumerate(affected_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   Input: '{case['input'][:100]}...'")
        print(f"   Current expected: {case['current_expected']}")
        print(f"   New expected: {case['new_expected']}")
        
        # Process to see current results
        results = process_ocr_text(case['input'])
        print(f"   Current results ({len(results)} notifications):")
        
        imperial_guardian_notifications = []
        for j, result in enumerate(results, 1):
            if 'imperial_guardian' in result['type']:
                last_marker = " (LAST IG)" if j == len([r for r in results if 'imperial_guardian' in r['type']]) and imperial_guardian_notifications else ""
                imperial_guardian_notifications.append(result)
                print(f"     #{j} {result['type']}{last_marker}")
            else:
                print(f"     #{j} {result['type']} (other)")
        
        if len(imperial_guardian_notifications) > 1:
            print(f"   ⚠️  WILL CHANGE: Will return {imperial_guardian_notifications[-1]['type']} instead of {imperial_guardian_notifications[0]['type']}")
        elif len(imperial_guardian_notifications) == 1:
            print(f"   ✅ NO CHANGE: Only one Imperial Guardian notification")
        else:
            print(f"   ✅ NO CHANGE: No Imperial Guardian notifications")
    
    print(f"\n" + "=" * 80)
    print("📊 SUMMARY OF CHANGES NEEDED:")
    print("=" * 80)
    
    total_affected = len(affected_cases)
    print(f"📈 Total test cases affected: {total_affected}")
    
    changes_needed = []
    for case in affected_cases:
        results = process_ocr_text(case['input'])
        imperial_guardian_notifications = [r for r in results if 'imperial_guardian' in r['type']]
        if len(imperial_guardian_notifications) > 1:
            changes_needed.append(case['name'])
    
    print(f"🔧 Test cases needing updates: {len(changes_needed)}")
    for name in changes_needed:
        print(f"   - {name}")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"1. Update test expectations to match last Imperial Guardian notification")
    print(f"2. Implement 'last Imperial Guardian only' logic in processor")
    print(f"3. Re-run all tests to verify new behavior")
    print(f"4. This rule makes sense: latest event state is most relevant")

if __name__ == "__main__":
    analyze_imperial_guardian_last_rule()
