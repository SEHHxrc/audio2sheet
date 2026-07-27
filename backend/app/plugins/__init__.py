# -*- coding: utf-8 -*-
# audio2sheet/backend/app/plugins/__init__.py
import importlib
import pkgutil
import os
import logging
from .base import ScoreAdapter, PolyToMonoAdapter
from .registry import registry

# 导出基础类和注册中心，方便外部调用
__all__ = ["ScoreAdapter", "PolyToMonoAdapter", "registry"]

logger = logging.getLogger(__name__)


def discover_and_register_plugins():
    """
    动态扫描 implementations 目录，并注册所有实现了 ScoreAdapter 接口的插件
    """
    # 定位 implementations 文件夹的绝对路径
    current_dir = os.path.dirname(__file__)
    implementations_dir = os.path.join(current_dir, "implementations")

    if not os.path.exists(implementations_dir):
        logger.warning(f"未找到插件实现目录: {implementations_dir}")
        return

    # 定义包名，以便进行绝对导入
    package_name = "backend.app.plugins.implementations"

    # 遍历 implementations 文件夹下的所有 Python 模块
    for _, module_name, is_pkg in pkgutil.iter_modules([implementations_dir]):
        if is_pkg:
            continue

        full_module_name = f"{package_name}.{module_name}"
        try:
            # 动态导入该模块
            module = importlib.import_module(full_module_name)

            # 遍历该模块内的所有属性，寻找 ScoreAdapter 的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                # 筛选条件：是一个类，且是 ScoreAdapter 的子类，但不能是接口基类本身
                if (
                        isinstance(attr, type)
                        and issubclass(attr, ScoreAdapter)
                        and attr is not ScoreAdapter
                        and attr is not PolyToMonoAdapter
                ):
                    # 自动注册到注册中心
                    registry.register(attr)

        except Exception as e:
            logger.error(f"加载插件模块 {full_module_name} 出错: {e}")


# 在包被导入时自动执行发现程序
discover_and_register_plugins()
