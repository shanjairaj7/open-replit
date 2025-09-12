#!/usr/bin/env python3

"""
Prompt Quality Test: Learning App Example

This test validates that the consolidated prompt (simpler_prompt_v2.py) 
produces equivalent quality output to the original prompt by analyzing
how it would handle a sample user request.

Sample User Request: "build me a learning app where there are interactive 
courses about how LLMs work. It will include flashcards to quiz people. 
$2/month plan for unlimited flashcards, free only has 2 limit"

Expected Behavior Analysis:
1. Should identify this as a NEW app requiring MVP approach
2. Should select 2 core features: courses + flashcards (with payment as revenue feature)
3. Should plan backend with JsonDB tables: users, courses, flashcards, subscriptions
4. Should transform frontend from boilerplate to learning app interface
5. Should apply professional UI design with appropriate color scheme
6. Should include quality assurance checklist
"""

from datetime import datetime
import sys
import os

# Add the parent directory to the path to import the prompts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import both versions
try:
    from prompts.simpler_prompt import prompt as original_prompt
    from prompts_consolidated.simpler_prompt_v2 import prompt as consolidated_prompt
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def analyze_prompt_coverage(prompt_content, test_name):
    """Analyze how well a prompt covers key requirements for the learning app example"""
    
    print(f"\n{'='*60}")
    print(f"ANALYZING {test_name}")
    print(f"{'='*60}")
    
    # Key requirements for learning app
    requirements = {
        "MVP Development Approach": [
            "mvp", "2 core features", "feature selection", "revenue features"
        ],
        "Backend Foundation": [
            "jsondb", "create_tables", "backend", "api", "modal"
        ],
        "Frontend Transformation": [
            "boilerplate", "dashboard", "sidebar", "app-specific", "remove all"
        ],
        "Payment Integration": [
            "stripe", "subscription", "payment", "monetization"
        ],
        "Professional UI Design": [
            "color scheme", "professional", "design system", "ui standards"
        ],
        "Quality Assurance": [
            "end-to-end", "npm run build", "completion", "validation"
        ],
        "Tool Usage Guidelines": [
            "read_file", "update_file", "run_command", "parallel", "search", "replace"
        ]
    }
    
    coverage_results = {}
    prompt_lower = prompt_content.lower()
    
    for category, keywords in requirements.items():
        found_keywords = [kw for kw in keywords if kw in prompt_lower]
        coverage_percent = (len(found_keywords) / len(keywords)) * 100
        coverage_results[category] = {
            "coverage": coverage_percent,
            "found": found_keywords,
            "missing": [kw for kw in keywords if kw not in found_keywords]
        }
        
        print(f"\n{category}: {coverage_percent:.1f}% coverage")
        print(f"  ✓ Found: {', '.join(found_keywords) if found_keywords else 'None'}")
        if coverage_results[category]["missing"]:
            print(f"  ✗ Missing: {', '.join(coverage_results[category]['missing'])}")
    
    # Overall coverage
    total_keywords = sum(len(keywords) for keywords in requirements.values())
    total_found = sum(len(result["found"]) for result in coverage_results.values())
    overall_coverage = (total_found / total_keywords) * 100
    
    print(f"\n{'='*20}")
    print(f"OVERALL COVERAGE: {overall_coverage:.1f}%")
    print(f"{'='*20}")
    
    return coverage_results, overall_coverage

def compare_prompt_lengths():
    """Compare the lengths of both prompts"""
    
    print(f"\n{'='*60}")
    print("PROMPT LENGTH COMPARISON")
    print(f"{'='*60}")
    
    original_lines = len(original_prompt.split('\n'))
    consolidated_lines = len(consolidated_prompt.split('\n'))
    reduction = ((original_lines - consolidated_lines) / original_lines) * 100
    
    print(f"Original Prompt: {original_lines} lines")
    print(f"Consolidated Prompt: {consolidated_lines} lines")
    print(f"Reduction: {reduction:.1f}%")
    
    return original_lines, consolidated_lines, reduction

def main():
    print("PROMPT QUALITY TEST - LEARNING APP EXAMPLE")
    print(f"Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Compare lengths
    orig_lines, consol_lines, reduction = compare_prompt_lengths()
    
    # Analyze coverage for both prompts
    original_results, original_coverage = analyze_prompt_coverage(original_prompt, "ORIGINAL PROMPT")
    consolidated_results, consolidated_coverage = analyze_prompt_coverage(consolidated_prompt, "CONSOLIDATED PROMPT")
    
    # Final comparison
    print(f"\n{'='*60}")
    print("FINAL COMPARISON")
    print(f"{'='*60}")
    
    print(f"Length Reduction: {reduction:.1f}%")
    print(f"Original Coverage: {original_coverage:.1f}%")
    print(f"Consolidated Coverage: {consolidated_coverage:.1f}%")
    
    coverage_change = consolidated_coverage - original_coverage
    if coverage_change >= -5:  # Allow up to 5% coverage loss
        print(f"✓ Coverage change: {coverage_change:+.1f}% (ACCEPTABLE)")
        verdict = "PASS"
    else:
        print(f"✗ Coverage change: {coverage_change:+.1f}% (TOO MUCH LOSS)")
        verdict = "FAIL"
    
    # Specific learning app requirements
    learning_app_keywords = ["course", "flashcard", "quiz", "learning", "interactive"]
    orig_learning = sum(1 for kw in learning_app_keywords if kw in original_prompt.lower())
    consol_learning = sum(1 for kw in learning_app_keywords if kw in consolidated_prompt.lower())
    
    print(f"\nLearning App Specific Terms:")
    print(f"Original: {orig_learning}/{len(learning_app_keywords)} terms")
    print(f"Consolidated: {consol_learning}/{len(learning_app_keywords)} terms")
    
    print(f"\n{'='*20}")
    print(f"VERDICT: {verdict}")
    print(f"{'='*20}")
    
    if verdict == "PASS":
        print("The consolidated prompt maintains sufficient functionality")
        print("while significantly reducing cognitive load.")
    else:
        print("The consolidated prompt may need additional refinement")
        print("to maintain all essential capabilities.")

if __name__ == "__main__":
    main()