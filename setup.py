"""Setup script for XPCS Power User Tools."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README_PACKAGE.md").read_text()

setup(
    name="poweruser-xpcs",
    version="0.1.0",
    author="XPCS Team",
    author_email="xpcs@example.com",
    description="XPCS Power User Tools - A collection of utilities for XPCS data analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AZjk/poweruser",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "h5py>=3.0.0",
        "tqdm>=4.60.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
        ]
    },
    entry_points={
        "console_scripts": [
            "xpcs-poweruser=poweruser_xpcs.cli:main",
        ],
    },
    package_data={
        "poweruser_xpcs": [
            "utils/sample_metadata.hdf",
            "utils/G2_average/*.json",
            "utils/fast_G2_average/*.json",
        ],
    },
    include_package_data=True,
)
