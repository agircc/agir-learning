from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agir-learning",
    version="0.1.0",
    author="AGIR",
    author_email="info@agir.ai",
    description="A system for evolving LLM-powered agents through simulated experiences",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agircc/agir-learning",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "agir-db @ git+https://github.com/agircc/agir-db.git",
        "python-dotenv>=1.0.0",
        "openai>=1.12.0",
        "anthropic>=0.15.0",
        "PyYAML>=6.0.1",
        "langchain>=0.1.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "agir-learning=agir_learning.cli:main",
        ],
    },
) 