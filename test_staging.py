#!/usr/bin/env python3
"""
Test Staging Environment
Test the system in staging mode with proper configuration
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

async def test_staging():
    print("=== Staging Environment Test ===\n")

    # Test news headlines
    test_headlines = [
        "Russia attacks Ukraine energy infrastructure",
        "Fed raises interest rates by 0.75 basis points",
        "ECB announces emergency bond buying program",
        "China restricts semiconductor exports to Western countries"
    ]

    print("Testing with staging configuration...")
    print(f"Project ID: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"Credentials: {os.getenv('GOOGLE_CREDENTIALS_PATH')}")
    print()

    # Initialize assessor for staging (use real Vertex AI)
    assessor = POCImpactAssessor(
        use_mock_llm=False,  # Use real Vertex AI
        vertex_ai_project=os.getenv("GOOGLE_CLOUD_PROJECT")
    )

    for i, headline in enumerate(test_headlines, 1):
        print(f"{i}. Testing: {headline}")
        print("-" * 60)

        try:
            result = await assessor.analyze_news_impact(headline)

            print(f"✅ Analysis completed")
            print(f"   Processing time: {result.total_processing_time_ms:.1f}ms")
            print(f"   Entities processed: {result.entities_processed}")
            print(f"   Overall confidence: {result.overall_confidence:.3f}")

            # Show top 3 results
            if result.entity_assessments:
                print("   Top impacts:")
                for assessment in result.entity_assessments[:3]:
                    probs = assessment.probabilities
                    print(f"     {assessment.entity_id}:")
                    print(f"       Major: {probs.case_3_major:.3f}, "
                          f"Moderate: {probs.case_2_moderate:.3f}, "
                          f"Minor: {probs.case_1_minor:.3f}")

            print()

        except Exception as e:
            print(f"❌ Error: {e}")
            print()

    # Show performance stats
    print("=" * 60)
    print("Performance Statistics:")
    stats = assessor.get_performance_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_staging())