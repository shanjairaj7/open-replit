"""
Database Knowledge Test for Qwen3 Coder
Ask the model directly about its database expertise
"""

# Test query for the AI model to answer
DATABASE_KNOWLEDGE_QUERY = """
You are Qwen3 Coder. Please analyze your own capabilities and answer these questions:

1. **Database Technologies you know BEST (rank top 5):**
   - Which databases can you write code for most confidently?
   - Which ones have you seen the most training examples for?

2. **Python Database Integration:**
   - Which Python database libraries do you know best? (SQLAlchemy, SQLite3, PyMongo, etc.)
   - Which ones require the least boilerplate code?

3. **Quick Setup Databases:**
   - Which databases can be set up with minimal configuration?
   - Which ones work well for both small and large projects?

4. **Code Generation Confidence:**
   - For which databases can you generate CRUD operations most reliably?
   - Which ones have the simplest query syntax you can work with?

5. **Schema Management:**
   - Which databases make it easiest to create/modify schemas programmatically?
   - Which ones handle migrations well?

Please be specific about your actual capabilities, not just general popularity.
"""

def test_database_knowledge():
    print("=" * 60)
    print("DATABASE KNOWLEDGE TEST FOR QWEN3 CODER")
    print("=" * 60)
    print(DATABASE_KNOWLEDGE_QUERY)
    print("=" * 60)
    print("This query should be sent to Qwen3 Coder to understand its database preferences")

if __name__ == "__main__":
    test_database_knowledge()