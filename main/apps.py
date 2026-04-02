from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        """Django 启动时自动执行"""
        logger.info("Main 应用已启动")

        # 启动 Agent 文件自动同步
        # 可通过环境变量 AGENT_AUTO_SYNC=true 启用
        import os
        if os.environ.get('AGENT_AUTO_SYNC', '').lower() == 'true':
            try:
                from .agent_auto_sync import auto_start_sync
                auto_start_sync()
                logger.info("Agent 文件自动同步已启用")
            except Exception as e:
                logger.error(f"启动 Agent 自动同步失败：{e}")
