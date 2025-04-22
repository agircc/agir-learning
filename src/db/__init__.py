"""
Database utilities
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from agir_db.db.session import get_db, SessionLocal
    from agir_db.models import User, Process
    from agir_db.db.base import Base
    import agir_db.db.migrations as migrations
except ImportError:
    logger.error("agir_db package not found. Please install it using pip install -e git+https://github.com/agircc/agir-db.git")
    sys.exit(1)

def check_database():
    """检查数据库是否存在和表是否创建，如果不存在则运行迁移文件"""
    try:
        # 检查数据库连接
        db = next(get_db())
        
        # 尝试查询用户表以检查表是否存在
        try:
            db.query(User).first()
            logger.info("Database check passed: tables exist")
            return True
        except Exception as e:
            logger.warning(f"Database tables do not exist: {str(e)}")
            # 运行迁移
            logger.info("Running database migrations...")
            migrations.run_migrations()
            logger.info("Database migrations completed")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()

__all__ = ["get_db", "SessionLocal", "User", "Process", "check_database"] 