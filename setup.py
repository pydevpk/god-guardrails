import os
from pathlib import Path

from setuptools import setup, find_packages

setup(
    name="god-guardrails",
    version=os.environ.get("PACKAGE_VERSION", "0.1.0"),
    description="Policy-driven guardrails middleware for LLM requests (PII masking, prompt-injection detection)",
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    author="pydevpk",
    author_email="pydev.pk@gmail.com",
    license="Custom (see LICENSE)",
    license_files=("LICENSE",),
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0",
        "PyYAML>=6.0",
    ],
    python_requires=">=3.8",
)
