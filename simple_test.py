#!/usr/bin/env python3
"""
Simple test without config system to verify Vertex AI works
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append('.')

from poc_implementation import POCImpactAssessor

async def simple_test():
    print("=== Simple Vertex AI Test ===\n")

    # Test with mock LLM first
    print("1. Testing with mock LLM...")
    assessor_mock = POCImpactAssessor(use_mock_llm=True)

    result_mock = await assessor_mock.analyze_news_impact(
        "Fed raises interest rates by 0.75%"
    )

    print(f"✅ Mock LLM test successful - {result_mock.entities_processed} entities processed")

    # Test with Vertex AI
    print("\n2. Testing with Vertex AI...")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if project_id:
        assessor_vertex = POCImpactAssessor(
            use_mock_llm=False,
            vertex_ai_project=project_id
        )

        result_vertex = await assessor_vertex.analyze_news_impact(
            "Russia attacks Ukraine energy infrastructure"
        )

        print(f"✅ Vertex AI test successful - {result_vertex.entities_processed} entities processed")
        print(f"   Processing time: {result_vertex.total_processing_time_ms:.1f}ms")

        # Show results
        if result_vertex.entity_assessments:
            assessment = result_vertex.entity_assessments[0]
            probs = assessment.probabilities
            print(f"   Top entity: {assessment.entity_id}")
            print(f"   Major impact: {probs.case_3_major:.3f}")
            print(f"   Model used: {getattr(assessment.probabilities, 'model_used', 'Unknown')}")
    else:
        print("❌ No GOOGLE_CLOUD_PROJECT found in environment")

if __name__ == "__main__":
    asyncio.run(simple_test())