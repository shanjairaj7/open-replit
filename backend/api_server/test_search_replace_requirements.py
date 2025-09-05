#!/usr/bin/env python3
"""
Comprehensive test script for update_file handler search/replace functionality
Tests various requirements.txt scenarios with single and multiple search/replace blocks
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from update_file_handler import UpdateFileHandler

class MockFileStorage:
    """Mock file storage for testing without Azure"""
    
    def __init__(self):
        self.files = {}
        self.read_calls = []
        self.update_calls = []
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Mock read file callback"""
        self.read_calls.append(file_path)
        return self.files.get(file_path)
    
    def update_file(self, file_path: str, content: str) -> dict:
        """Mock update file callback"""
        self.update_calls.append((file_path, content))
        self.files[file_path] = content
        return {"status": "updated", "path": file_path}
    
    def set_file_content(self, file_path: str, content: str):
        """Set initial file content for testing"""
        self.files[file_path] = content
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get current file content"""
        return self.files.get(file_path)

class RequirementsTestSuite:
    """Test suite for requirements.txt update scenarios"""
    
    def __init__(self):
        self.storage = MockFileStorage()
        self.handler = UpdateFileHandler(
            read_file_callback=self.storage.read_file,
            update_file_callback=self.storage.update_file
        )
        self.test_results = []
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "name": test_name,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    def create_basic_requirements(self) -> str:
        """Create a basic requirements.txt content"""
        return """# Basic requirements
flask==2.0.1
requests==2.25.1
numpy==1.21.0
pandas==1.3.0
django==3.2.5
pytest==6.2.4
"""

    def create_complex_requirements(self) -> str:
        """Create a complex requirements.txt with various formats"""
        return """# Production requirements
# Web framework
flask==2.0.1
django==3.2.5

# Data processing
numpy>=1.21.0,<1.22.0
pandas==1.3.0
scipy==1.7.0

# API and HTTP
requests==2.25.1
urllib3>=1.26.0

# Testing
pytest==6.2.4
pytest-cov==2.12.1

# Development tools
black==21.6.0
flake8==3.9.2

# Database
sqlalchemy==1.4.22
psycopg2-binary==2.9.1

# Optional dependencies
redis>=3.5.0  # For caching
celery[redis]==5.1.2  # Task queue

# Git dependencies
-e git+https://github.com/example/repo.git@v1.0#egg=example
"""

    def create_minimal_requirements(self) -> str:
        """Create minimal requirements.txt"""
        return """flask==2.0.1
requests==2.25.1
"""

    def run_test_case(self, test_name: str, initial_content: str, search_replace_content: str, 
                     expected_patterns: List[str] = None, should_fail: bool = False) -> bool:
        """Run a single test case"""
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING: {test_name}")
        print(f"{'='*60}")
        
        # Setup initial file content
        file_path = "requirements.txt"
        self.storage.set_file_content(file_path, initial_content)
        
        print(f"📝 Initial requirements.txt ({len(initial_content)} chars):")
        print("─" * 40)
        print(initial_content)
        print("─" * 40)
        
        print(f"🔄 Applying search/replace content:")
        print("─" * 40)
        print(search_replace_content)
        print("─" * 40)
        
        # Apply the update
        action = {
            "path": file_path,
            "content": search_replace_content
        }
        
        try:
            result = self.handler.handle_update_file(action)
            success = result.get("success", False)
            message = result.get("message", "")
            
            print(f"📊 Result: {'SUCCESS' if success else 'FAILED'}")
            if message:
                print(f"📄 Message: {message}")
            
            # Get final content
            final_content = self.storage.get_file_content(file_path)
            
            if final_content:
                print(f"📝 Final requirements.txt ({len(final_content)} chars):")
                print("─" * 40)
                print(final_content)
                print("─" * 40)
                
                # Check expected patterns if provided
                if expected_patterns and success:
                    patterns_found = []
                    for pattern in expected_patterns:
                        if pattern in final_content:
                            patterns_found.append(f"✅ Found: {pattern}")
                        else:
                            patterns_found.append(f"❌ Missing: {pattern}")
                    
                    print(f"🔍 Pattern verification:")
                    for result in patterns_found:
                        print(f"   {result}")
                    
                    all_patterns_found = all("✅" in result for result in patterns_found)
                    if not all_patterns_found:
                        success = False
                        message += " (Pattern verification failed)"
            
            # Check if test should fail
            if should_fail:
                success = not success  # Invert for tests that should fail
                test_result = success
                details = f"Expected failure: {'Got expected failure' if success else 'Unexpected success'}"
            else:
                test_result = success
                details = message
            
            self.log_test_result(test_name, test_result, details)
            return test_result
            
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"💥 {error_msg}")
            
            test_result = should_fail  # If we expect failure and got exception, that's success
            details = error_msg
            self.log_test_result(test_name, test_result, details)
            return test_result
    
    def test_single_version_update(self):
        """Test updating a single package version"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
