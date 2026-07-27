# -*- coding: utf-8 -*-
# audio2sheet/backend/app/config.py
import os

# 1. 项目根目录定位
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. 统一的数据存储根目录
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# 3. 细分业务子目录
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")      # 原始上传混音音频
SEPARATED_DIR = os.path.join(STORAGE_DIR, "separated")  # Demucs 分离出的音轨
MIDI_DIR = os.path.join(STORAGE_DIR, "midi")            # Basic Pitch 识别出的 MIDI
ADAPTED_DIR = os.path.join(STORAGE_DIR, "adapted")      # 改编后的小提琴等 MusicXML

# 4. PyTorch 缓存目录（防止 Windows C:\Users 权限问题）
TORCH_CACHE_DIR = os.path.join(STORAGE_DIR, "cache", "torch")

# 5. 跨域访问白名单（允许前端的网页端口访问后端，如 http://localhost:3000）
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8501",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8501",
]

# 启动时自动确保所有必需的文件夹在磁盘上被创建
for path in [UPLOAD_DIR, SEPARATED_DIR, MIDI_DIR, ADAPTED_DIR, TORCH_CACHE_DIR]:
    os.makedirs(path, exist_ok=True)
