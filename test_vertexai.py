#!/usr/bin/env python3
"""
Test Vertex AI / Gemini Flash Integration
Quick test to verify that the Vertex AI client can connect and make requests
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path to import our modules
sys.path.append('.')

from poc_implementation import VertexAIClient


async def test_vertex_ai():
    """Test the Vertex AI client connection and response"""

    print("=== Testing Vertex AI / Gemini Flash Integration ===\n")

    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

    print("Environment Check:")
    print(f"  Google Cloud Project: {project_id or 'NOT SET'}")
    print(f"  Credentials Path: {credentials_path or 'NOT SET'}")

    if not project_id:
        print("\n❌ GOOGLE_CLOUD_PROJECT not set. Please set up your .env file.")
        print("   Run: python setup_env.py")
        return False

    if credentials_path and not os.path.exists(credentials_path):
        print(f"\n❌ Credentials file not found: {credentials_path}")
        print("   Make sure the path in your .env file is correct.")
        return False

    try:
        print(f"\n🔌 Initializing Vertex AI client...")

        # Initialize the client
        client = VertexAIClient(project_id=project_id)

        print("✅ Client initialized successfully")

        # Test sample analysis
        print(f"\n🧪 Testing sample analysis...")

        test_headline = "Federal Reserve raises interest rates by 0.75 basis points"
        test_entity = "EURUSD"
        test_context = {
            'trade_partners': {'USA': 0.15, 'Germany': 0.12},
            'currency_group': ['major_currencies'],
            'economic_indicators': {'gdp_usd': 4.2e12, 'inflation_rate': 0.028}
        }

        # Make the API call
        result = await client.analyze_semantic_impact(
            test_headline, test_entity, test_context
        )

        print("✅ API call successful!")
        print("\nResponse:")
        print(f"  Model Used: {result.get('model_used', 'Unknown')}")
        print(f"  Confidence: {result.get('confidence', 0):.3f}")

        # Show probabilities
        if 'probabilities' in result:
            probs = result['probabilities']
            print("  Probabilities:")
            print(f"    Abstain: {probs.get('abstain', 0):.3f}")
            print(f"    Minor: {probs.get('case_1_minor', 0):.3f}")
            print(f"    Moderate: {probs.get('case_2_moderate', 0):.3f}")
            print(f"    Major: {probs.get('case_3_major', 0):.3f}")

        # Show reasoning (truncated)
        reasoning = result.get('reasoning', 'No reasoning provided')
        print(f"  Reasoning: {reasoning[:100]}...")

        print(f"\n✅ Vertex AI integration test passed!")
        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure you have installed: pip install google-cloud-aiplatform")
        return False

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nCommon issues:")
        print("  1. Invalid credentials or project ID")
        print("  2. Vertex AI API not enabled for your project")
        print("  3. Network connectivity issues")
        print("  4. Insufficient permissions on the service account")
        return False


async def test_integration_with_poc():
    """Test the full POC integration"""

    print("\n" + "="*60)
    print("Testing Full POC Integration")
    print("="*60)

    try:
        from poc_implementation import POCImpactAssessor

        # Initialize with Vertex AI (production mode)
        assessor = POCImpactAssessor(
            use_mock_llm=False,
            vertex_ai_project=os.getenv("GOOGLE_CLOUD_PROJECT")
        )

        print("✅ POC Assessor initialized with Vertex AI")

        # Test news analysis
        test_headline = "ECB announces emergency bond buying program"
        print(f"\n📰 Analyzing: {test_headline}")

        result = await assessor.analyze_news_impact(test_headline)

        print(f"✅ Analysis completed!")
        print(f"   Processing time: {result.total_processing_time_ms:.1f}ms")
        print(f"   Entities processed: {result.entities_processed}")
        print(f"   Overall confidence: {result.overall_confidence:.3f}")

        # Show top results
        if result.entity_assessments:
            print("\n📊 Top Impact Assessments:")
            for assessment in result.entity_assessments[:3]:
                probs = assessment.probabilities
                print(f"   {assessment.entity_id}:")
                print(f"     Major: {probs.case_3_major:.3f}, Moderate: {probs.case_2_moderate:.3f}")

        return True

    except Exception as e:
        print(f"❌ POC integration test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        # Test Vertex AI client directly
        vertex_ai_success = await test_vertex_ai()

        if vertex_ai_success:
            # Test full POC integration
            await test_integration_with_poc()
        else:
            print("\n⚠️  Skipping POC integration test due to Vertex AI issues")

        print(f"\n{'='*60}")
        print("Test Summary:")
        print(f"  Vertex AI Client: {'✅ PASS' if vertex_ai_success else '❌ FAIL'}")
        print(f"{'='*60}")

    asyncio.run(main())