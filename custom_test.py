#!/usr/bin/env python
"""
测试 CustomFields 表的访问和使用
"""

import os
import sys
import inspect
from dotenv import load_dotenv
from sqlalchemy import text

# 确保环境变量加载
load_dotenv()

print("====== 环境变量 ======")
print(f"SQLALCHEMY_DATABASE_URI = {os.environ.get('SQLALCHEMY_DATABASE_URI')}")

# 导入数据库相关模块
from agir_db.db.session import get_db, SessionLocal, engine
from agir_db.models.user import User

print("\n====== 测试 CustomFields 表操作 ======")

with SessionLocal() as db:
    # 检查数据库中的表
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"数据库中的表: {', '.join(tables)}")
    
    # 检查是否存在 custom_fields 表
    if 'custom_fields' not in tables:
        print("错误: 数据库中不存在 custom_fields 表")
        sys.exit(1)
    
    # 使用 text SQL 查询 custom_fields 表
    print("\n----- 查询 custom_fields 表 -----")
    result = db.execute(text("SELECT COUNT(*) FROM custom_fields")).scalar()
    print(f"custom_fields 表中的记录数: {result}")
    
    # 检查已有的用户
    users = db.query(User).all()
    if not users:
        print("数据库中没有用户记录，创建测试用户")
        # 创建一个测试用户
        test_user = User(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_virtual=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"创建了测试用户: {test_user.username}, ID: {test_user.id}")
        user_id = test_user.id
    else:
        print(f"找到现有用户: {users[0].username}, ID: {users[0].id}")
        user_id = users[0].id
    
    # 尝试使用 utils.database 中的 CustomField 函数
    print("\n----- 使用 utils.database 中的 CustomField -----")
    
    try:
        # 导入 CustomField 类
        from src.utils.database import CustomField
        
        # 创建一个自定义字段记录
        test_field = CustomField(
            user_id=user_id,
            field_name="test_field",
            field_value="test_value"
        )
        
        # 保存到数据库
        db.add(test_field)
        db.commit()
        print(f"成功创建了自定义字段记录: {test_field}")
        
        # 查询刚刚创建的字段
        result = db.execute(
            text("SELECT * FROM custom_fields WHERE user_id = :user_id AND field_name = :field_name"),
            {"user_id": user_id, "field_name": "test_field"}
        ).fetchone()
        
        if result:
            print(f"成功查询到字段记录: {result}")
        else:
            print("未找到刚创建的字段记录")
    
    except Exception as e:
        print(f"使用 CustomField 时出错: {str(e)}")
        
        # 尝试直接使用 SQL 插入记录
        print("\n尝试使用原始 SQL 插入记录...")
        try:
            db.execute(
                text("""
                INSERT INTO custom_fields (id, user_id, field_name, field_value, created_at, updated_at)
                VALUES (gen_random_uuid(), :user_id, :field_name, :field_value, NOW(), NOW())
                """),
                {"user_id": user_id, "field_name": "sql_test_field", "field_value": "sql_test_value"}
            )
            db.commit()
            print("成功使用 SQL 插入记录")
            
            # 查询插入的记录
            result = db.execute(
                text("SELECT * FROM custom_fields WHERE user_id = :user_id AND field_name = :field_name"),
                {"user_id": user_id, "field_name": "sql_test_field"}
            ).fetchone()
            
            if result:
                print(f"成功查询到 SQL 插入的记录: {result}")
            else:
                print("未找到 SQL 插入的记录")
        except Exception as e2:
            print(f"使用 SQL 插入记录时出错: {str(e2)}")

print("\n====== 测试完成 ======") 