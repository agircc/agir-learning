#!/usr/bin/env python
"""
适配器模块 - 用于连接 UserMemory 和 custom_fields 表
该模块提供了一个类，可以在代码中用作 CustomField，但实际上使用数据库中的 custom_fields 表
"""

import logging
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CustomFieldAdapter:
    """
    适配器类，将 custom_fields 表的操作转化为类似 CustomField 的接口
    """
    
    def __init__(self, db: Session, user_id=None, field_name=None, field_value=None):
        """
        初始化适配器
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            field_name: 字段名
            field_value: 字段值
        """
        self.db = db
        self.user_id = user_id
        self.field_name = field_name
        self.field_value = field_value
        self._id = None
        
    def save(self):
        """
        保存字段到数据库
        """
        if not self.user_id or not self.field_name:
            raise ValueError("必须提供 user_id 和 field_name")
            
        # 检查是否存在同名字段
        existing = self.db.execute(
            text("""
            SELECT id FROM custom_fields 
            WHERE user_id = :user_id AND field_name = :field_name
            """),
            {"user_id": self.user_id, "field_name": self.field_name}
        ).fetchone()
        
        if existing:
            # 更新现有字段
            self.db.execute(
                text("""
                UPDATE custom_fields 
                SET field_value = :field_value, updated_at = NOW()
                WHERE id = :id
                """),
                {"field_value": self.field_value, "id": existing[0]}
            )
            self._id = existing[0]
        else:
            # 创建新字段
            result = self.db.execute(
                text("""
                INSERT INTO custom_fields (id, user_id, field_name, field_value, created_at, updated_at)
                VALUES (gen_random_uuid(), :user_id, :field_name, :field_value, NOW(), NOW())
                RETURNING id
                """),
                {"user_id": self.user_id, "field_name": self.field_name, "field_value": self.field_value}
            ).fetchone()
            
            if result:
                self._id = result[0]
        
        self.db.commit()
        return self
        
    @classmethod
    def find(cls, db: Session, user_id, field_name):
        """
        查找字段
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            field_name: 字段名
            
        Returns:
            CustomFieldAdapter 实例或 None
        """
        result = db.execute(
            text("""
            SELECT id, field_value FROM custom_fields 
            WHERE user_id = :user_id AND field_name = :field_name
            """),
            {"user_id": user_id, "field_name": field_name}
        ).fetchone()
        
        if not result:
            return None
            
        instance = cls(db, user_id, field_name, result[1])
        instance._id = result[0]
        return instance
        
    @classmethod
    def delete(cls, db: Session, user_id, field_name):
        """
        删除字段
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            field_name: 字段名
            
        Returns:
            是否成功删除
        """
        result = db.execute(
            text("""
            DELETE FROM custom_fields 
            WHERE user_id = :user_id AND field_name = :field_name
            """),
            {"user_id": user_id, "field_name": field_name}
        )
        db.commit()
        return result.rowcount > 0
        
    def __repr__(self):
        return f"<CustomField(user_id={self.user_id}, field_name={self.field_name})>"


# 使用适配器代替CustomField
def apply_adapter():
    """
    将CustomFieldAdapter应用到代码中，替换CustomField的导入
    """
    import sys
    from types import ModuleType
    
    # 创建一个假模块
    fake_module = ModuleType('agir_db.models.custom_fields')
    fake_module.CustomField = CustomFieldAdapter
    
    # 添加到sys.modules
    sys.modules['agir_db.models.custom_fields'] = fake_module
    
    logger.info("Successfully applied CustomFieldAdapter as agir_db.models.custom_fields.CustomField")
    
    return CustomFieldAdapter


if __name__ == "__main__":
    # 测试适配器
    from agir_db.db.session import SessionLocal
    
    with SessionLocal() as db:
        # 创建一个测试字段
        test_field = CustomFieldAdapter(db, 
            user_id=uuid.uuid4(), 
            field_name="test_adapter", 
            field_value="test value"
        )
        test_field.save()
        
        print(f"创建的字段: {test_field}")
        
        # 模拟替换CustomField导入
        CustomField = CustomFieldAdapter
        
        # 测试能否正常使用
        another_field = CustomField(db,
            user_id=test_field.user_id,
            field_name="another_test",
            field_value="another value"
        )
        another_field.save()
        
        print(f"另一个字段: {another_field}") 