#!/usr/bin/env python
"""
Test runner for poweruser_xpcs utilities.

This script runs all unit tests in the tests directory.
"""

import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_all_tests():
    """Run all tests in the tests directory."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_module):
    """Run a specific test module."""
    loader = unittest.TestLoader()
    
    try:
        # Import the test module
        module = __import__(f'test_{test_module}', fromlist=[''])
        suite = loader.loadTestsFromModule(module)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return 0 if result.wasSuccessful() else 1
    except ImportError as e:
        print(f"Error: Could not import test module 'test_{test_module}': {e}")
        return 1

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) > 1:
        # Run specific test module
        test_module = sys.argv[1]
        print(f"\nRunning tests from test_{test_module}.py...\n")
        exit_code = run_specific_test(test_module)
    else:
        # Run all tests
        print("\nRunning all tests...\n")
        exit_code = run_all_tests()
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
