#!/usr/bin/env python
"""Test script to verify XPCS Power User Tools installation."""

import sys
import subprocess

def test_package_import():
    """Test if the package can be imported."""
    try:
        import xpcs_poweruser
        print("✓ Package import successful")
        print(f"  Version: {xpcs_poweruser.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Package import failed: {e}")
        return False

def test_cli_command():
    """Test if the CLI command is available."""
    try:
        result = subprocess.run(['xpcs-poweruser', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ CLI command available")
            print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ CLI command failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ CLI command not found in PATH")
        return False

def test_utils_import():
    """Test if utils modules can be imported."""
    try:
        from xpcs_poweruser.utils import (
            Read_Frames_8IDI_Rigaku,
            Muititau_Corr,
            Read_Qmap_8IDI,
            SAXS,
            Multitau_Group_g2,
            Write_HDF_Result
        )
        print("✓ Utils functions import successful")
        return True
    except ImportError as e:
        print(f"✗ Utils import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing XPCS Power User Tools installation...\n")
    
    tests = [
        test_package_import,
        test_cli_command,
        test_utils_import
    ]
    
    results = [test() for test in tests]
    
    print(f"\nTests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n✓ All tests passed! The package is installed correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
