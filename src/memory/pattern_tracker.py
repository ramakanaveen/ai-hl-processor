from collections import defaultdict
from typing import Dict, List, Tuple
from src.memory.file_store import FileSystemMemory
import json


class PatternTracker:
    """
    Analyzes historical patterns in currency impacts
    Builds knowledge like: "UK tax news → 85% avg confidence on GBP"
    """

    def __init__(self, memory: FileSystemMemory):
        self.memory = memory

    def get_event_currency_patterns(self) -> Dict[str, Dict[str, float]]:
        """
        Analyze patterns: which event keywords correlate with which currencies
        Returns: {keyword: {currency: avg_confidence}}
        """
        patterns = defaultdict(lambda: defaultdict(list))

        for filepath in self.memory.analyses_path.glob("*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)

            headline_words = set(data['headline'].lower().split())

            for entity in data.get('impacted_entities', []):
                currency = entity['currency']
                confidence = entity['confidence']

                # Track keyword-currency correlations
                for word in headline_words:
                    if len(word) > 3:  # Skip short words
                        patterns[word][currency].append(confidence)

        # Average confidences
        result = {}
        for word, currencies in patterns.items():
            result[word] = {
                curr: sum(confs) / len(confs)
                for curr, confs in currencies.items()
            }

        return result

    def get_currency_avg_confidence(self, currency: str) -> float:
        """Get average confidence for a currency across all analyses"""
        confidences = []

        for filepath in self.memory.analyses_path.glob("*.json"):
            with open(filepath, 'r') as f:
                data = json.load(f)

            for entity in data.get('impacted_entities', []):
                if entity['currency'] == currency:
                    confidences.append(entity['confidence'])

        return sum(confidences) / len(confidences) if confidences else 0.0
