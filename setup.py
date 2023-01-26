#!/usr/bin/env python3
from setuptools import find_packages, setup
setup(
    name="benchmark",
    version="0.1",
    packages=find_packages(),
    python_requires=">=3.7",
    extras_require={"dev": ["flake8", "isort", "black"]},
)