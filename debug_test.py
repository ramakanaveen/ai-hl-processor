#!/usr/bin/env python3

import traceback
import sys
import os

# Add current directory to path
sys.path.append('.')

try:
    print("Testing imports...")
    from poc_implementation import POCImpactAssessor
    print("✅ Import successful")

    print("Testing POC initialization...")
    assessor = POCImpactAssessor(use_mock_llm=True)
    print("✅ POC initialized with mock LLM")

    print("Testing with production LLM...")
    assessor_prod = POCImpactAssessor(use_mock_llm=False)
    print("✅ POC initialized with production LLM")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nFull traceback:")
    traceback.print_exc()