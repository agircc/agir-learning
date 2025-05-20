# Installation Guide

This document provides detailed instructions for installing AGIR Learning and setting up the development environment.

## Prerequisites

Before installing AGIR Learning, ensure you have the following prerequisites:

- **Python 3.12+**: The system is built on Python 3.12 and may not work with older versions
- **Conda Package Manager**: Used for environment management and dependency installation
- **PostgreSQL Database**: Required for storing scenarios, users, and learning data
- **LLM API Keys**: For OpenAI, Anthropic, or other supported LLM providers

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/agir-learning.git
cd agir-learning
```

### 2. Set Up the Conda Environment

```bash
# Create the conda environment from the provided specification
conda env create -f environment.yml

# Activate the environment
conda activate agir-learning
```

If you need to update an existing environment:

```bash
# Update the environment with new dependencies
conda env update -f environment.yml --prune
conda activate agir-learning
```

### 3. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
cp .env.example .env
```

Edit the `.env` file to include your database URL and API keys:

```
DATABASE_URL=postgresql://username:password@localhost:5432/agir_learning
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 4. Set Up the Database

Ensure your PostgreSQL server is running, then create a database:

```bash
# Using psql command line
psql -U postgres -c "CREATE DATABASE agir_learning;"

# Run database migrations
make migrate
```

## Troubleshooting Installation Issues

### Environment Setup Issues

If you encounter issues with the Conda environment:

```bash
# If a package is missing
conda activate agir-learning
pip install missing_package_name

# To check if a package is installed
pip show package_name

# If you need to remove and recreate the environment
conda deactivate
conda remove -n agir-learning --all
conda env create -f environment.yml
```

### Database Connection Issues

If you have trouble connecting to the database:

1. Verify the PostgreSQL server is running
2. Check the `DATABASE_URL` in your `.env` file
3. Ensure the database exists
4. Verify that your user has the necessary permissions

```bash
# Test the database connection
psql -d your_database_name -U your_username
```

### API Key Issues

If LLM API calls fail:

1. Verify your API keys in the `.env` file
2. Check your account status with the LLM provider
3. Ensure you have sufficient credits or billing set up

## Manual Installation (Alternative)

If you prefer to install dependencies manually:

```bash
# Create a new conda environment
conda create -n agir-learning python=3.12
conda activate agir-learning

# Install FAISS from conda-forge (recommended way for this package)
conda install -c conda-forge faiss-cpu

# Install other Python dependencies
pip install agir-db @ git+https://github.com/agircc/agir-db.git
pip install python-dotenv==1.0.0
pip install openai>=1.78.1
pip install anthropic>=0.51.0
pip install PyYAML>=6.0.1
pip install langchain>=0.3.25 langchain-community>=0.3.24
pip install langchain-openai>=0.3.17 langchain-anthropic>=0.3.13
pip install fastapi>=0.104.1,<0.114.0 uvicorn==0.23.2
pip install pydantic>=2.7.4,<3.0.0 python-multipart==0.0.6
pip install requests>=2.30.0 email-validator==2.1.0.post1
pip install tk==0.1.0 langchain-ollama==0.3.3
pip install sentence-transformers>=2.2.2
```

## Verifying Installation

To verify that the installation was successful:

```bash
# Activate the environment
conda activate agir-learning

# Run a simple test scenario
make learning SCENARIO=scenarios/hello.yml

# Check if visualization works
make visualizer
```

If all the above commands work without errors, your installation is successful. 