#!/usr/bin/env python
"""
Entry point script for running Evolution Process
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 确保环境变量加载
load_dotenv()

# 打印环境变量用于调试
print("Environment variables:")
print(f"SQLALCHEMY_DATABASE_URI = {os.environ.get('SQLALCHEMY_DATABASE_URI')}")
print(f"DATABASE_URL = {os.environ.get('DATABASE_URL')}")

# Import the database session
try:
    from agir_db.db.session import get_db, SessionLocal
    # Get a database session for CustomFieldAdapter
    db = next(get_db())
except Exception as e:
    print(f"Failed to get database session: {str(e)}")
    db = None

from src.cli import main

if __name__ == "__main__":
    sys.exit(main()) 