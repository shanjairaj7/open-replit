# Integration Prompt Enhancement Plan

## Overview
Enhance simpler_prompt.py to enable the LLM to build AI-powered and integration-rich applications by understanding user intent and naturally including integrations when they deliver core value.

## Implementation Strategy

### 1. Add Third-Party Integration Section
**Location**: After "Tools" section, before "Development Methodology"
**Content**: 
- Brief introduction to available integrations (OpenAI, Exa.ai, Stripe, etc.)
- Emphasis on using docs for detailed implementation guides
- Key management and configuration patterns

### 2. Add Integration-Powered Example
**Location**: After existing examples, before "Battle tested common mistakes"
**Content**: Example showing AI document management app where:
- User describes functionality without explicitly mentioning OpenAI
- LLM recognizes need for AI integration as core value
- Selects document upload + AI search as 2 core features
- Shows docs usage for OpenAI integration implementation

### 3. Enhance Documentation Usage Rules
**Location**: Update existing docs rule in technical implementation section
**Enhancement**: Strengthen guidance about reading docs for integration patterns

### 4. Maintain Feature Selection Methodology
**Key principle**: Keep existing "2 core features" rule intact
- Don't change prioritization of simple CRUD over complex features
- Show how integrations can be one of the 2 core features when they ARE the core value
- Demonstrate natural decision-making through examples, not explicit rules

## Specific Changes

### New Section: Third-Party Integration Capabilities
```
## Third-Party Integration Capabilities

You can build applications with powerful third-party integrations:
- **AI/LLM Integration**: OpenAI, Claude, embeddings, vector search, chat completions
- **Web Search**: Real-time information retrieval and research capabilities  
- **Payment Processing**: Complete e-commerce and subscription functionality
- **And more**: Email, SMS, file storage, analytics, and other services

The `docs` folder contains detailed implementation guides for each integration, including:
- Step-by-step integration patterns
- API key configuration and management
- Code examples and best practices
- Error handling and edge cases

Always check docs before implementing integrations to understand the established patterns.
```

### New Example: AI-Powered App Development
**User Request**: "Build me a smart research assistant where I can ask questions about any topic and get comprehensive answers"

**LLM Response**: Shows understanding that this needs web search + AI analysis as core features, selects Exa.ai + OpenAI integration naturally.

### Enhanced Rules
Update existing docs rule to emphasize integration guidance:
- "Read documentation in docs folder for integration patterns before implementation"
- "Integration docs contain API keys, configuration, and implementation details"

## Implementation Tasks:
- [x] Create implementation plan
- [ ] Add Third-Party Integration Capabilities section
- [ ] Add AI-powered research assistant example
- [ ] Enhance documentation usage rules
- [ ] Test prompt with integration scenarios

## Success Criteria:
- LLM can identify when integrations are core to user value
- Natural inclusion of integrations in initial version when appropriate
- Maintains existing feature selection methodology
- Uses docs system for integration implementation guidance
- Delivers working integration-powered apps in initial version

This creates the meta-capability: our coding LLM can now build AI-powered applications while maintaining the proven development methodology.