# -*- coding: utf-8 -*-
# audio2sheet/backend/app/services/separator/demucs_impl.py
import os
import shutil
import logging
from backend.app.services.base import AudioSeparator
import demucs.api

logger = logging.getLogger(__name__)


class DemucsSeparator(AudioSeparator):
    """
    基于命令行调用 demucs 的音源分离服务（动态适配任意模型音轨）
    """

    def __init__(self, model_name: str = "htdemucs"):
        self.model_name = model_name
        # 初始化官方API分离器
        self.separator = demucs.api.Separator(model=self.model_name)

    def separate(self, audio_path: str, output_dir: str) -> dict:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"未找到输入混音音频文件: {audio_path}")

        os.makedirs(output_dir, exist_ok=True)
        print(f"\n[音源分离] 正在加载 Demucs 模型: {self.model_name}...")

        # 调用官方 API 进行音频分离 (返回原始音频张量与分离后的音轨字典)
        _, separated = self.separator.separate_audio_file(audio_path)

        output_paths = {}

        # === 不硬编码音轨名，动态扫描生成的所有 .wav 文件 ===
        # 这样无论选择 4 声部模型还是 6 声部模型（新增 piano, guitar），都能自动提取并输出
        print("[音源分离] 正在动态整理并提取音频轨...")
        for stem, source_tensor in separated.items():
            # 定义输出文件的完整路径
            stem_filename = f"{stem}.wav"
            stem_path = os.path.join(output_dir, stem_filename)

            # 如果目标文件已存在先删除，防止文件冲突
            if os.path.exists(stem_path):
                os.remove(stem_path)

            demucs.api.save_audio(source_tensor, stem_path, self.separator.samplerate)
            output_paths[stem] = os.path.abspath(stem_path)
            print(f" -> 提取音轨成功 [{stem}]: {stem_path}")

        try:
            shutil.rmtree(os.path.join(output_dir, self.model_name))
        except Exception:
            pass

        print("[音源分离] 整理完毕！")
        return output_paths
