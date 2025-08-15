# Classification Pipeline API Testing Guide

## Overview
Test the new classification pipeline with mode parameter support and approval workflow.

## Prerequisites
1. Start the backend server: `cd backend && python -m app.main`
2. Ensure database is set up with sample transactions

## Test Endpoints

### 1. Classification with Different Modes

#### Auto Mode (Default Pipeline)
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": true
  }'
```

#### Rule-Based Only
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=rule" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": true
  }'
```

#### Embedding-Based Only
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=embed" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": true
  }'
```

#### ML-Based Only
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=ml" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": true
  }'
```

#### LLM-Based Only
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=llm" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": true
  }'
```

### 2. Approval Workflow

#### Approve Classification
```bash
curl -X POST "http://localhost:8000/classify/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": 1,
    "approved_by": "test_user",
    "create_rule": false,
    "update_vendor_mapping": true,
    "notes": "Looks correct"
  }'
```

#### Approve and Create Rule
```bash
curl -X POST "http://localhost:8000/classify/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": 2,
    "approved_by": "test_user", 
    "create_rule": true,
    "update_vendor_mapping": true,
    "notes": "Create rule for future similar transactions"
  }'
```

### 3. Legacy Endpoint (Backward Compatibility)
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3],
    "force_reclassify": false
  }'
```

### 4. Get Classification Rules
```bash
curl -X GET "http://localhost:8000/classify/rules?limit=20&active_only=true"
```

### 5. Get Accuracy Metrics
```bash
curl -X GET "http://localhost:8000/classify/accuracy"
```

## Expected Response Format

### Classification Response
```json
[
  {
    "transaction_id": 1,
    "predicted_coa_id": 123,
    "predicted_coa_name": "Office Expenses",
    "confidence_score": 0.92,
    "classification_method": "vendor_mapping",
    "source": "vendor_mapping",
    "rule_id": null,
    "similarity_score": null,
    "reason": null
  }
]
```

### Approval Response
```json
{
  "success": true,
  "message": "Classification approved",
  "rule_created": false,
  "vendor_mapping_updated": true
}
```

## Testing Different Source Types

### Rule-Based Sources
- `vendor_mapping`: Direct vendor match
- `regex_rule`: Pattern-based rule match

### Embedding Sources
- `embedding`: Vector similarity match

### AI Sources  
- `llm`: LLM-generated classification

### Hybrid Sources
- `hybrid`: Combination of methods
- `fallback`: Default when no method succeeds

## Performance Testing

### Test Pipeline Timing
```bash
time curl -X POST "http://localhost:8000/classify/predict?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3, 4, 5],
    "force_reclassify": true
  }'
```

### Test Individual Mode Performance
```bash
# Rule mode (should be fastest)
time curl -X POST "http://localhost:8000/classify/predict?mode=rule" \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": [1, 2, 3, 4, 5], "force_reclassify": true}'

# LLM mode (should be slowest)  
time curl -X POST "http://localhost:8000/classify/predict?mode=llm" \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": [1, 2, 3, 4, 5], "force_reclassify": true}'
```

## Error Testing

### Invalid Mode
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=invalid" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1],
    "force_reclassify": true
  }'
```

### Non-existent Transaction
```bash
curl -X POST "http://localhost:8000/classify/predict?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [999999],
    "force_reclassify": true
  }'
```

### Invalid Approval
```bash
curl -X POST "http://localhost:8000/classify/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": 999999,
    "approved_by": "test_user"
  }'
```

## Frontend Testing

### Test Frontend Integration
1. Open browser to frontend URL
2. Navigate to Classification page
3. Look for source tags on transactions:
   - Green badge: `VENDOR MAPPING`
   - Purple badge: `REGEX RULE` 
   - Orange badge: `EMBEDDING`
   - Red badge: `LLM`
   - Gray badge: `FALLBACK`
4. Test "Approve" and "Approve + Create Rule" buttons
5. Verify approval calls `/classify/approve` endpoint

## Confidence Score Validation

### High Confidence (>= 0.9)
- Should come from rule-based classification
- Vendor mappings and strong regex matches

### Medium Confidence (0.7 - 0.89)  
- Embedding similarities
- ML predictions

### Low Confidence (< 0.7)
- LLM fallback scenarios
- Ambiguous transactions

## Cache Testing

### Test LLM Cache
```bash
# First call (should be slow)
time curl -X POST "http://localhost:8000/classify/predict?mode=llm" \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": [1], "force_reclassify": true}'

# Second call (should be fast - cached)
time curl -X POST "http://localhost:8000/classify/predict?mode=llm" \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": [1], "force_reclassify": true}'
```

## Debugging Tips

1. **Check logs**: Monitor backend logs for classification pipeline execution
2. **Verify database**: Ensure transactions exist and have proper data
3. **Test incrementally**: Start with rule mode, then progress through pipeline
4. **Monitor confidence**: Low confidence may indicate missing rules or poor data
5. **Check vendor mappings**: Verify vendor names match expected patterns

## Expected Behavior

1. **Auto mode** should try methods in order until confidence threshold met
2. **Individual modes** should only use that specific method  
3. **Approval** should update transaction and optionally create rules
4. **Source tags** should indicate which method was used
5. **Caching** should speed up repeated LLM calls
6. **Error handling** should gracefully handle failures and return appropriate responses