# -*- coding: utf-8 -*-
# audio2sheet/backend/app/services/transcriber/basic_pitch_impl.py
import os
import pathlib
import logging
from backend.app.services.base import AudioTranscriber
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

logger = logging.getLogger(__name__)


class BasicPitchTranscriber(AudioTranscriber):
    """
    基于 Spotify Basic Pitch 模型的多音高转录服务（支持敏感度参数微调）
    """

    def transcribe(
            self,
            audio_path: str,
            output_midi_path: str,
            onset_threshold: float = 0.3,  # 起始音敏感度（默认 0.3）
            frame_threshold: float = 0.25,  # 持续音敏感度（默认 0.25）
            minimum_note_length: int = 100  # 忽略短于该毫秒数的极短杂音（默认 100ms）
    ) -> None:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"未找到输入音频文件: {audio_path}")

        output_dir = os.path.dirname(output_midi_path)
        os.makedirs(output_dir, exist_ok=True)

        print(f"正在调用 AI 引擎（敏感度 - 起始: {onset_threshold}, 持续: {frame_threshold}）分析音频...")

        # 运行识别，并将敏感度参数透传给底层 basic-pitch API
        predict_and_save(
            audio_path_list=[audio_path],
            output_directory=output_dir,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            minimum_note_length=minimum_note_length
        )

        # 自动定位生成的文件，并重命名为用户指定的 output_midi_path
        audio_stem = pathlib.Path(audio_path).stem
        default_output_name = f"{audio_stem}_basic_pitch.midi"
        default_output_path = os.path.join(output_dir, default_output_name)

        if os.path.exists(default_output_path):
            if os.path.exists(output_midi_path):
                os.remove(output_midi_path)
            os.rename(default_output_path, output_midi_path)
            print(f"[转录服务] 音频转 MIDI 成功，已保存至: {output_midi_path}")
        else:
            raise RuntimeError("Basic Pitch 运行结束，但未能生成或定位中间 MIDI 文件。")
