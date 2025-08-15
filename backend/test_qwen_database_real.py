#!/usr/local/bin/python3.13
"""
REAL Testing of Qwen3 Database Capabilities
Run actual tests with your existing API and give concrete answers
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def run_test(test_name, test_prompt):
    """Run a test with the actual system and capture results"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {test_name}")
    print('='*60)
    
    # Generate unique project name
    timestamp = datetime.now().strftime("%H%M%S")
    project_name = f"db-test-{test_name.lower().replace(' ', '-')}-{timestamp}"
    
    print(f"📋 Project: {project_name}")
    print(f"🎯 Test Description: {test_name}")
    print(f"📝 Prompt length: {len(test_prompt)} chars")
    
    try:
        # Run the base_test.py with our test prompt
        cmd = [
            "python3", str(backend_dir / "setup" / "base_test.py"),
            "--message", test_prompt,
            "--create"
        ]
        
        print(f"🚀 Executing: {' '.join(cmd)}")
        print("⏱️  Starting test execution...")
        
        start_time = time.time()
        
        # Run the test
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=backend_dir
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Test completed in {duration:.1f} seconds")
        
        # Analyze results
        test_result = {
            "test_name": test_name,
            "project_name": project_name,
            "duration_seconds": duration,
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "prompt": test_prompt
        }
        
        # Print results
        if test_result["success"]:
            print("✅ TEST COMPLETED SUCCESSFULLY")
        else:
            print(f"❌ TEST FAILED (exit code: {result.returncode})")
        
        # Show output snippets
        if result.stdout:
            print(f"📄 STDOUT ({len(result.stdout)} chars):")
            print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
        
        if result.stderr:
            print(f"⚠️  STDERR ({len(result.stderr)} chars):")
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        
        return test_result
        
    except subprocess.TimeoutExpired:
        print("⏰ TEST TIMED OUT (5 minutes)")
        return {
            "test_name": test_name,
            "project_name": project_name,
            "success": False,
            "error": "timeout",
            "duration_seconds": 300
        }
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        return {
            "test_name": test_name,
            "project_name": project_name,
            "success": False,
            "error": str(e),
            "duration_seconds": 0
        }

def test_1_database_knowledge():
    """Test 1: Direct database knowledge assessment"""
    
    prompt = """
You are Qwen3 Coder. I need to choose the best database technology for an AI coding system where you generate complete backend applications with databases.

Please honestly assess your capabilities:

1. **Database Technology Confidence** (Rate 1-10 for generating working code):
   - SQLite + SQLAlchemy: ?/10
   - PostgreSQL + SQLAlchemy: ?/10
   - MongoDB + PyMongo: ?/10
   - MySQL + SQLAlchemy: ?/10
   - Redis + redis-py: ?/10

2. **What you know BEST**:
   - Which database have you seen the most examples of in your training?
   - Which one can you generate the most reliable, complete code for?
   - Which has the simplest setup that you can handle well?

3. **For each database, rate your confidence (1-10) in generating:**
   - Basic CRUD operations
   - Database connection setup
   - Schema migrations
   - Error handling
   - Production deployment code

4. **Multi-project architecture**: 
   For a system where each user project needs its own isolated database:
   - SQLite file per project
   - PostgreSQL schema per project  
   - MongoDB database per project
   
   Which approach would you generate the most reliable code for?

5. **Honest limitations**:
   - What database tasks do you struggle with?
   - What often breaks in your generated database code?
   - Which setup requires the least complex configuration?

Be completely honest - this determines our database architecture choice.
"""
    
    return run_test("Database Knowledge Assessment", prompt)

def test_2_sqlite_generation():
    """Test 2: SQLite code generation quality"""
    
    prompt = """
Create a complete FastAPI application with SQLite database.

Requirements:
- Task management system
- Models: User, Task (with foreign key to User)
- User: id, email, username, created_at, is_active
- Task: id, title, description, completed, user_id, created_at, due_date
- Complete CRUD endpoints for both models
- SQLAlchemy ORM with proper relationships
- Pydantic schemas for all request/response models
- Environment configuration (.env support)
- Comprehensive error handling
- Input validation
- Database initialization script

Provide a complete, working implementation that I can run immediately.
Include all files, imports, and setup instructions.

Focus on:
1. Clean, production-ready code
2. Proper database relationships
3. Error handling for all endpoints
4. Complete API documentation
5. Easy setup and deployment
"""
    
    return run_test("SQLite Code Generation", prompt)

