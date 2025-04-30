"""
Database utilities
"""

import os
import sys
import logging
from dotenv import load_dotenv
import importlib
from agir_db.db.session import get_db, SessionLocal
from agir_db.models import User, Process
from agir_db.db.base_class import Base
from ..evolution.process_instance_manager import ProcessManager

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from agir_db.db.session import engine
    # 尝试导入迁移模块
    try:
        # import agir_db.alembic.env as alembic_env
        has_alembic = False
        has_alembic = True
    except ImportError:
        logger.warning("Alembic migrations not available, will use SQLAlchemy create_all instead")
        has_alembic = False
except ImportError:
    logger.error("agir_db package not found. Please install it using pip install -e git+https://github.com/agircc/agir-db.git")
    sys.exit(1)

def check_database() -> bool:
    """
    Check if database is configured correctly.
    
    Returns:
        bool: True if database is configured correctly, False otherwise
    """
    try:
        # Use ProcessManager to check database tables
        return ProcessManager.check_database_tables()
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return False

def run_migrations():
    """运行数据库迁移"""
    try:
        # 使用Alembic运行迁移或使用SQLAlchemy创建表
        if has_alembic:
            try:
                # 尝试使用alembic运行迁移
                from alembic import command
                from alembic.config import Config
                
                # 获取alembic配置文件路径
                alembic_cfg_path = os.path.join(os.path.dirname(importlib.util.find_spec("agir_db").origin), "alembic.ini")
                
                if os.path.exists(alembic_cfg_path):
                    alembic_cfg = Config(alembic_cfg_path)
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Alembic migrations completed successfully")
                else:
                    logger.warning(f"Alembic config not found at {alembic_cfg_path}, falling back to SQLAlchemy create_all")
                    Base.metadata.create_all(bind=engine)
                    logger.info("SQLAlchemy tables created successfully")
            except Exception as e:
                logger.error(f"Alembic migration failed: {str(e)}")
                logger.info("Falling back to SQLAlchemy create_all")
                Base.metadata.create_all(bind=engine)
                logger.info("SQLAlchemy tables created successfully")
        else:
            # 使用SQLAlchemy创建所有表
            Base.metadata.create_all(bind=engine)
            logger.info("SQLAlchemy tables created successfully")
            
        return True
    except Exception as e:
        logger.error(f"Database migration failed: {str(e)}")
        return False

__all__ = ["get_db", "SessionLocal", "User", "Process", "check_database", "run_migrations"] 