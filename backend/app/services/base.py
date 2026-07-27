# -*- coding: utf-8 -*-
# audio2sheet/backend/app/services/base.py
from abc import ABC, abstractmethod

# --- 1. 音源拆分接口 ---
class AudioSeparator(ABC):
    @abstractmethod
    def separate(self, audio_path: str, output_dir: str) -> dict:
        """
        读取混音音频，进行分离，输出分离后的单声道音频文件。

        :param audio_path: 原始混音音频文件的路径
        :param output_dir: 分离后的各个单轨 WAV 音频的存放目录
        :return: 字典，键为分离出的音轨名（如 'vocals', 'other'），值为对应的 WAV 文件绝对路径
        """
        pass

# --- 2. 音高识别接口 ---
class AudioTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, output_midi_path: str) -> None:
        """输入单声道音频，输出 MIDI 文件"""
        pass

# --- 3. 乐谱排版渲染接口 ---
class ScoreRenderer(ABC):
    @abstractmethod
    def render(self, xml_path: str, output_pdf_path: str) -> None:
        """输入 MusicXML，输出排版后的 PDF/PNG"""
        pass
