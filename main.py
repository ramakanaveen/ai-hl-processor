#!/usr/bin/env python3
"""
Main Entry Point for Financial News Impact Analysis System
Provides CLI interface for running the POC and production systems
"""

import asyncio
import argparse
import sys
import json
import time
import os
from typing import List, Optional
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from poc_implementation import POCImpactAssessor
from config_loader import get_config
from semantic_impact_engine import SemanticImpactEngine
from economic_knowledge_graph import EconomicKnowledgeBase

# Configure logging (will be updated based on config)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAnalysisCLI:
    """Command-line interface for the news analysis system"""

    def __init__(self):
        self.assessor = None
        self.config = None

    def setup_argument_parser(self) -> argparse.ArgumentParser:
        """Setup command line argument parser"""
        parser = argparse.ArgumentParser(
            description="Financial News Impact Analysis System",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Analyze a single news headline
  python main.py analyze "Fed raises interest rates by 0.75%"

  # Analyze with specific entities
  python main.py analyze "ECB bond buying program" --entities EURUSD GBPUSD

  # Run in production mode
  python main.py analyze "Russia attacks Ukraine" --environment prod

  # Batch process from file
  python main.py batch --input headlines.txt --output results.json

  # Run demo with sample headlines
  python main.py demo

  # Test system components
  python main.py test
            """
        )

        parser.add_argument(
            '--environment', '-e',
            choices=['test', 'dev', 'uat', 'prod'],
            default=None,
            help='Environment to run in (default: from ENV variable or test)'
        )

        parser.add_argument(
            '--config-file', '-c',
            type=str,
            help='Path to configuration file'
        )

        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Analyze command
        analyze_parser = subparsers.add_parser('analyze', help='Analyze a single news headline')
        analyze_parser.add_argument('headline', help='News headline to analyze')
        analyze_parser.add_argument(
            '--entities', '-n',
            nargs='+',
            help='Specific entities to analyze (default: auto-detect)'
        )
        analyze_parser.add_argument(
            '--output', '-o',
            type=str,
            help='Output file for results (JSON format)'
        )
        analyze_parser.add_argument(
            '--format',
            choices=['json', 'table', 'summary'],
            default='summary',
            help='Output format (default: summary)'
        )

        # Batch command
        batch_parser = subparsers.add_parser('batch', help='Batch process multiple headlines')
        batch_parser.add_argument(
            '--input', '-i',
            required=True,
            help='Input file with headlines (one per line)'
        )
        batch_parser.add_argument(
            '--output', '-o',
            required=True,
            help='Output file for results (JSON format)'
        )
        batch_parser.add_argument(
            '--max-concurrent',
            type=int,
            default=5,
            help='Maximum concurrent analyses (default: 5)'
        )

        # Demo command
        demo_parser = subparsers.add_parser('demo', help='Run demonstration with sample headlines')
        demo_parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of sample headlines to process (default: 5)'
        )

        # Test command
        test_parser = subparsers.add_parser('test', help='Test system components')
        test_parser.add_argument(
            '--component',
            choices=['all', 'semantic', 'economic', 'features', 'poc'],
            default='all',
            help='Component to test (default: all)'
        )

        # Benchmark command
        benchmark_parser = subparsers.add_parser('benchmark', help='Performance benchmark')
        benchmark_parser.add_argument(
            '--iterations',
            type=int,
            default=10,
            help='Number of benchmark iterations (default: 10)'
        )

        return parser

    async def initialize_system(self, args):
        """Initialize the analysis system"""
        # Initialize configuration (will auto-detect environment from ENV or use 'test')
        config_file = args.config_file if args.config_file else "config.ini"
        self.config = get_config(args.environment, config_file)

        # Set logging level based on configuration
        log_level = getattr(logging, self.config.monitoring_config.log_level.upper())
        if args.verbose:
            log_level = logging.DEBUG
        logging.getLogger().setLevel(log_level)

        logger.info(f"Initializing system in {self.config.environment} environment")

        # Initialize assessor (configuration will determine mock vs real LLM)
        self.assessor = POCImpactAssessor()

        logger.info("System initialization complete")

    async def run_analyze_command(self, args):
        """Run single headline analysis"""
        logger.info(f"Analyzing headline: {args.headline}")

        start_time = time.time()
        result = await self.assessor.analyze_news_impact(
            args.headline,
            target_entities=args.entities
        )
        end_time = time.time()

        if args.format == 'json':
            self._print_json_results(result)
        elif args.format == 'table':
            self._print_table_results(result)
        else:  # summary
            self._print_summary_results(result)

        logger.info(f"Analysis completed in {(end_time - start_time) * 1000:.1f}ms")

        # Save to file if requested
        if args.output:
            filename = self.assessor.export_results_to_json(result, args.output)
            logger.info(f"Results saved to {filename}")

    async def run_batch_command(self, args):
        """Run batch processing"""
        logger.info(f"Starting batch processing from {args.input}")

        # Read headlines from file
        headlines = self._read_headlines_file(args.input)
        logger.info(f"Processing {len(headlines)} headlines")

        # Process in batches
        all_results = []
        semaphore = asyncio.Semaphore(args.max_concurrent)

        async def process_headline(headline):
            async with semaphore:
                return await self.assessor.analyze_news_impact(headline)

        # Execute batch processing
        start_time = time.time()
        results = await asyncio.gather(
            *[process_headline(headline) for headline in headlines],
            return_exceptions=True
        )
        end_time = time.time()

        # Filter successful results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_count = len(results) - len(successful_results)

        logger.info(f"Batch processing completed in {(end_time - start_time):.2f}s")
        logger.info(f"Successful: {len(successful_results)}, Failed: {failed_count}")

        # Save results
        self._save_batch_results(successful_results, args.output)

    async def run_demo_command(self, args):
        """Run demonstration with sample headlines"""
        sample_headlines = [
            "Russia launches missile attack on Ukrainian energy infrastructure",
            "Federal Reserve raises interest rates by 0.75 basis points amid inflation concerns",
            "China announces new trade restrictions on semiconductor exports to Western countries",
            "ECB President signals potential emergency bond buying program amid eurozone crisis",
            "OPEC+ announces surprise oil production cut of 2 million barrels per day",
            "Bank of England emergency intervention in UK gilt market after pension fund crisis",
            "Switzerland central bank intervenes to support franc amid banking sector concerns",
            "Japan intervenes in currency markets as yen hits 32-year low against dollar"
        ]

        headlines_to_process = sample_headlines[:args.count]

        print("=" * 80)
        print("Financial News Impact Analysis - DEMONSTRATION")
        print("=" * 80)

        for i, headline in enumerate(headlines_to_process, 1):
            print(f"\n{i}. Analyzing: {headline}")
            print("-" * 80)

            result = await self.assessor.analyze_news_impact(headline)
            self._print_summary_results(result)

        # Show overall performance statistics
        print("\n" + "=" * 80)
        print("PERFORMANCE STATISTICS")
        print("=" * 80)
        stats = self.assessor.get_performance_stats()
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

    async def run_test_command(self, args):
        """Run system component tests"""
        print("=" * 80)
        print("SYSTEM COMPONENT TESTS")
        print("=" * 80)

        if args.component in ['all', 'semantic']:
            print("\n1. Testing Semantic Impact Engine...")
            await self._test_semantic_engine()

        if args.component in ['all', 'economic']:
            print("\n2. Testing Economic Knowledge Graph...")
            self._test_economic_graph()

        if args.component in ['all', 'features']:
            print("\n3. Testing Feature Engineering...")
            self._test_feature_engineering()

        if args.component in ['all', 'poc']:
            print("\n4. Testing POC Implementation...")
            await self._test_poc_implementation()

        print("\nAll tests completed!")

    async def run_benchmark_command(self, args):
        """Run performance benchmark"""
        print("=" * 80)
        print("PERFORMANCE BENCHMARK")
        print("=" * 80)

        test_headline = "Federal Reserve announces emergency rate cut amid market volatility"
        times = []

        print(f"Running {args.iterations} iterations of impact analysis...")

        for i in range(args.iterations):
            start_time = time.time()
            result = await self.assessor.analyze_news_impact(test_headline)
            end_time = time.time()

            iteration_time = (end_time - start_time) * 1000
            times.append(iteration_time)

            if (i + 1) % 5 == 0:
                print(f"Completed {i + 1}/{args.iterations} iterations")

        # Calculate statistics
        import numpy as np
        print(f"\nBenchmark Results:")
        print(f"  Average time: {np.mean(times):.1f}ms")
        print(f"  Median time: {np.median(times):.1f}ms")
        print(f"  95th percentile: {np.percentile(times, 95):.1f}ms")
        print(f"  Min time: {np.min(times):.1f}ms")
        print(f"  Max time: {np.max(times):.1f}ms")

    def _read_headlines_file(self, filename: str) -> List[str]:
        """Read headlines from file"""
        with open(filename, 'r', encoding='utf-8') as f:
            headlines = [line.strip() for line in f if line.strip()]
        return headlines

    def _save_batch_results(self, results, filename: str):
        """Save batch results to file"""
        batch_data = {
            'processing_timestamp': time.time(),
            'total_results': len(results),
            'results': []
        }

        for result in results:
            result_data = {
                'headline': result.news_headline,
                'processing_time_ms': result.total_processing_time_ms,
                'entities_processed': result.entities_processed,
                'overall_confidence': result.overall_confidence,
                'entity_assessments': [
                    {
                        'entity_id': assessment.entity_id,
                        'entity_type': assessment.entity_type,
                        'probabilities': {
                            'abstain': assessment.probabilities.abstain,
                            'minor': assessment.probabilities.case_1_minor,
                            'moderate': assessment.probabilities.case_2_moderate,
                            'major': assessment.probabilities.case_3_major
                        },
                        'confidence': assessment.confidence_score
                    }
                    for assessment in result.entity_assessments
                ]
            }
            batch_data['results'].append(result_data)

        with open(filename, 'w') as f:
            json.dump(batch_data, f, indent=2)

        logger.info(f"Batch results saved to {filename}")

    def _print_json_results(self, result):
        """Print results in JSON format"""
        result_dict = {
            'headline': result.news_headline,
            'processing_time_ms': result.total_processing_time_ms,
            'entities_processed': result.entities_processed,
            'overall_confidence': result.overall_confidence,
            'entity_assessments': [
                {
                    'entity_id': assessment.entity_id,
                    'probabilities': {
                        'abstain': assessment.probabilities.abstain,
                        'minor': assessment.probabilities.case_1_minor,
                        'moderate': assessment.probabilities.case_2_moderate,
                        'major': assessment.probabilities.case_3_major
                    },
                    'reasoning': assessment.reasoning,
                    'confidence': assessment.confidence_score
                }
                for assessment in result.entity_assessments
            ]
        }
        print(json.dumps(result_dict, indent=2))

    def _print_table_results(self, result):
        """Print results in table format"""
        print(f"Headline: {result.news_headline}")
        print(f"Processing Time: {result.total_processing_time_ms:.1f}ms")
        print(f"Overall Confidence: {result.overall_confidence:.3f}")
        print()

        if result.entity_assessments:
            print(f"{'Entity':<15} {'Abstain':<8} {'Minor':<8} {'Moderate':<8} {'Major':<8} {'Confidence':<10}")
            print("-" * 70)

            for assessment in result.entity_assessments:
                probs = assessment.probabilities
                print(f"{assessment.entity_id:<15} "
                      f"{probs.abstain:<8.3f} "
                      f"{probs.case_1_minor:<8.3f} "
                      f"{probs.case_2_moderate:<8.3f} "
                      f"{probs.case_3_major:<8.3f} "
                      f"{assessment.confidence_score:<10.3f}")

    def _print_summary_results(self, result):
        """Print results in summary format"""
        print(f"Processing Time: {result.total_processing_time_ms:.1f}ms")
        print(f"Entities Processed: {result.entities_processed}")
        print(f"Overall Confidence: {result.overall_confidence:.3f}")

        if result.semantic_event:
            print(f"Event Type: {result.semantic_event.event_type.value}")
            print(f"Severity: {result.semantic_event.severity.value}")

        # Show top 5 impact assessments
        if result.entity_assessments:
            top_assessments = sorted(
                result.entity_assessments,
                key=lambda x: x.probabilities.case_3_major,
                reverse=True
            )[:5]

            print("\nTop Impact Assessments:")
            for assessment in top_assessments:
                probs = assessment.probabilities
                print(f"  {assessment.entity_id}:")
                print(f"    Major: {probs.case_3_major:.3f}, "
                      f"Moderate: {probs.case_2_moderate:.3f}, "
                      f"Minor: {probs.case_1_minor:.3f}")
                print(f"    Confidence: {assessment.confidence_score:.3f}")

    async def _test_semantic_engine(self):
        """Test semantic impact engine"""
        try:
            from semantic_impact_engine import SemanticImpactEngine
            engine = SemanticImpactEngine()

            test_headline = "Russia attacks Ukraine energy infrastructure"
            result = await engine.analyze_news_impact(test_headline)

            if result.get('semantic_event'):
                print("  ✓ Semantic event extraction working")
            else:
                print("  ✗ Semantic event extraction failed")

            if result.get('entity_assessments'):
                print("  ✓ Entity impact assessment working")
            else:
                print("  ✗ Entity impact assessment failed")

        except Exception as e:
            print(f"  ✗ Semantic engine test failed: {e}")

    def _test_economic_graph(self):
        """Test economic knowledge graph"""
        try:
            from economic_knowledge_graph import EconomicKnowledgeBase, EconomicRelationshipGraph

            kb = EconomicKnowledgeBase()
            graph = EconomicRelationshipGraph(kb)

            # Test entity context
            context = kb.get_entity_context('Germany')
            if context and 'trade_partners' in context:
                print("  ✓ Economic context retrieval working")
            else:
                print("  ✗ Economic context retrieval failed")

            # Test relationship graph
            related = graph.get_related_entities('Russia')
            if related:
                print("  ✓ Economic relationship graph working")
            else:
                print("  ✗ Economic relationship graph failed")

        except Exception as e:
            print(f"  ✗ Economic graph test failed: {e}")

    def _test_feature_engineering(self):
        """Test feature engineering"""
        try:
            from feature_engineering import ContextualFeatureBuilder, EntityType
            from economic_knowledge_graph import EconomicKnowledgeBase

            kb = EconomicKnowledgeBase()
            builder = ContextualFeatureBuilder(kb)

            test_headline = "Fed raises interest rates"
            feature_vector = builder.build_features(
                test_headline, "EURUSD", EntityType.CURRENCY
            )

            if feature_vector.to_array().size > 0:
                print("  ✓ Feature engineering working")
            else:
                print("  ✗ Feature engineering failed")

        except Exception as e:
            print(f"  ✗ Feature engineering test failed: {e}")

    async def _test_poc_implementation(self):
        """Test POC implementation"""
        try:
            test_headline = "ECB announces bond buying program"
            result = await self.assessor.analyze_news_impact(test_headline)

            if result.entity_assessments:
                print("  ✓ POC implementation working")
            else:
                print("  ✗ POC implementation failed")

        except Exception as e:
            print(f"  ✗ POC implementation test failed: {e}")


async def main():
    """Main entry point"""
    cli = NewsAnalysisCLI()
    parser = cli.setup_argument_parser()

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Initialize system
        await cli.initialize_system(args)

        # Run command
        if args.command == 'analyze':
            await cli.run_analyze_command(args)
        elif args.command == 'batch':
            await cli.run_batch_command(args)
        elif args.command == 'demo':
            await cli.run_demo_command(args)
        elif args.command == 'test':
            await cli.run_test_command(args)
        elif args.command == 'benchmark':
            await cli.run_benchmark_command(args)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())