flask==2.0.1
=======
flask==2.1.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Single Version Update",
            initial,
            search_replace,
            expected_patterns=["flask==2.1.0"]
        )
    
    def test_multiple_version_updates(self):
        """Test updating multiple package versions in one go"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
flask==2.0.1
=======
flask==2.1.0
+++++++ REPLACE

------- SEARCH
requests==2.25.1
=======
requests==2.26.0
+++++++ REPLACE

------- SEARCH
numpy==1.21.0
=======
numpy==1.22.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Multiple Version Updates",
            initial,
            search_replace,
            expected_patterns=["flask==2.1.0", "requests==2.26.0", "numpy==1.22.0"]
        )
    
    def test_add_new_package(self):
        """Test adding a new package"""
        initial = self.create_minimal_requirements()
        search_replace = """------- SEARCH
requests==2.25.1
=======
requests==2.25.1
scipy==1.7.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Add New Package",
            initial,
            search_replace,
            expected_patterns=["scipy==1.7.0"]
        )
    
    def test_remove_package(self):
        """Test removing a package"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
numpy==1.21.0
pandas==1.3.0
=======
pandas==1.3.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Remove Package",
            initial,
            search_replace
        )
    
    def test_complex_requirements_multiple_changes(self):
        """Test multiple changes in complex requirements.txt"""
        initial = self.create_complex_requirements()
        search_replace = """------- SEARCH
flask==2.0.1
=======
flask==2.1.1
+++++++ REPLACE

------- SEARCH
numpy>=1.21.0,<1.22.0
=======
numpy>=1.22.0,<1.23.0
+++++++ REPLACE

------- SEARCH
# Testing
pytest==6.2.4
pytest-cov==2.12.1
=======
# Testing
pytest==6.2.5
pytest-cov==2.12.2
coverage==5.5
+++++++ REPLACE

------- SEARCH
redis>=3.5.0  # For caching
=======
redis>=4.0.0  # For caching with new features
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Complex Requirements Multiple Changes",
            initial,
            search_replace,
            expected_patterns=[
                "flask==2.1.1",
                "numpy>=1.22.0,<1.23.0", 
                "pytest==6.2.5",
                "pytest-cov==2.12.2",
                "coverage==5.5",
                "redis>=4.0.0  # For caching with new features"
            ]
        )
    
    def test_whitespace_sensitivity(self):
        """Test whitespace-sensitive matching"""
        initial = """flask==2.0.1
requests==2.25.1

numpy==1.21.0
"""
        search_replace = """------- SEARCH
requests==2.25.1

numpy==1.21.0
=======
requests==2.26.0
scipy==1.7.0
numpy==1.22.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Whitespace Sensitivity",
            initial,
            search_replace,
            expected_patterns=["requests==2.26.0", "scipy==1.7.0", "numpy==1.22.0"]
        )
    
    def test_comment_preservation(self):
        """Test preserving comments during updates"""
        initial = """# Web framework
flask==2.0.1  # Core web framework
django==3.2.5

# Data processing
numpy==1.21.0  # Scientific computing
"""
        search_replace = """------- SEARCH
# Web framework
flask==2.0.1  # Core web framework
=======
# Web framework  
flask==2.1.0  # Updated core web framework
+++++++ REPLACE

------- SEARCH
numpy==1.21.0  # Scientific computing
=======
numpy==1.22.0  # Updated scientific computing
pandas==1.3.1  # Data analysis
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Comment Preservation",
            initial,
            search_replace,
            expected_patterns=[
                "flask==2.1.0  # Updated core web framework",
                "numpy==1.22.0  # Updated scientific computing",
                "pandas==1.3.1  # Data analysis"
            ]
        )
    
    def test_version_specifier_formats(self):
        """Test different version specifier formats"""
        initial = """flask>=2.0.0
requests~=2.25.0
numpy==1.21.*
pandas>=1.3.0,<1.4.0
scipy===1.7.0
"""
        search_replace = """------- SEARCH
flask>=2.0.0
=======
flask>=2.1.0
+++++++ REPLACE

------- SEARCH
requests~=2.25.0
=======
requests~=2.26.0
+++++++ REPLACE

------- SEARCH
scipy===1.7.0
=======
scipy===1.8.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Version Specifier Formats",
            initial,
            search_replace,
            expected_patterns=["flask>=2.1.0", "requests~=2.26.0", "scipy===1.8.0"]
        )
    
    def test_git_dependencies(self):
        """Test updating git dependencies"""
        initial = """-e git+https://github.com/user/repo.git@v1.0#egg=mypackage
-e git+https://github.com/user/other.git@main#egg=otherpackage
flask==2.0.1
"""
        search_replace = """------- SEARCH
-e git+https://github.com/user/repo.git@v1.0#egg=mypackage
=======
-e git+https://github.com/user/repo.git@v2.0#egg=mypackage
+++++++ REPLACE

