#!/usr/bin/env python
"""
Test database connection
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 加载环境变量
load_dotenv()

# 打印环境变量
print("Environment variables:")
print(f"SQLALCHEMY_DATABASE_URI = {os.environ.get('SQLALCHEMY_DATABASE_URI')}")
print(f"DATABASE_URL = {os.environ.get('DATABASE_URL')}")

# 尝试连接数据库
uri = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/agir')
print(f"\nAttempting to connect using URI: {uri}")

try:
    engine = create_engine(uri)
    conn = engine.connect()
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {str(e)}")

# 尝试直接导入并使用 agir_db 中的连接配置
print("\nTrying to connect using agir_db configuration:")
try:
    from agir_db.db.session import engine, SQLALCHEMY_DATABASE_URI
    print(f"agir_db is using URI: {SQLALCHEMY_DATABASE_URI}")
    
    conn = engine.connect()
    print("Connection using agir_db engine successful!")
    conn.close()
except Exception as e:
    print(f"Connection using agir_db engine failed: {str(e)}") 