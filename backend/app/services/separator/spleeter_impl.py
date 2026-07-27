# -*- coding: utf-8 -*-
# audio2sheet/backend/app/services/separator/spleeter_impl.py
import os
import subprocess
import shutil
from backend.app.services.base import AudioSeparator


class SpleeterSeparator(AudioSeparator):
    """
    基于 Deezer Spleeter 的快速音源分离服务（免显卡，极速运行）
    """

    def __init__(self, model_name: str = "5stems"):
        # model_name 可选: "2stems" (vocals/accomp), "4stems" (v/d/b/o), "5stems" (v/d/b/p/o)
        self.model_name = model_name

    def separate(self, audio_path: str, output_dir: str) -> dict:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"未找到输入音频: {audio_path}")

        os.makedirs(output_dir, exist_ok=True)
        print(f"[音源分离] 正在通过系统命令行调用 Spleeter (配置: {self.model_name})...")

        # spleeter 命令行格式
        command = [
            "spleeter",
            "separate",
            "-o", output_dir,
            "-p", f"spleeter:{self.model_name}",
            audio_path
        ]

        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"Spleeter 运行失败: {result.stderr or result.stdout}")

        # Spleeter 默认会输出至 output_dir/音频名/ 目录下
        audio_stem = os.path.splitext(os.path.basename(audio_path))[0]
        spleeter_deep_dir = os.path.join(output_dir, audio_stem)

        output_paths = {}
        # 动态扫描生成的所有音轨并提取出来
        if os.path.exists(spleeter_deep_dir):
            for file_name in os.listdir(spleeter_deep_dir):
                if file_name.lower().endswith(".wav"):
                    stem = os.path.splitext(file_name)[0]
                    src_file = os.path.join(spleeter_deep_dir, file_name)
                    dest_file = os.path.join(output_dir, file_name)

                    if os.path.exists(dest_file):
                        os.remove(dest_file)
                    shutil.move(src_file, dest_file)
                    output_paths[stem] = os.path.abspath(dest_file)

            try:
                shutil.rmtree(spleeter_deep_dir)
            except Exception:
                pass

        return output_paths
