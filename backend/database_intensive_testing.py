"""
Intensive Database Testing Framework for Qwen3 Coder
Test what the model actually knows and can generate effectively
"""

import json
import time
from datetime import datetime
import os

class DatabaseTestFramework:
    """
    Comprehensive testing framework to evaluate database options for AI coder
    """
    
    def __init__(self):
        self.test_results = {}
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.results_file = f"database_test_results_{self.timestamp}.json"
        
    def create_test_prompts(self):
        """Create comprehensive test prompts for different database technologies"""
        
        database_technologies = {
            "sqlite": {
                "description": "File-based SQL database",
                "setup_complexity": "minimal",
                "expected_knowledge": "high"
            },
            "postgresql": {
                "description": "Advanced SQL database",  
                "setup_complexity": "medium",
                "expected_knowledge": "high"
            },
            "mongodb": {
                "description": "NoSQL document database",
                "setup_complexity": "medium", 
                "expected_knowledge": "medium"
            },
            "redis": {
                "description": "In-memory key-value store",
                "setup_complexity": "low",
                "expected_knowledge": "medium"
            },
            "mysql": {
                "description": "Popular SQL database",
                "setup_complexity": "medium",
                "expected_knowledge": "high" 
            }
        }
        
        test_scenarios = {
            "basic_crud": "Create a simple CRUD API for a User model",
            "relationships": "Create models with foreign key relationships",
            "complex_queries": "Implement complex queries with joins and filtering",
            "migrations": "Handle database schema migrations",
            "async_operations": "Implement async database operations",
            "error_handling": "Add proper error handling for database operations",
            "performance": "Optimize database queries for performance",
            "testing": "Create unit tests for database operations"
        }
        
        return database_technologies, test_scenarios
    
    def generate_test_cases(self):
        """Generate specific test cases for each database + scenario combination"""
        
        technologies, scenarios = self.create_test_prompts()
        test_cases = []
        
        for db_name, db_info in technologies.items():
            for scenario_name, scenario_desc in scenarios.items():
                test_case = {
                    "id": f"{db_name}_{scenario_name}",
                    "database": db_name,
                    "scenario": scenario_name,
                    "prompt": self._create_detailed_prompt(db_name, db_info, scenario_name, scenario_desc),
                    "evaluation_criteria": self._get_evaluation_criteria(scenario_name),
                    "expected_files": self._get_expected_files(db_name, scenario_name)
                }
                test_cases.append(test_case)
        
        return test_cases
    
    def _create_detailed_prompt(self, db_name, db_info, scenario_name, scenario_desc):
        """Create detailed prompt for specific database + scenario"""
        
        base_prompt = f"""
You are a senior Python developer. Create a FastAPI backend application using {db_name.upper()} database.

Task: {scenario_desc}

Requirements:
1. Create a complete, working backend API
2. Use proper project structure
3. Include all necessary imports and dependencies
4. Add environment variable configuration
5. Include error handling
6. Make it production-ready

Database: {db_name} ({db_info['description']})
Setup Complexity: {db_info['setup_complexity']}

Please provide:
1. Complete file structure
2. All code files with full implementation
3. requirements.txt with exact versions
4. Environment configuration (.env example)
5. Basic usage instructions

Focus on:
- Clean, readable code
- Proper error handling
- Best practices for {db_name}
- Minimal setup complexity
- Good documentation

Generate complete, working code that I can run immediately.
"""
        
        # Add specific requirements per scenario
        if scenario_name == "basic_crud":
            base_prompt += """
Specific Requirements:
- User model with: id, email, username, created_at, is_active
- CRUD endpoints: GET /users, POST /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}
- Input validation using Pydantic
- Response models for API
"""
        elif scenario_name == "relationships":
            base_prompt += """
Specific Requirements:
- User model (id, email, username)
- Post model (id, title, content, user_id, created_at) 
- One-to-many relationship (User -> Posts)
- Endpoints to create users, posts, and get user with all posts
- Proper foreign key constraints
"""
        elif scenario_name == "complex_queries":
            base_prompt += """
Specific Requirements:
- User, Post, Comment models with relationships
- Search endpoint: GET /posts/search?q=term&author_id=1&date_from=2024-01-01
- Pagination support
- Sorting options
- Complex filtering with multiple conditions
"""
        
        return base_prompt.strip()
    
    def _get_evaluation_criteria(self, scenario_name):
        """Define evaluation criteria for each scenario"""
        criteria = {
            "basic_crud": [
                "Complete CRUD operations",
                "Proper HTTP status codes", 
                "Input validation",
                "Error handling",
                "Database connection setup",
                "Code organization"
            ],
            "relationships": [
                "Proper foreign keys",
                "Relationship definitions",
                "Cascade operations",
                "Join queries",
                "Data integrity"
            ],
            "complex_queries": [
                "Query optimization",
                "Filtering logic",
                "Pagination implementation",
                "Performance considerations",
                "SQL query quality"
            ],
            "migrations": [
                "Migration scripts",
                "Schema versioning",
                "Rollback capability",
                "Data preservation"
            ],
            "async_operations": [
                "Async/await usage",
                "Connection pooling",
                "Concurrent safety",
                "Performance benefits"
            ]
        }
        
        return criteria.get(scenario_name, ["Code quality", "Functionality", "Best practices"])
    
    def _get_expected_files(self, db_name, scenario_name):
        """Define expected files for each test case"""
        base_files = [
            "main.py",
            "requirements.txt", 
            ".env.example"
        ]
        
        if db_name in ["sqlite", "postgresql", "mysql"]:
            base_files.extend([
                "models.py",
                "database.py", 
                "crud.py",
                "schemas.py"
            ])
        elif db_name == "mongodb":
            base_files.extend([
                "models.py",
                "database.py",
                "services.py"
            ])
        elif db_name == "redis":
            base_files.extend([
                "database.py",
                "services.py"
            ])
        
        return base_files

