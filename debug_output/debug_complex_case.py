#!/usr/bin/env python3
"""Debug complex OCR case that failed"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.logic.system_executor.ocr_text_processor import process_ocr_text, tokenize, PATTERNS, match_pattern

def debug_complex_case():
    print("🔍 DEBUG COMPLEX OCR CASE")
    print("=" * 70)
    
    # Failed test case
    test_input = "Còn 3 phút dể tham gia trong Hỗn Nguyên Lau kiện Imperial Guardian se bát đau sau 1Olphút nữa Còn 2 phút đẻ tham gia trong Hỗn Nguyên Lau Còn 1 phút để tham gia trong Hỗn Nguyên Lâu Cap nhat giá tai sàn giao dich: 1b 149 10s 2 bac, 1 tý Zen 200 bac Sự bac."
    
    print(f"📝 Input: '{test_input}'")
    print(f"📏 Length: {len(test_input)} characters")
    
    # Tokenize
    tokens = tokenize(test_input)
    print(f"\n🧩 TOKENS ({len(tokens)}):")
    for i, token in enumerate(tokens[:20]):  # Show first 20
        print(f"  {i+1:2d}. '{token.raw}' -> '{token.norm}'")
    if len(tokens) > 20:
        print(f"  ... and {len(tokens) - 20} more tokens")
    
    # Find Imperial Guardian in tokens
    print(f"\n🔍 SEARCHING FOR IMPERIAL GUARDIAN:")
    for i, token in enumerate(tokens):
        if 'imperial' in token.norm.lower() or 'guardian' in token.norm.lower():
            print(f"  Found at position {i}: '{token.raw}' -> '{token.norm}'")
            
            # Check surrounding tokens
            start = max(0, i - 5)
            end = min(len(tokens), i + 10)
            print(f"  Context ({start}-{end}):")
            for j in range(start, end):
                token_j = tokens[j]
                marker = "👉" if j == i else "   "
                print(f"  {marker} {j:2d}. '{token_j.raw}' -> '{token_j.norm}'")
    
    # Test patterns against Imperial Guardian location
    print(f"\n🎯 TESTING PATTERNS:")
    imperial_guardian_patterns = [p for p in PATTERNS if 'imperial_guardian' in p['id']]
    
    for pattern in imperial_guardian_patterns:
        print(f"\n📋 Pattern: {pattern['id']}")
        print(f"   Template: {pattern['template']}")
        print(f"   Pattern: {pattern['pattern']}")
        
        # Try to match at each position
        for i in range(len(tokens)):
            if i + len(pattern['pattern']) <= len(tokens):
                match = match_pattern(tokens, i, pattern['pattern'])
                if match:
                    print(f"   ✅ MATCH at position {i}")
                    print(f"      Score: {match['score']:.1f}%")
                    print(f"      Variables: {match['variables']}")
                    
                    # Show matched text
                    end_pos = i + len(pattern['pattern'])
                    matched_text = " ".join([tokens[j].raw for j in range(i, end_pos)])
                    print(f"      Matched: '{matched_text}'")
                else:
                    # Show why it failed
                    if i < 5:  # Only show first few attempts
                        end_pos = i + len(pattern['pattern'])
                        if end_pos <= len(tokens):
                            tokens_subset = tokens[i:end_pos]
                            expected_tokens = pattern['pattern']
                            print(f"   ❌ No match at position {i}")
                            print(f"      Expected: {expected_tokens}")
                            actual_norms = [t.norm for t in tokens_subset]
                            print(f"      Actual:   {actual_norms}")
    
    # Run full processor
    print(f"\n🔄 FULL PROCESSOR RESULTS:")
    results = process_ocr_text(test_input)
    
    print(f"📊 Found {len(results)} notifications:")
    for i, result in enumerate(results, 1):
        print(f"\n#{i} 📢 {result['type'].upper()}")
        print(f"   Text: '{result['text']}'")
        print(f"   Score: {result['score']}%")
        if result['vars']:
            print(f"   Variables: {result['vars']}")

if __name__ == "__main__":
    debug_complex_case()
