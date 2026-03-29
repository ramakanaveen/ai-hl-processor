import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.models import ImpactAnalysisResult
import hashlib


class FileSystemMemory:
    """
    File-based memory store for headline analyses and patterns
    Stores:
    - Individual headline analyses (memory_store/analyses/)
    - Historical impact patterns (memory_store/patterns/)
    - Performance metrics (memory_store/metrics/)
    """

    def __init__(self, base_path: str = "memory_store"):
        self.base_path = Path(base_path)
        self.analyses_path = self.base_path / "analyses"
        self.patterns_path = self.base_path / "patterns"
        self.metrics_path = self.base_path / "metrics"

        # Create directories
        for path in [self.analyses_path, self.patterns_path, self.metrics_path]:
            path.mkdir(parents=True, exist_ok=True)

    def store_analysis(self, result: ImpactAnalysisResult) -> str:
        """
        Store headline analysis result

        Returns:
            File path where analysis was stored
        """
        # Generate unique ID from headline + timestamp
        analysis_id = hashlib.md5(
            f"{result.headline}{result.timestamp}".encode()
        ).hexdigest()[:12]

        # Create filename with timestamp
        timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp_str}_{analysis_id}.json"
        filepath = self.analyses_path / filename

        # Store as JSON
        with open(filepath, 'w') as f:
            json.dump(result.dict(), f, indent=2, default=str)

        return str(filepath)

    def search_similar_headlines(
        self,
        headline: str,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> List[ImpactAnalysisResult]:
        """
        Search for similar past headlines using simple keyword matching
        In production, could use embeddings + vector search
        """
        results = []
        headline_words = set(headline.lower().split())

        # Scan analysis files
        for filepath in sorted(self.analyses_path.glob("*.json"), reverse=True):
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Simple similarity: Jaccard index of words
            stored_words = set(data['headline'].lower().split())
            intersection = headline_words & stored_words
            union = headline_words | stored_words
            similarity = len(intersection) / len(union) if union else 0

            if similarity >= similarity_threshold:
                results.append(ImpactAnalysisResult(**data))

            if len(results) >= limit:
                break

        return results

    def get_currency_impact_history(
        self,
        currency: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical impact patterns for a specific currency
        Returns list of {headline, confidence, reasoning, timestamp}
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        impacts = []

        for filepath in sorted(self.analyses_path.glob("*.json"), reverse=True):
            with open(filepath, 'r') as f:
                data = json.load(f)

            timestamp = datetime.fromisoformat(data['timestamp'])
            if timestamp < cutoff_date:
                continue

            # Check if currency was impacted
            for entity in data.get('impacted_entities', []):
                if entity['currency'] == currency:
                    impacts.append({
                        'headline': data['headline'],
                        'confidence': entity['confidence'],
                        'reasoning': entity['reasoning'],
                        'timestamp': data['timestamp']
                    })
                    break

        return impacts

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        num_analyses = len(list(self.analyses_path.glob("*.json")))

        return {
            'total_analyses': num_analyses,
            'storage_path': str(self.base_path),
            'oldest_analysis': self._get_oldest_analysis_date(),
            'newest_analysis': self._get_newest_analysis_date()
        }

    def _get_oldest_analysis_date(self) -> Optional[str]:
        files = sorted(self.analyses_path.glob("*.json"))
        if files:
            with open(files[0], 'r') as f:
                return json.load(f)['timestamp']
        return None

    def _get_newest_analysis_date(self) -> Optional[str]:
        files = sorted(self.analyses_path.glob("*.json"), reverse=True)
        if files:
            with open(files[0], 'r') as f:
                return json.load(f)['timestamp']
        return None
