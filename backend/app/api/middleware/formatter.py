# -*- coding: utf-8 -*-
# audio2sheet/backend/app/api/middleware/formatter.py
from functools import wraps
from typing import Dict, Any, List

# 1. 内部参数配置元数据（对核心算法和前端均隐藏，仅由格式化中间件内部掌握）
_PARAMETER_METADATA = {
    "onset_threshold": {
        "name": {"zh": "AI 起始音敏感度", "en": "Onset Sensitivity"},
        "ui_type": "slider",
        "min": 0.0, "max": 1.0, "step": 0.05
    },
    "frame_threshold": {
        "name": {"zh": "AI 持续音敏感度", "en": "Frame Sensitivity"},
        "ui_type": "slider",
        "min": 0.0, "max": 1.0, "step": 0.05
    },
    "minimum_note_length": {
        "name": {"zh": "过滤极短杂音(毫秒)", "en": "Min Note Length (ms)"},
        "ui_type": "input_number",
        "min": 0, "max": 1000, "step": 10
    },
    "auto_transpose": {
        "name": {"zh": "自动适配音域", "en": "Auto Range Adaptation"},
        "ui_type": "switch"
    }
}


def format_parameters(raw_params: Dict[str, Any], lang: str = "zh") -> List[Dict[str, Any]]:
    """
    格式化输出的核心转换函数。
    将纯技术字典： {"onset_threshold": 0.3}
    转换为标准前端组件数据： [{"key": "onset_threshold", "display_name": "AI 起始音敏感度", ...}]
    """
    formatted_list = []
    for key, value in raw_params.items():
        meta = _PARAMETER_METADATA.get(key, {})

        # 参数名转义：如果在元数据里有定义，就取对应语言的名称，否则默认显示 key 兜底
        display_name = meta.get("name", {}).get(lang, key)

        # 组装为前端可以直接渲染的标准组件对象
        item = {
            "key": key,  # 供前端提交时使用的参数名
            "display_name": display_name,  # 【转义后】的展示名称（中文/英文）
            "value": value,  # 当前/默认值
            "ui_type": meta.get("ui_type", "input"),  # 对应前端的组件类型
            "min": meta.get("min"),
            "max": meta.get("max"),
            "step": meta.get("step")
        }
        formatted_list.append(item)

    return formatted_list


def format_api_response(lang_param_name: str = "lang"):
    """
    类似于中间件的 FastAPI 响应格式化装饰器。
    会自动拦截 API 的返回结果，并将其中的参数部分进行格式化和转义。
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. 运行原 API 路由函数，获取最原始、纯粹的技术字典
            raw_data = func(*args, **kwargs)

            # 2. 从请求参数中提取前端期望的语言（默认为中文 'zh'）
            lang = kwargs.get(lang_param_name, "zh")

            # 3. 经过中间件函数统一转义、格式化
            formatted_data = format_parameters(raw_data, lang)

            # 4. 返回包装后的规范响应
            return {
                "status": "success",
                "data": formatted_data
            }

        return wrapper

    return decorator