class QwenTestingProtocol:
    """
    Protocol for testing Qwen3 Coder's database capabilities
    """
    
    def __init__(self):
        self.framework = DatabaseTestFramework()
        
    def run_knowledge_assessment(self):
        """Test basic database knowledge across technologies"""
        
        knowledge_tests = {
            "technology_familiarity": """
Rate your familiarity and confidence (1-10) with each database technology for Python backend development:

1. SQLite - File-based SQL database
2. PostgreSQL - Advanced SQL database  
3. MySQL - Popular SQL database
4. MongoDB - NoSQL document database
5. Redis - In-memory key-value store

For each, also indicate:
- Your confidence in generating working code (1-10)
- Common libraries you know (SQLAlchemy, PyMongo, etc.)  
- Typical use cases you've seen
- Setup complexity you're aware of

Be honest about your actual training data and capabilities.
""",
            
            "code_generation_confidence": """
For Python FastAPI backends, rank these tasks by your confidence in generating correct, working code:

1. Basic CRUD with SQLite + SQLAlchemy
2. Basic CRUD with PostgreSQL + SQLAlchemy  
3. Basic CRUD with MongoDB + PyMongo
4. Complex queries with joins (SQL databases)
5. Database migrations and schema changes
6. Async database operations
7. Error handling and validation
8. Performance optimization
9. Database testing
10. Production deployment setup

Rate each 1-10 and explain what makes some easier/harder for you.
""",
            
            "practical_experience": """
Based on your training data, which database setups have you seen the most examples of?

Consider:
- Tutorial frequency in your training
- Documentation quality you've seen
- Common patterns and best practices
- Error scenarios and troubleshooting
- Real-world vs toy examples

This will help us understand what you can generate most reliably.
"""
        }
        
        return knowledge_tests
    
    def create_practical_tests(self):
        """Create practical coding tests"""
        
        practical_tests = [
            {
                "name": "sqlite_basic_test",
                "description": "Simple SQLite CRUD with FastAPI",
                "prompt": """
Create a working FastAPI app with SQLite database for a simple todo application.

Requirements:
- Todo model: id, title, description, completed, created_at
- CRUD endpoints for todos
- SQLAlchemy ORM
- Pydantic schemas
- Environment configuration
- Working example you can run with 'python main.py'

Provide complete code that works immediately without modifications.
""",
                "success_criteria": [
                    "Code runs without errors",
                    "All CRUD operations work",
                    "Database file is created",
                    "API responses are correct",
                    "Proper error handling"
                ]
            },
            
            {
                "name": "postgresql_relationship_test", 
                "description": "PostgreSQL with relationships",
                "prompt": """
Create a FastAPI app with PostgreSQL for a blog system.

Requirements:
- User model (id, email, username)
- Post model (id, title, content, user_id, created_at)
- One-to-many relationship
- Endpoints: users CRUD, posts CRUD, get user with posts
- SQLAlchemy with relationships
- Proper foreign keys and constraints
- Connection string from environment

Provide complete working code.
""",
                "success_criteria": [
                    "Relationships work correctly",
                    "Foreign key constraints enforced", 
                    "Join queries execute properly",
                    "Data integrity maintained",
                    "Environment configuration correct"
                ]
            },
            
            {
                "name": "mongodb_document_test",
                "description": "MongoDB with PyMongo",
                "prompt": """
Create a FastAPI app with MongoDB for a product catalog.

Requirements:  
- Product model with flexible schema
- Category embedding within products
- Text search capabilities
- CRUD operations
- PyMongo or Motor for async
- Connection from environment

Provide complete working code.
""",
                "success_criteria": [
                    "MongoDB connection works",
                    "Document operations correct",
                    "Flexible schema handled",
                    "Search functionality works",
                    "Async operations if used"
                ]
            }
        ]
        
        return practical_tests
    
    def create_complexity_tests(self):
        """Test handling of increasing complexity"""
        
        complexity_tests = [
            {
                "level": "beginner",
                "description": "Simple single-table CRUD",
                "expected_success_rate": "90%+"
            },
            {
                "level": "intermediate", 
                "description": "Multi-table with relationships",
                "expected_success_rate": "70%+"
            },
            {
                "level": "advanced",
                "description": "Complex queries, optimization, migrations",
                "expected_success_rate": "50%+"
            },
            {
                "level": "expert",
                "description": "Production setup, monitoring, scaling",
                "expected_success_rate": "30%+"
            }
        ]
        
        return complexity_tests
    
    def save_test_plan(self):
        """Save comprehensive test plan to file"""
        
        test_plan = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "purpose": "Evaluate Qwen3 Coder database capabilities",
                "focus_areas": [
                    "Technology knowledge assessment",
                    "Code generation quality",
                    "Practical implementation ability", 
                    "Complexity handling",
                    "Cost-effectiveness analysis"
                ]
            },
            "phase_1_knowledge_assessment": self.run_knowledge_assessment(),
            "phase_2_practical_tests": self.create_practical_tests(),
            "phase_3_complexity_tests": self.create_complexity_tests(),
            "phase_4_evaluation_framework": self.framework.generate_test_cases()
        }
        
        filename = f"qwen3_database_test_plan_{self.framework.timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_plan, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Comprehensive test plan saved to: {filename}")
        print(f"📊 Total test cases: {len(test_plan['phase_4_evaluation_framework'])}")
        
        return filename, test_plan

def main():
    """Run the testing framework setup"""
    
    print("🧪 Setting up intensive database testing for Qwen3 Coder")
    print("=" * 60)
    
    protocol = QwenTestingProtocol()
    filename, test_plan = protocol.save_test_plan()
    
    print(f"\n📋 Test Plan Overview:")
    print(f"   Knowledge Assessment: {len(test_plan['phase_1_knowledge_assessment'])} areas")
    print(f"   Practical Tests: {len(test_plan['phase_2_practical_tests'])} scenarios") 
    print(f"   Complexity Tests: {len(test_plan['phase_3_complexity_tests'])} levels")
    print(f"   Detailed Evaluation: {len(test_plan['phase_4_evaluation_framework'])} test cases")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Run knowledge assessment with Qwen3")
    print(f"   2. Execute practical coding tests")
    print(f"   3. Evaluate code quality and functionality")
    print(f"   4. Analyze cost vs capability trade-offs") 
    print(f"   5. Make data-driven database choice")
    
    return filename

if __name__ == "__main__":
    main()