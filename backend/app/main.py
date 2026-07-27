# -*- coding: utf-8 -*-
# audio2sheet/backend/app/main.py
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 确保导入路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.app import config
# === 核心修改：导入 audio 路由器 ===
from backend.app.api.endpoints import plugins, audio

app = FastAPI(
    title="音频转五线谱与乐谱改编 API",
    description="提供 AI 音源分离、AI 乐符转录、以及多声部乐器改编插件服务的后端 Web 系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 核心修改：挂载子路由 ===
app.include_router(plugins.router, prefix="/api", tags=["插件与配置"])
app.include_router(audio.router, prefix="/api", tags=["音频处理与异步任务"])  # <-- 挂载音频任务路由

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "音频转五线谱服务已成功运行。"}
