# Claude Code Guidelines

## Implementation Approach for Significant Features
1. **Read existing files** - Understand current implementation, dependencies, parent files/functions
2. **Create plan in plans/ folder** - Write detailed MD file with task tracking  
3. **Implement iteratively** - Step by step, following the plan properly

## Continuous Learning
- **Keep learning the codebase** - Understanding patterns, structure, dependencies
- **Remember user instructions** - How they prefer code style, organization, approaches  
- **Improve with each interaction** - Better understanding of this specific codebase and user preferences

## Tool Implementation Pattern (New)
- **Keep ALL existing tool handlers in base_test_azure_hybrid.py unchanged**
- **Only add NEW tools to tools.py** 
- **Establish pattern for future tools to use tools.py**

## Code Style Preferences
- Simple, functional code with prints for debugging
- Clear property names for LLM understanding
- Don't over-engineer or add too many comments
- Avoid too much structured/clean code - keep it practical