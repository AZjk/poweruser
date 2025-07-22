#!/usr/bin/env python
"""Quick start demonstration of XPCS Power User Tools."""

import os
import sys
import subprocess

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)

def run_command(cmd, description):
    """Run a command and display the output."""
    print(f"\n{description}")
    print(f"Command: {cmd}")
    print("-" * 40)
    
    # For demonstration, we'll just show what the command would do
    # In real usage, remove the --help flag to run the actual command
    demo_cmd = cmd.split()
    if len(demo_cmd) > 1 and demo_cmd[1] != '--help':
        demo_cmd.insert(2, '--help')
    
    result = subprocess.run(demo_cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
    if result.stderr:
        print("Error:", result.stderr)

def main():
    """Run the quick start demonstration."""
    print_section("XPCS Power User Tools - Quick Start Demo")
    
    print("\nThis demo shows the available commands in the xpcs-poweruser CLI.")
    print("Note: Commands are shown with --help flag for demonstration.")
    print("Remove --help to run the actual commands with your data.\n")
    
    # Check if package is installed
    try:
        subprocess.run(['xpcs-poweruser', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: xpcs-poweruser is not installed!")
        print("Please install the package first:")
        print("  pip install -e .")
        return 1
    
    # Show main help
    run_command(
        "xpcs-poweruser --help",
        "1. View all available commands:"
    )
    
    # Show list-utils command
    run_command(
        "xpcs-poweruser list-utils",
        "2. List all available utilities:"
    )
    
    # Show convert-legacy help
    run_command(
        "xpcs-poweruser convert-legacy --help",
        "3. Convert legacy datasets to NeXus format:"
    )
    
    # Show nexus-to-csv help
    run_command(
        "xpcs-poweruser nexus-to-csv --help",
        "4. Convert HDF5/NeXus files to CSV:"
    )
    
    # Show g2-average help
    run_command(
        "xpcs-poweruser g2-average --help",
        "5. Run G2 averaging analysis:"
    )
    
    # Show run-script help
    run_command(
        "xpcs-poweruser run-script --help",
        "6. Run any Python script from utils:"
    )
    
    print_section("Example Commands (for real usage)")
    
    print("""
# Convert legacy datasets with 4 workers:
xpcs-poweruser convert-legacy /data/legacy /data/nexus --workers 4

# Convert HDF5 to CSV with filter:
xpcs-poweruser nexus-to-csv -i /data/hdf5 -o /data/csv --filter "sample_A"

# Run G2 averaging:
xpcs-poweruser g2-average /data/sample.hdf -o /results/

# Run a custom script:
xpcs-poweruser run-script /path/to/script.py arg1 arg2
""")
    
    print_section("Next Steps")
    
    print("""
1. Install the package if not already done:
   pip install -e .

2. Try the commands with your own data files

3. Use Python API for programmatic access:
   from poweruser_xpcs.utils import Read_Frames_8IDI_Rigaku, Muititau_Corr

4. Check the README_PACKAGE.md for detailed documentation
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
