#!/usr/bin/env python
"""
深入检查 agir_db 的配置情况
"""

import os
import sys
import inspect
from dotenv import load_dotenv

# 确保环境变量加载
load_dotenv()

print("====== 环境变量 ======")
print(f"SQLALCHEMY_DATABASE_URI = {os.environ.get('SQLALCHEMY_DATABASE_URI')}")
print(f"DATABASE_URL = {os.environ.get('DATABASE_URL')}")

# 导入并检查 agir_db 的数据库配置
print("\n====== agir_db.db.session 检查 ======")
from agir_db.db.session import get_db, SessionLocal, engine, SQLALCHEMY_DATABASE_URI
print(f"agir_db 使用的数据库 URI: {SQLALCHEMY_DATABASE_URI}")
print(f"连接对象类型: {type(engine)}")

# 检查连接情况
print("\n====== 数据库连接测试 ======")
try:
    conn = engine.connect()
    print("连接成功!")
    print(f"数据库类型: {engine.dialect.name}")
    print(f"数据库驱动: {engine.dialect.driver}")
    print(f"数据库主机: {engine.url.host}")
    print(f"数据库用户: {engine.url.username}")
    print(f"数据库名称: {engine.url.database}")
    conn.close()
except Exception as e:
    print(f"连接失败: {str(e)}")

# 检查模型和表
print("\n====== 数据库表检查 ======")
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"数据库中的表: {', '.join(tables)}")
    
    # 检查 CustomFields 表结构
    if 'custom_fields' in tables:
        print("\n----- CustomFields 表结构 -----")
        columns = inspector.get_columns('custom_fields')
        for column in columns:
            print(f"列名: {column['name']}, 类型: {column['type']}, 可空: {column.get('nullable', True)}")
        
        print("\n----- CustomFields 表外键 -----")
        fks = inspector.get_foreign_keys('custom_fields')
        for fk in fks:
            print(f"约束名: {fk.get('name')}")
            print(f"引用表: {fk['referred_table']}")
            print(f"引用列: {fk['referred_columns']}")
            print(f"本地列: {fk['constrained_columns']}")
    else:
        print("数据库中不存在 CustomFields 表")
        
except Exception as e:
    print(f"检查表结构时出错: {str(e)}")

# 测试会话操作
print("\n====== 会话操作测试 ======")
try:
    # 获取数据库会话
    db = next(get_db())
    
    # 导入 User 模型
    from agir_db.models.user import User
    
    # 尝试查询用户
    user_count = db.query(User).count()
    print(f"用户表中的记录数: {user_count}")
    
    # 检查是否存在 CustomField 模型
    try:
        from agir_db.models.memory import UserMemory
        print("已找到 UserMemory 模型")
    except ImportError:
        print("未找到 UserMemory 模型")
    
    try:
        from agir_db.models.custom_fields import CustomField
        print("已找到 CustomField 模型")
    except ImportError:
        print("未找到 CustomField 模型")
    
    # 尝试从数据库查询 CustomFields 表
    if 'custom_fields' in inspector.get_table_names():
        try:
            # 使用原始 SQL 查询
            result = db.execute("SELECT COUNT(*) FROM custom_fields").scalar()
            print(f"custom_fields 表中的记录数: {result}")
        except Exception as e:
            print(f"查询 custom_fields 表时出错: {str(e)}")
    
    db.close()
except Exception as e:
    print(f"会话操作测试失败: {str(e)}")

print("\n====== 完成 ======") 