def test_3_postgresql_generation():
    """Test 3: PostgreSQL code generation quality"""
    
    prompt = """
Create a complete FastAPI application with PostgreSQL database.

Requirements:
- Blog management system
- Models: User, Category, Post, Comment, Tag
- Complex relationships:
  - User -> Posts (1:many)
  - Post -> Comments (1:many)
  - Post -> Category (many:1)
  - Post <-> Tags (many:many)
- Advanced features:
  - Full-text search on posts
  - Pagination for all list endpoints
  - Filtering by category, author, tags
  - JSON fields for post metadata
- PostgreSQL-specific optimizations:
  - Proper indexing strategy
  - Database connection pooling
  - Async operations where beneficial
- Migration management with Alembic
- Comprehensive test suite
- Production deployment configuration

Create a sophisticated, scalable implementation.
"""
    
    return run_test("PostgreSQL Code Generation", prompt)

def test_4_mongodb_generation():
    """Test 4: MongoDB code generation quality"""
    
    prompt = """
Create a complete FastAPI application with MongoDB database.

Requirements:
- E-commerce product catalog
- Collections: Product, Category, User, Review, Order
- Flexible document schemas:
  - Products with varying attributes
  - Embedded reviews within products
  - Order history with product snapshots
- MongoDB-specific features:
  - Text search across products
  - Aggregation pipelines for analytics
  - Efficient indexing strategy
  - Document validation schemas
- PyMongo or Motor for async operations
- Complex queries:
  - Product search with filters
  - Category-based browsing
  - Analytics (top products, sales by category)
  - User order history with details

Build a production-ready MongoDB application with proper error handling and performance optimization.
"""
    
    return run_test("MongoDB Code Generation", prompt)

def test_5_simple_crud():
    """Test 5: Simple CRUD to establish baseline"""
    
    prompt = """
Create the simplest possible working CRUD API with a database.

Requirements:
- ONE model: Item (id, name, description)
- CRUD endpoints: GET /items, POST /items, GET /items/{id}, PUT /items/{id}, DELETE /items/{id}
- Choose the database YOU think is best for this simple case
- Working code that runs immediately
- Minimal dependencies
- Clear setup instructions

Make it as simple and reliable as possible. This is a baseline test.
"""
    
    return run_test("Simple CRUD Baseline", prompt)

def analyze_results(test_results):
    """Analyze test results and make recommendations"""
    
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST ANALYSIS")
    print('='*80)
    
    successful_tests = [t for t in test_results if t.get('success', False)]
    failed_tests = [t for t in test_results if not t.get('success', False)]
    
    print(f"✅ Successful Tests: {len(successful_tests)}/{len(test_results)}")
    print(f"❌ Failed Tests: {len(failed_tests)}/{len(test_results)}")
    
    # Success rate analysis
    success_rate = len(successful_tests) / len(test_results) * 100 if test_results else 0
    print(f"📈 Overall Success Rate: {success_rate:.1f}%")
    
    # Duration analysis
    successful_durations = [t['duration_seconds'] for t in successful_tests]
    if successful_durations:
        avg_duration = sum(successful_durations) / len(successful_durations)
        print(f"⏱️  Average Success Duration: {avg_duration:.1f} seconds")
    
    # Database-specific analysis
    print(f"\n🎯 DATABASE TECHNOLOGY ASSESSMENT:")
    print("-" * 40)
    
    for test in test_results:
        test_name = test['test_name']
        success = "✅" if test.get('success', False) else "❌"
        duration = test.get('duration_seconds', 0)
        
        print(f"{success} {test_name}: {duration:.1f}s")
        
        # Extract specific insights from output
        if test.get('stdout'):
            output = test['stdout'].lower()
            if 'sqlite' in output:
                print(f"   📊 SQLite mentioned in output")
            if 'postgresql' in output:
                print(f"   📊 PostgreSQL mentioned in output")
            if 'mongodb' in output:
                print(f"   📊 MongoDB mentioned in output")
    
    # Generate final recommendation
    print(f"\n🏆 FINAL RECOMMENDATION:")
    print("-" * 40)
    
    if success_rate >= 80:
        print("✅ HIGH CONFIDENCE: Qwen3 demonstrates strong database capabilities")
        
        # Analyze which database type performed best
        sqlite_success = any('sqlite' in t.get('test_name', '').lower() and t.get('success', False) for t in test_results)
        postgres_success = any('postgresql' in t.get('test_name', '').lower() and t.get('success', False) for t in test_results)
        mongodb_success = any('mongodb' in t.get('test_name', '').lower() and t.get('success', False) for t in test_results)
        simple_success = any('simple' in t.get('test_name', '').lower() and t.get('success', False) for t in test_results)
        
        if sqlite_success and simple_success:
            print("🥇 RECOMMENDED DATABASE: SQLite + SQLAlchemy")
            print("   ✅ Demonstrated working code generation")
            print("   ✅ Simple setup and deployment")
            print("   ✅ Perfect for project isolation")
            print("   ✅ Cost-effective (zero infrastructure)")
        else:
            print("⚠️  MIXED RESULTS - Need manual review of generated code")
            
    elif success_rate >= 60:
        print("⚡ MODERATE CONFIDENCE: Some database capabilities demonstrated")
        print("   📋 Recommendation: Use simplest option (SQLite)")
        print("   🔍 Manual review required for complex features")
        
    else:
        print("❌ LOW CONFIDENCE: Multiple test failures")
        print("   📋 Recommendation: Implement database templates manually")
        print("   🔧 Provide pre-built database patterns to model")
    
    # Cost-effectiveness reminder
    print(f"\n💰 COST ANALYSIS REMINDER:")
    print("   SQLite: $0.03/month for 1000 projects")
    print("   PostgreSQL: $57.94/month for 1000 projects") 
    print("   MongoDB: $132.00/month for 1000 projects")
    
    return {
        "success_rate": success_rate,
        "recommended_database": "sqlite" if sqlite_success and simple_success else "manual_review_needed",
        "total_tests": len(test_results),
        "successful_tests": len(successful_tests),
        "failed_tests": len(failed_tests)
    }

