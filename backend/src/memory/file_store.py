import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.models import ImpactAnalysisResult, CurrencyImpact
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
        self.corrections_path = self.base_path / "corrections"

        # Create directories
        for path in [self.analyses_path, self.patterns_path, self.metrics_path, self.corrections_path]:
            path.mkdir(parents=True, exist_ok=True)

    def store_analysis(self, result: ImpactAnalysisResult) -> str:
        """
        Store headline analysis result

        Returns:
            File path where analysis was stored
        """
        if result.last_modified_at is None:
            result.last_modified_at = result.timestamp

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
            json.dump(result.model_dump(), f, indent=2, default=str)

        return str(filepath)

    @staticmethod
    def _normalize_headline(headline: str) -> str:
        return headline.lower().strip()

    def _analysis_matches_headline(self, data: Dict[str, Any], headline: str) -> bool:
        return self._normalize_headline(data.get('headline', '')) == self._normalize_headline(headline)

    def apply_correction(
        self,
        headline: str,
        corrected_entities: list,
        note: str = "",
        corrected_by: str = "user",
    ) -> List[ImpactAnalysisResult]:
        """
        Rewrite all matching analyses so the corrected result becomes canonical.
        Returns the updated analyses, newest first.
        """
        now = datetime.now(timezone.utc)
        updated_results = []

        for filepath in sorted(self.analyses_path.glob("*.json"), reverse=True):
            with open(filepath, 'r') as f:
                data = json.load(f)

            if not self._analysis_matches_headline(data, headline):
                continue

            data['impacted_entities'] = [
                CurrencyImpact(**entity).model_dump() for entity in corrected_entities
            ]
            data['is_corrected'] = True
            data['corrected_by'] = corrected_by
            data['correction_note'] = note
            data['last_modified_at'] = now.isoformat()
            data['error'] = None

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            updated_results.append(ImpactAnalysisResult(**data))

        return updated_results

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

    # ------------------------------------------------------------------
    # User corrections  (permanent audit trail)
    # ------------------------------------------------------------------

    def store_correction(
        self,
        headline: str,
        original_entities: list,
        corrected_entities: list,
        note: str = "",
        corrected_by: str = "user",
    ) -> str:
        """Persist a user correction. Returns the file path written."""
        h = hashlib.sha256(headline.lower().strip().encode()).hexdigest()[:12]
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts_str}_{h}.json"
        filepath = self.corrections_path / filename

        payload = {
            "headline": headline,
            "original_entities": original_entities,
            "corrected_entities": corrected_entities,
            "correction_note": note,
            "corrected_by": corrected_by,
            "corrected_at": datetime.now().isoformat(),
        }
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, default=str)
        return str(filepath)

    def get_correction_by_hash(self, headline_hash: str) -> Optional[Dict[str, Any]]:
        """Find the most recent correction file whose name starts with the given hash prefix."""
        matches = sorted(
            [fp for fp in self.corrections_path.glob("*.json")
             if headline_hash in fp.stem],
            reverse=True
        )
        if not matches:
            return None
        with open(matches[0], 'r') as f:
            return json.load(f)
