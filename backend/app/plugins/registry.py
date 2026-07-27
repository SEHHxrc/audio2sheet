# -*- coding: utf-8 -*-
# backend/app/plugins/registry.py
import logging
from typing import Dict, Type, List, Any
from .base import ScoreAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    乐谱改编插件注册中心
    """

    def __init__(self):
        # 键为 plugin_id，值为已实例化的插件对象
        self._adapters: Dict[str, ScoreAdapter] = {}

    def register(self, adapter_cls: Type[ScoreAdapter]):
        """
        注册一个插件类（在自动加载时被调用）
        """
        try:
            adapter_instance = adapter_cls()
            plugin_id = adapter_instance.plugin_id

            if plugin_id in self._adapters:
                logger.warning(f"插件 ID '{plugin_id}' 已被注册。原有插件将被覆盖。")

            self._adapters[plugin_id] = adapter_instance
            logger.info(
                f"成功注册乐谱改编插件: [{plugin_id}] ({adapter_instance.source_instrument} -> {adapter_instance.target_instrument})")
        except Exception as e:
            logger.error(f"注册插件类 {adapter_cls.__name__} 失败: {e}")

    def get_adapter(self, plugin_id: str) -> ScoreAdapter:
        """
        根据 ID 获取插件实例
        """
        if plugin_id not in self._adapters:
            raise KeyError(f"未找到标识符为 '{plugin_id}' 的乐谱改编插件")
        return self._adapters[plugin_id]

    def list_adapters(self) -> List[Dict[str, Any]]:
        """
        列出所有已加载插件的信息，供 FastAPI 接口返回给前端下拉菜单
        """
        return [
            {
                "plugin_id": inst.plugin_id,
                "source_instrument": inst.source_instrument,
                "target_instrument": inst.target_instrument,
            }
            for inst in self._adapters.values()
        ]


# 暴露出一个全局唯一的注册表实例
registry = AdapterRegistry()
