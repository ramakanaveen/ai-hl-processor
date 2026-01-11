## Overview
Modify the system to return a simplified output format that directly maps headlines to impacted entities (currencies) with confidence levels, rather than the current probability distribution approach.

## Motivation
The current output provides probability distributions across 4 cases (abstain, minor, moderate, major) for each entity. For Phase 1, we need a simpler, more direct output that focuses on:
- Which currencies will be impacted
- Confidence level for each impact
- Optional reasoning

## Proposed Output Format

### Example Input
```
"Rachel Reeves increased the tax"
```

### Example Output
```json
{
  "headline": "Rachel Reeves increased the tax",
  "impacted_entities": [
    {
      "currency": "GBP",
      "confidence": "high",
      "confidence_score": 0.85,
      "reasoning": "UK Chancellor fiscal policy directly impacts British pound"
    },
    {
      "currency": "EUR",
      "confidence": "low",
      "confidence_score": 0.35,
      "reasoning": "Indirect impact via UK-EU trade relationship"
    }
  ],
  "processing_time_ms": 450
}
```

## Key Changes Required

1. **Simplified Confidence Levels**
   - Replace 4-case probability distribution with simple confidence levels: `high`, `medium`, `low`
   - Keep numeric confidence_score (0.0-1.0) for programmatic use
   - Thresholds: high (>0.7), medium (0.4-0.7), low (<0.4)

2. **Entity Filtering**
   - Only return entities with confidence > threshold (e.g., 0.3)
   - Sort by confidence_score descending

3. **Reasoning Field**
   - Add optional `reasoning` field explaining why entity is impacted
   - Can be extracted from existing LLM response

4. **Output Structure**
   - Remove: `entity_type`, `probabilities` breakdown, `feature_vector`, `semantic_event` details
   - Keep: `entity_id` (as `currency`), `confidence_score`, add `confidence` category
   - Simplify top-level structure

## Implementation Notes

**Files to modify:**
- `poc_implementation.py`: Update `ImpactAssessmentResult` and `NewsAnalysisResult` dataclasses
- `main.py`: Modify output formatters (`_print_summary_results`, `_print_json_results`)
- Add helper function to convert confidence_score to confidence level category

**Backward Compatibility:**
- Consider adding a `--format` flag to support both old and new output formats
- Or create a new command: `python main.py analyze-simple "headline"`

## Example Usage

```bash
# Simple entity-impact analysis
python main.py analyze "Rachel Reeves increased the tax" --format simple

# Output only high-confidence entities
python main.py analyze "Rachel Reeves increased the tax" --min-confidence 0.7
```

## Acceptance Criteria

- [ ] Output format matches the proposed JSON structure
- [ ] Confidence levels correctly categorized (high/medium/low)
- [ ] Only relevant entities (confidence > threshold) are returned
- [ ] Reasoning field populated from LLM response
- [ ] Existing functionality remains intact (if using flag approach)
- [ ] CLI commands work with new output format
- [ ] Batch processing supports new format

## Related Files

- `poc_implementation.py` (lines 29-52: ImpactAssessmentResult, lines 43-52: NewsAnalysisResult)
- `main.py` (lines 370-439: output formatters)
- `semantic_impact_engine.py` (lines 61-69: ImpactProbabilities)
