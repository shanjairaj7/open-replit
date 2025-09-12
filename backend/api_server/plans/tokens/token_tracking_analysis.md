# Token Tracking & Efficiency Analysis System

## Overview

This system tracks token usage and satisfaction ratings across chat stream sessions to measure and optimize system efficiency over time. The goal is to achieve **higher satisfaction with fewer tokens** - indicating improved system performance.

## How Token Tracking Works

### 1. Audit Logging (`utils/token_tracking.py`)
- **Session Boundaries**: Each chat stream session is tracked with `start` and `end` boundaries
- **Token Progression**: Token usage is logged throughout each session during coder iterations
- **JSON Storage**: All data is stored in `logs/token_usage_audit.json`

### 2. Audit Log Structure
```json
{
  "timestamp": "2025-09-03T13:50:05.751641",
  "project_id": "ecommerce-store-001", 
  "session_id": "ecommerce-store-001_session_000",
  "total_input_tokens": 269,
  "total_output_tokens": 628,
  "total_tokens": 897,
  "session_boundary": "start", // "start", "end", or null
  "generation_id": null,
  "done": false // true when session ends
}
```

### 3. Session Tracking Integration
- **Stream API Integration**: `streaming_api.py` automatically starts/ends sessions
- **Multi-Project Support**: Each project gets isolated tracking
- **Real-time Logging**: Token usage logged during coder iterations

## Analysis & Visualization

### Efficiency Calculation
**Efficiency Score = Average Tokens ÷ Average Satisfaction**

- **Lower score = BETTER** (fewer tokens per satisfaction point)
- **Higher score = WORSE** (more tokens per satisfaction point)

### Time Interval Logic
The system automatically chooses appropriate time intervals based on data span:

- **≤7 days**: Daily intervals
- **8-30 days**: 3-day intervals  
- **31-90 days**: Weekly intervals
- **90+ days**: Monthly intervals

### Bar Chart Features
- **X-axis**: Time periods (auto-selected intervals)
- **Y-axis**: Efficiency score (lower is better)
- **Bar Labels**: 
  - Main number: Efficiency score
  - In brackets: `(XXXt, X.Xs)` = Average tokens, Average satisfaction
- **Status Box**: Shows overall IMPROVED/DECLINED with percentage

## Goals & Optimization

### Primary Objective
**Achieve higher satisfaction ratings with fewer tokens over time**

### Success Indicators
- **Decreasing bar heights** = Improving efficiency
- **Green "IMPROVED" status** = Positive trend
- **Lower token usage** with same/higher satisfaction
- **Consistent optimization** across different time periods

### Use Cases
- **Performance Monitoring**: Track system efficiency trends
- **Optimization Validation**: Confirm improvements are working
- **Regression Detection**: Identify when efficiency declines
- **Resource Planning**: Understand token usage patterns

## How to Run

### Prerequisites
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Required packages already installed:
# - matplotlib, pandas, numpy
```

### Basic Usage
```bash
# Run analysis with default settings
python3 analyze_token_sessions.py

# Specify custom audit log path
python3 analyze_token_sessions.py --audit-log /path/to/audit.json

# Specify custom output chart path  
python3 analyze_token_sessions.py --chart efficiency_report.png
```

### Generate Test Data (for development)
```bash
# Create realistic multi-project test data
python3 test_multi_project_audit.py
```

## File Functions

### `analyze_token_sessions.py`
**Primary analysis script that:**

1. **Loads audit data** from JSON log file
2. **Extracts complete sessions** using start/end boundaries
3. **Groups sessions** into appropriate time intervals
4. **Calculates efficiency scores** for each interval
5. **Generates bar chart** with detailed labels
6. **Shows improvement status** with percentage change

### `test_multi_project_audit.py` 
**Test data generator that:**

1. **Creates realistic audit data** across multiple projects
2. **Simulates 22 sessions** over 4 days with varying token usage
3. **Includes proper session boundaries** for testing
4. **Generates diverse project scenarios** (e-commerce, blog, dashboard, etc.)

### `utils/token_tracking.py`
**Core tracking system that:**

1. **Manages session lifecycle** (start/end boundaries)
2. **Logs token usage** during coder iterations  
3. **Stores audit entries** in JSON format
4. **Integrates with OpenRouter** API for token counting
5. **Supports multi-project tracking** with project IDs

## Output Interpretation

### Sample Output
```
📊 Data span: 4 days, using Daily intervals
📈 09-03: 9 sessions, 2496 avg tokens, 5.0 avg satisfaction, efficiency: 499
📈 09-04: 5 sessions, 2822 avg tokens, 5.0 avg satisfaction, efficiency: 564  
📈 09-05: 3 sessions, 2608 avg tokens, 5.0 avg satisfaction, efficiency: 522
📈 09-06: 5 sessions, 2840 avg tokens, 5.0 avg satisfaction, efficiency: 568

Total Sessions Analyzed: 22
Average Tokens per Session: 2663.4
Average Satisfaction: 5.0/10
Overall Efficiency: 1.88 satisfaction per 1K tokens
```

### Key Metrics
- **Efficiency 499** = Most efficient day (best performance)
- **Efficiency 568** = Least efficient day (needs improvement)
- **Consistent satisfaction** at 5.0 shows stable quality
- **Varying token usage** (2496-2840) shows optimization opportunities

## Long-term Benefits

- **Performance Tracking**: Monitor efficiency trends over months/years
- **Optimization Validation**: Confirm code improvements reduce token usage
- **Cost Management**: Track token costs and optimize spending
- **Quality Assurance**: Ensure satisfaction doesn't decline with optimization
- **Data-Driven Decisions**: Use concrete metrics for system improvements