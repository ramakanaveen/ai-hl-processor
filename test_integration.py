"""
Quick integration test for Phase 1
Tests the complete flow: Request → API → POCImpactAssessor → Response
"""

import asyncio
import sys
sys.path.insert(0, '.')

from poc_implementation import POCImpactAssessor
from api_service import convert_to_simplified_output
from models import NewsAnalysisRequest

async def test_integration():
    print("=" * 60)
    print("Phase 1 Integration Test")
    print("=" * 60)

    # Initialize assessor
    print("\n1. Initializing POCImpactAssessor...")
    assessor = POCImpactAssessor()
    print("   ✅ Assessor initialized (using mock LLM)")

    # Test headline
    test_headline = "Federal Reserve raises interest rates by 0.75 basis points"
    print(f"\n2. Testing headline: '{test_headline}'")

    # Run analysis
    print("   Running analysis...")
    result = await assessor.analyze_news_impact(test_headline)

    print(f"   ✅ Analysis completed in {result.total_processing_time_ms:.1f}ms")
    print(f"   ✅ Entities processed: {result.entities_processed}")
    print(f"   ✅ Overall confidence: {result.overall_confidence:.3f}")

    # Convert to Phase 1 format
    print("\n3. Converting to Phase 1 simplified format...")
    simplified = convert_to_simplified_output(result, min_confidence=0.3)

    print(f"   ✅ Impacted entities: {len(simplified.impacted_entities)}")
    print(f"   ✅ Processing time: {simplified.processing_time_ms:.1f}ms")

    # Display results
    print("\n4. Results:")
    print(f"   Headline: {simplified.headline}")
    print(f"   \n   Impacted Currencies:")

    for entity in simplified.impacted_entities[:5]:  # Show top 5
        conf_emoji = "🟢" if entity.confidence == "high" else "🟡" if entity.confidence == "medium" else "🔴"
        print(f"     {conf_emoji} {entity.currency:8} - {entity.confidence.upper():6} ({entity.confidence_score:.2f})")
        print(f"        → {entity.reasoning[:80]}...")

    print("\n" + "=" * 60)
    print("✅ Integration test PASSED!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_integration())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