------- SEARCH
flask==2.0.1
=======
flask==2.1.0
gunicorn==20.1.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Git Dependencies",
            initial,
            search_replace,
            expected_patterns=[
                "-e git+https://github.com/user/repo.git@v2.0#egg=mypackage",
                "flask==2.1.0",
                "gunicorn==20.1.0"
            ]
        )
    
    def test_failed_search_exact_match(self):
        """Test search pattern that doesn't match exactly (should fail)"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
flask==2.0.2
=======
flask==2.1.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Failed Search - Exact Match",
            initial,
            search_replace,
            should_fail=True
        )
    
    def test_failed_search_whitespace_mismatch(self):
        """Test search with whitespace mismatch (should fail)"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
flask==2.0.1 
=======
flask==2.1.0
+++++++ REPLACE"""  # Note extra space after flask==2.0.1
        
        return self.run_test_case(
            "Failed Search - Whitespace Mismatch",
            initial,
            search_replace,
            should_fail=True
        )
    
    def test_empty_requirements(self):
        """Test updating empty requirements.txt"""
        initial = ""
        search_replace = """------- SEARCH

=======
flask==2.1.0
requests==2.26.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Empty Requirements Update",
            initial,
            search_replace,
            expected_patterns=["flask==2.1.0", "requests==2.26.0"]
        )
    
    def test_mixed_format_updates(self):
        """Test multiple search/replace with different separators"""
        initial = self.create_basic_requirements()
        search_replace = """------- SEARCH
flask==2.0.1
=======
flask==2.1.0
+++++++ REPLACE

------- SEARCH
requests==2.25.1
======= 
requests==2.26.0
+++++++ REPLACE"""  # Note different number of = signs
        
        return self.run_test_case(
            "Mixed Format Updates",
            initial,
            search_replace,
            expected_patterns=["flask==2.1.0", "requests==2.26.0"]
        )

    def test_large_file_performance(self):
        """Test performance with large requirements file"""
        # Create a large requirements file
        large_requirements = []
        for i in range(100):
            large_requirements.extend([
                f"package{i:03d}=={i%10}.{i%5}.{i%3}",
                f"lib{i:03d}>={i%10}.0.0",
                f"tool{i:03d}~={i%10}.{i%5}.0"
            ])
        
        initial = "\n".join(large_requirements)
        
        # Update multiple packages
        search_replace = """------- SEARCH
package001==1.1.1
=======
package001==2.0.0
+++++++ REPLACE

------- SEARCH
package050==0.0.2
=======
package050==1.0.0
+++++++ REPLACE

------- SEARCH
lib075>=5.0.0
=======
lib075>=6.0.0
+++++++ REPLACE"""
        
        return self.run_test_case(
            "Large File Performance",
            initial,
            search_replace,
            expected_patterns=["package001==2.0.0", "package050==1.0.0", "lib075>=6.0.0"]
        )
    
    def run_all_tests(self):
        """Run all test cases"""
        print("🚀 Starting comprehensive search/replace tests for requirements.txt")
        print(f"📋 Using UpdateFileHandler with DiffParser backend")
        print(f"💾 Mock storage backend for testing")
        print("=" * 80)
        
        # Test cases to run
        test_methods = [
            self.test_single_version_update,
            self.test_multiple_version_updates,
            self.test_add_new_package,
            self.test_remove_package,
            self.test_complex_requirements_multiple_changes,
            self.test_whitespace_sensitivity,
            self.test_comment_preservation,
            self.test_version_specifier_formats,
            self.test_git_dependencies,
            self.test_failed_search_exact_match,
            self.test_failed_search_whitespace_mismatch,
            self.test_empty_requirements,
            self.test_mixed_format_updates,
            self.test_large_file_performance
        ]
        
        # Run each test
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test_result(f"{test_method.__name__}", False, f"Exception: {str(e)}")
        
        # Print summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📈 SUCCESS RATE: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print(f"\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['name']}: {result['details']}")
        
        print("\n🎯 COVERAGE AREAS TESTED:")
        print("   ✓ Single search/replace block")
        print("   ✓ Multiple search/replace blocks in one operation")
        print("   ✓ Version updates (==, >=, ~=, ===)")
        print("   ✓ Package addition and removal")
        print("   ✓ Comment preservation")
        print("   ✓ Whitespace handling")
        print("   ✓ Git dependencies")
        print("   ✓ Complex requirements.txt structures")
        print("   ✓ Error cases (failed matches)")
        print("   ✓ Performance with large files")
        
        print(f"\n📈 HANDLER PERFORMANCE:")
        print(f"   📖 Total file reads: {len(self.storage.read_calls)}")
        print(f"   💾 Total file updates: {len(self.storage.update_calls)}")

if __name__ == "__main__":
    print("🧪 Requirements.txt Search/Replace Test Suite")
    print("=" * 80)
    
    # Run the comprehensive test suite
    test_suite = RequirementsTestSuite()
    test_suite.run_all_tests()