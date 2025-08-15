"""
Execute actual tests with Qwen3 Coder to evaluate database capabilities
This connects to your existing API to run real tests
"""

import requests
import json
import time
from datetime import datetime
import os

class QwenDatabaseTester:
    """
    Execute real tests with Qwen3 Coder via your API
    """
    
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        self.test_results = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def test_basic_database_knowledge(self):
        """Test 1: Basic database technology knowledge"""
        
        print("🧪 TEST 1: Database Technology Knowledge Assessment")
        print("=" * 50)
        
        knowledge_prompt = """
You are Qwen3 Coder, an AI specialized in code generation. Please honestly assess your capabilities:

**QUESTION 1: Database Technology Ranking**
Rank these databases from 1-5 based on your confidence in generating working Python code (1=highest confidence, 5=lowest):

A) SQLite + SQLAlchemy
B) PostgreSQL + SQLAlchemy  
C) MongoDB + PyMongo
D) MySQL + SQLAlchemy
E) Redis + redis-py

For each, briefly explain WHY you ranked it that way.

**QUESTION 2: Code Generation Confidence**
For a simple FastAPI CRUD application, rate your confidence (1-10) in generating complete, working code for:

A) SQLite setup and basic CRUD
B) PostgreSQL connection and relationships  
C) MongoDB document operations
D) Complex SQL queries with joins
E) Database migrations and schema updates

**QUESTION 3: Training Data Assessment**
Which database patterns have you seen MOST frequently in your training data? Be specific about:
- Tutorial examples
- Documentation patterns  
- Common libraries and imports
- Error handling approaches

**QUESTION 4: Practical Limitations**
What database-related tasks do you find most challenging to generate code for?
What often goes wrong in your generated database code?

Please be honest and specific - this helps us choose the right database for our AI coding system.
"""
        
        result = self._make_api_call("database_knowledge_test", knowledge_prompt)
        
        if result:
            print("✅ Knowledge assessment completed")
            self._save_test_result("knowledge_assessment", knowledge_prompt, result)
            return result
        else:
            print("❌ Knowledge assessment failed")
            return None
    
    def test_sqlite_code_generation(self):
        """Test 2: SQLite code generation quality"""
        
        print("\n🧪 TEST 2: SQLite Code Generation")
        print("=" * 50)
        
        sqlite_prompt = """
Create a complete, working FastAPI application with SQLite database.

Requirements:
- Todo management system
- Models: User, Todo (with foreign key to User)
- User: id, email, username, created_at
- Todo: id, title, description, completed, user_id, created_at  
- Complete CRUD endpoints for both models
- SQLAlchemy ORM with proper relationships
- Pydantic schemas for request/response
- Environment configuration (.env support)
- Error handling for common database errors
- Basic input validation

Provide:
1. Complete file structure 
2. All Python files with full code
3. requirements.txt
4. .env.example
5. Instructions to run

Make it production-ready and immediately runnable.
"""
        
        result = self._make_api_call("sqlite_test", sqlite_prompt)
        
        if result:
            print("✅ SQLite code generation completed")
            self._save_test_result("sqlite_generation", sqlite_prompt, result)
            return result
        else:
            print("❌ SQLite code generation failed")
            return None
    
    def test_postgresql_code_generation(self):
        """Test 3: PostgreSQL code generation quality"""
        
        print("\n🧪 TEST 3: PostgreSQL Code Generation")
        print("=" * 50)
        
        postgres_prompt = """
Create a complete FastAPI application with PostgreSQL database.

Requirements:
- Blog management system
- Models: User, Category, Post, Comment
- Relationships: User->Posts (1:many), Post->Comments (1:many), Post->Category (many:1)
- Complex endpoints:
  - GET /posts?category=tech&author_id=1&limit=10 (filtering + pagination)
  - GET /users/{id}/posts (user with all posts)
  - GET /posts/{id}/comments (post with all comments)
- PostgreSQL-specific features (JSON fields, full-text search)
- Database connection pooling
- Migration setup (Alembic)
- Async database operations
- Comprehensive error handling

Provide complete, production-ready code that works with PostgreSQL.
"""
        
        result = self._make_api_call("postgresql_test", postgres_prompt)
        
        if result:
            print("✅ PostgreSQL code generation completed")
            self._save_test_result("postgresql_generation", postgres_prompt, result)
            return result
        else:
            print("❌ PostgreSQL code generation failed")
            return None
    
    def test_mongodb_code_generation(self):
        """Test 4: MongoDB code generation quality"""
        
        print("\n🧪 TEST 4: MongoDB Code Generation")
        print("=" * 50)
        
        mongodb_prompt = """
Create a complete FastAPI application with MongoDB database.

Requirements:
- E-commerce product catalog
- Documents: Product, Category, Review, User
- Flexible schemas (products can have different attributes)
- Embedded documents (reviews within products)
- Text search capabilities
- Aggregation pipelines for analytics
- PyMongo or Motor for async operations
- Proper indexing strategy
- Connection pooling
- Error handling for MongoDB-specific errors

Features needed:
- Product search with text and filters
- Category-based product browsing  
- User reviews and ratings
- Analytics endpoints (top products, category stats)

Provide complete MongoDB implementation.
"""
        
        result = self._make_api_call("mongodb_test", mongodb_prompt)
        
        if result:
            print("✅ MongoDB code generation completed") 
            self._save_test_result("mongodb_generation", mongodb_prompt, result)
            return result
        else:
            print("❌ MongoDB code generation failed")
            return None
    
    def test_complexity_handling(self):
        """Test 5: Complex database scenarios"""
        
        print("\n🧪 TEST 5: Complex Database Scenarios")
        print("=" * 50)
        
        complexity_prompt = """
Create a sophisticated database solution for a multi-tenant SaaS application.

Requirements:
- Multi-tenancy (data isolation per tenant)
- Complex relationships (Users, Organizations, Projects, Tasks, Comments)
- Advanced features:
  - Database migrations with rollback capability
  - Connection pooling and optimization
  - Caching layer (Redis integration)
  - Background tasks with database operations
  - Database monitoring and health checks
  - Soft deletes and audit trails
  - Full-text search across multiple tables
  - Data export/import functionality

Choose the BEST database technology for this use case and justify your choice.
Provide complete implementation with all advanced features.

Focus on:
1. Scalability for multiple tenants
2. Performance optimization
3. Data security and isolation  
4. Monitoring and maintenance
5. Cost-effectiveness

This tests your ability to handle enterprise-level database requirements.
"""
        
        result = self._make_api_call("complexity_test", complexity_prompt)
        
        if result:
            print("✅ Complexity handling test completed")
            self._save_test_result("complexity_handling", complexity_prompt, result)
            return result
        else:
            print("❌ Complexity handling test failed")
            return None
    
    def _make_api_call(self, test_name, prompt):
        """Make API call to your existing coder system"""
        
        print(f"🔄 Executing {test_name} via API...")
        
        try:
            # This would call your existing API endpoint
            # Adjust URL and payload based on your actual API structure
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "project_id": f"db_test_{test_name}_{self.timestamp}",
                "max_iterations": 5
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/coder",
                json=payload,
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def _save_test_result(self, test_type, prompt, result):
        """Save individual test result"""
        
        test_data = {
            "test_type": test_type,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "result": result,
            "metadata": {
                "api_url": self.api_base_url,
                "test_session": self.timestamp
            }
        }
        
        self.test_results.append(test_data)
        
        # Save individual result file
        filename = f"qwen_test_{test_type}_{self.timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Test result saved: {filename}")
    
    def run_complete_evaluation(self):
        """Run all tests and generate comprehensive evaluation"""
        
        print("🚀 Starting Comprehensive Qwen3 Database Evaluation")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_basic_database_knowledge,
            self.test_sqlite_code_generation, 
            self.test_postgresql_code_generation,
            self.test_mongodb_code_generation,
            self.test_complexity_handling
        ]
        
        results_summary = {}
        
        for test_func in tests:
            try:
                result = test_func()
                test_name = test_func.__name__
                results_summary[test_name] = {
                    "status": "completed" if result else "failed",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Wait between tests to avoid overwhelming the API
                time.sleep(5)
                
            except Exception as e:
                test_name = test_func.__name__
                results_summary[test_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                print(f"❌ Test {test_name} failed with error: {e}")
        
        # Generate final evaluation report
        self._generate_evaluation_report(results_summary)
        
        return results_summary
    
    def _generate_evaluation_report(self, results_summary):
        """Generate comprehensive evaluation report"""
        
        report = {
            "evaluation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(results_summary),
                "successful_tests": len([r for r in results_summary.values() if r["status"] == "completed"]),
                "failed_tests": len([r for r in results_summary.values() if r["status"] != "completed"]),
                "test_session_id": self.timestamp
            },
            "test_results": results_summary,
            "detailed_results": self.test_results,
            "analysis_framework": {
                "evaluation_criteria": [
                    "Code completeness and correctness",
                    "Best practices adherence", 
                    "Error handling quality",
                    "Database-specific optimizations",
                    "Production readiness",
                    "Setup complexity",
                    "Documentation quality"
                ],
                "decision_factors": [
                    "Model knowledge confidence",
                    "Code generation reliability",
                    "Infrastructure cost",
                    "Scalability requirements",
                    "Maintenance complexity"
                ]
            },
            "next_steps": [
                "Analyze code quality for each database type",
                "Test generated code for functionality",
                "Evaluate setup and deployment complexity", 
                "Calculate total cost of ownership",
                "Make final database technology decision"
            ]
        }
        
        report_filename = f"qwen3_database_evaluation_report_{self.timestamp}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 EVALUATION COMPLETED")
        print(f"📄 Full report saved: {report_filename}")
        print(f"✅ Successful tests: {report['evaluation_summary']['successful_tests']}")
        print(f"❌ Failed tests: {report['evaluation_summary']['failed_tests']}")
        
        return report_filename

def main():
    """Run the complete testing suite"""
    
    print("🔬 Qwen3 Coder Database Capability Testing")
    print("=" * 50)
    print("This will run intensive tests to determine the best database choice")
    print("for your AI coding system based on actual model performance.\n")
    
    # Initialize tester (adjust API URL as needed)
    api_url = input("Enter your API base URL (default: http://localhost:8000): ").strip()
    if not api_url:
        api_url = "http://localhost:8000"
    
    tester = QwenDatabaseTester(api_url)
    
    print(f"🔗 Using API: {api_url}")
    print(f"⏱️  Test session: {tester.timestamp}")
    print("\nStarting evaluation...\n")
    
    # Run complete evaluation
    results = tester.run_complete_evaluation()
    
    print("\n🎯 EVALUATION COMPLETE!")
    print("Review the generated reports to make your database technology decision.")
    
    return results

if __name__ == "__main__":
    main()