"""
Quick Database Test for Immediate Feedback
Run this to get immediate insights from Qwen3 about database preferences
"""

# Test message to send to Qwen3 Coder directly
QWEN_DATABASE_TEST_PROMPT = """
You are Qwen3 Coder. I'm building an AI coding system where you generate complete backend applications with databases. I need to choose the best database technology based on YOUR actual capabilities and knowledge.

Please honestly assess yourself:

**1. Database Technology Confidence (Rate 1-10 for generating working code)**
- SQLite + SQLAlchemy: ?/10
- PostgreSQL + SQLAlchemy: ?/10  
- MongoDB + PyMongo: ?/10
- MySQL + SQLAlchemy: ?/10
- Redis + redis-py: ?/10

**2. What you know BEST**
Which database have you seen the most examples of in your training?
Which one can you generate the most reliable, complete code for?

**3. Quick Code Test - SQLite**
Generate a simple FastAPI + SQLite example right now:
- User model (id, email, username)
- CRUD endpoints  
- Complete working code
- Just show me database.py and models.py files

**4. Quick Code Test - PostgreSQL**
Same thing but with PostgreSQL:
- Show connection setup
- Migration handling
- Environment configuration

**5. Honest Assessment**
- What database tasks do you struggle with?
- What often breaks in your generated database code?
- Which setup is simplest for you to generate correctly?

**6. For a multi-project system where each project needs its own database:**
- SQLite file per project vs
- PostgreSQL schema per project vs  
- MongoDB database per project

Which approach would you generate the most reliable code for?

Be very honest - this determines our entire database architecture!
"""

def print_test_prompt():
    """Print the test prompt for manual testing"""
    print("🧪 QWEN3 DATABASE KNOWLEDGE TEST")
    print("=" * 50)
    print("Copy this prompt and send it to Qwen3 Coder:")
    print()
    print(QWEN_DATABASE_TEST_PROMPT)
    print()
    print("=" * 50)
    print("📋 Analysis Framework:")
    print("Look for:")
    print("- Confidence ratings (higher = better choice)")
    print("- Code generation quality and completeness")  
    print("- Specific limitations and challenges mentioned")
    print("- Setup complexity preferences")
    print("- Multi-project architecture recommendations")
    
def create_evaluation_rubric():
    """Create evaluation rubric for analyzing Qwen3's response"""
    
    rubric = {
        "confidence_scores": {
            "description": "Numerical confidence ratings for each database",
            "weight": 30,
            "criteria": [
                "SQLite confidence (target: 8+)",
                "PostgreSQL confidence (target: 7+)",
                "MongoDB confidence (target: 6+)",
                "Overall confidence distribution"
            ]
        },
        "code_quality": {
            "description": "Quality of generated code examples",
            "weight": 25,
            "criteria": [
                "Code completeness",
                "Correct imports and syntax",
                "Proper error handling",
                "Best practices followed",
                "Production readiness"
            ]
        },
        "honesty_assessment": {
            "description": "How honest about limitations",
            "weight": 20,
            "criteria": [
                "Acknowledges weaknesses",
                "Identifies common problems",
                "Realistic about capabilities",
                "Specific about training data"
            ]
        },
        "practical_recommendations": {
            "description": "Usefulness of multi-project advice",
            "weight": 15,
            "criteria": [
                "Clear preference stated",
                "Reasoning provided",
                "Scalability considerations",
                "Cost-effectiveness awareness"
            ]
        },
        "technical_depth": {
            "description": "Understanding of database concepts",
            "weight": 10,
            "criteria": [
                "Connection management",
                "Schema design",
                "Performance considerations",
                "Migration strategies"
            ]
        }
    }
    
    return rubric

def save_test_template():
    """Save a template for recording results"""
    
    template = {
        "test_metadata": {
            "date": "YYYY-MM-DD",
            "tester": "your_name",
            "qwen_model": "qwen3-coder",
            "purpose": "Database technology selection"
        },
        "qwen_responses": {
            "confidence_scores": {
                "sqlite": "?/10",
                "postgresql": "?/10", 
                "mongodb": "?/10",
                "mysql": "?/10",
                "redis": "?/10"
            },
            "best_knowledge": "Which database mentioned as strongest?",
            "sqlite_code_quality": "Rate the generated SQLite code 1-10",
            "postgresql_code_quality": "Rate the generated PostgreSQL code 1-10",
            "honest_limitations": "What limitations did Qwen3 admit?",
            "multi_project_recommendation": "Which approach recommended?"
        },
        "evaluation_scores": {
            "confidence_scores": "?/30",
            "code_quality": "?/25", 
            "honesty_assessment": "?/20",
            "practical_recommendations": "?/15",
            "technical_depth": "?/10",
            "total_score": "?/100"
        },
        "decision_factors": {
            "primary_strength": "",
            "main_weakness": "", 
            "recommended_choice": "",
            "reasoning": ""
        },
        "next_steps": [
            "Test actual code generation",
            "Evaluate setup complexity",
            "Cost analysis",
            "Final architecture decision"
        ]
    }
    
    import json
    with open("qwen3_database_test_template.json", 'w') as f:
        json.dump(template, f, indent=2)
    
    print("📄 Test template saved: qwen3_database_test_template.json")
    return template

if __name__ == "__main__":
    print("🚀 Quick Database Test Setup")
    print("This creates a focused test to get immediate insights from Qwen3")
    print()
    
    # Print the test prompt
    print_test_prompt()
    
    # Create evaluation framework
    rubric = create_evaluation_rubric()
    print(f"📊 Evaluation rubric created with {len(rubric)} criteria")
    
    # Save test template  
    template = save_test_template()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Copy the prompt above and test it with Qwen3 Coder")
    print("2. Record responses in the JSON template") 
    print("3. Evaluate using the rubric")
    print("4. Run more detailed tests based on results")
    print("5. Make informed database architecture decision")
    
    print(f"\n💡 Focus on finding:")
    print("- Which database Qwen3 is most confident with")
    print("- Quality of generated code examples")
    print("- Honest assessment of limitations")
    print("- Practical multi-project recommendations")