# -*- coding: utf-8 -*-
# audio2sheet/backend/app/api/endpoints/plugins.py
from fastapi import APIRouter
from backend.app.plugins import registry
from backend.app.api.middleware.formatter import format_api_response

router = APIRouter()

@router.get("/plugins")
def get_plugins():
    """
    获取当前系统加载的所有乐谱改编插件列表，供前端下拉菜单使用
    """
    return {
        "status": "success",
        "data": registry.list_adapters()
    }

@router.get("/transcribe/default-settings")
@format_api_response(lang_param_name="lang")  # 挂载格式化输出中间件
def get_default_settings(lang: str = "zh"):
    """
    获取转谱模块默认的技术参数。
    经 format_api_response 中间件处理后，会被自动包装并转义为前端可读的组件描述。
    """
    # 核心逻辑只负责返回纯技术键值对，格式化和语言转义由中间件托管
    return {
        "onset_threshold": 0.3,
        "frame_threshold": 0.25,
        "minimum_note_length": 100,
        "auto_transpose": True
    }
