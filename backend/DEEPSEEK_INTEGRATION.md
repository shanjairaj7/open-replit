# DeepSeek R1 Azure Integration

## Overview
Successfully integrated DeepSeek R1 model alongside GPT-4.1 in the API server with environment-based model selection.

## Configuration Details

### DeepSeek R1 Deployment
- **Model Name**: `DeepSeek-R1-0528`
- **Endpoint**: `https://rajsu-m9qoo96e-eastus2.services.ai.azure.com`
- **API Version**: `2024-05-01-preview`
- **API Key**: Same as GPT-4.1 (shared Azure subscription)

### GPT-4.1 Deployment (Updated)
- **Model Name**: `gpt-4.1`
- **Endpoint**: `https://rajsu-m9qoo96e-eastus2.services.ai.azure.com`
- **API Version**: `2024-12-01-preview`
- **API Key**: Same shared key

## Usage

### Environment Variable Control
Use the `MODEL_TYPE` environment variable to switch between models:

```bash
# Use GPT-4.1 (default)
export MODEL_TYPE=gpt
# OR simply don't set it

# Use DeepSeek R1
export MODEL_TYPE=deepseek
```

### Testing
```bash
# Test DeepSeek specifically
python test_deepseek_azure.py

# Test both model switching
python test_both_models.py
```

## Key Implementation Features

### 1. **Automatic Model Selection**
- Default: GPT-4.1
- Environment override: `MODEL_TYPE=deepseek` for DeepSeek R1

### 2. **Unified Client Interface**
- Same `azure_client` object works for both models
- Same API patterns and response handling

### 3. **Model-Specific Configuration**
- Different API versions for each model
- Proper endpoint configuration for each deployment

## Files Modified

### `base_test_azure_hybrid.py`
- Added dual model configuration
- Environment-based model selection logic
- Unified client initialization

### Test Files Created
- `test_deepseek_azure.py` - DeepSeek-specific testing
- `test_both_models.py` - Model switching validation

## API Response Differences

### GPT-4.1
- Standard OpenAI-style responses
- Clean, direct answers

### DeepSeek R1
- Includes `<think>` reasoning blocks in responses
- More verbose with internal reasoning shown
- Higher token usage due to thinking process

## Usage Examples

```python
# The client automatically uses the selected model
response = azure_client.chat.completions.create(
    model=model_name,  # Will be "gpt-4.1" or "DeepSeek-R1-0528"
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    max_tokens=2048
)
```

## Production Considerations

1. **Token Usage**: DeepSeek R1 uses more tokens due to reasoning
2. **Response Format**: DeepSeek includes thinking process in output
3. **Model Selection**: Set environment variable before starting API server
4. **Error Handling**: Both models use same error handling patterns

## Success Indicators
✅ Both models tested and working  
✅ Environment-based switching functional  
✅ Shared authentication working  
✅ Unified API interface maintained