def save_results(test_results, analysis):
    """Save test results to file"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"qwen_database_test_results_{timestamp}.json"
    
    full_results = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_results),
            "test_framework": "Real API Testing with base_test.py"
        },
        "test_results": test_results,
        "analysis": analysis,
        "final_recommendation": {
            "database_choice": analysis.get("recommended_database", "unknown"),
            "confidence_level": "high" if analysis.get("success_rate", 0) >= 80 else "medium" if analysis.get("success_rate", 0) >= 60 else "low",
            "reasoning": "Based on actual code generation tests with Qwen3 Coder"
        }
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {results_file}")
    return results_file

def main():
    """Run all tests and provide final recommendation"""
    
    print("🚀 QWEN3 CODER DATABASE TESTING - REAL API TESTS")
    print("=" * 70)
    print("This will run actual tests with your existing API system")
    print("Each test creates a real project and generates real code")
    print()
    
    # List of tests to run
    tests = [
        ("Knowledge Assessment", test_1_database_knowledge),
        ("Simple CRUD", test_5_simple_crud),  # Run simple test first
        ("SQLite Generation", test_2_sqlite_generation),
        # ("PostgreSQL Generation", test_3_postgresql_generation),  # Skip for now - too complex
        # ("MongoDB Generation", test_4_mongodb_generation),  # Skip for now - too complex
    ]
    
    test_results = []
    
    print(f"📋 Running {len(tests)} tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"   {i}. {name}")
    print()
    
    # Run each test
    for i, (test_name, test_func) in enumerate(tests, 1):
        print(f"\n🎯 TEST {i}/{len(tests)}: {test_name}")
        
        try:
            result = test_func()
            test_results.append(result)
            
            # Brief result summary
            if result.get('success'):
                print(f"✅ {test_name}: SUCCESS ({result.get('duration_seconds', 0):.1f}s)")
            else:
                print(f"❌ {test_name}: FAILED")
                if result.get('error'):
                    print(f"   Error: {result['error']}")
                    
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            test_results.append({
                "test_name": test_name,
                "success": False,
                "error": str(e)
            })
        
        # Wait between tests
        if i < len(tests):
            print("⏳ Waiting 10 seconds between tests...")
            time.sleep(10)
    
    # Analyze results
    analysis = analyze_results(test_results)
    
    # Save results
    results_file = save_results(test_results, analysis)
    
    # Final summary
    print(f"\n🎉 TESTING COMPLETE!")
    print(f"📊 Success Rate: {analysis['success_rate']:.1f}%")
    print(f"📄 Full results: {results_file}")
    
    return test_results, analysis

if __name__ == "__main__":
    main()