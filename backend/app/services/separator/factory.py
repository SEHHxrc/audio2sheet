# -*- coding: utf-8 -*-
# audio2sheet/backend/app/services/separator/factory.py
from backend.app.services.base import AudioSeparator
from backend.app.services.separator.demucs_impl import DemucsSeparator
from backend.app.services.separator.spleeter_impl import SpleeterSeparator

class SeparatorFactory:
    """
    音源分离引擎工厂类
    """
    @staticmethod
    def get_separator(engine_name: str, model_name: str) -> AudioSeparator:
        """
        根据前端传来的引擎名称和模型名称，动态分发并返回对应的分离处理器
        """
        engine_lower = engine_name.lower()
        if engine_lower == "demucs":
            return DemucsSeparator(model_name=model_name)
        elif engine_lower == "spleeter":
            return SpleeterSeparator(model_name=model_name)
        else:
            raise ValueError(f"暂不支持的分离引擎: {engine_name}")
