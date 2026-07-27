# -*- coding: utf-8 -*-
# audio2sheet/backend/tests/separate_test.py
import os
import sys
import warnings
import music21

# 屏蔽 librosa 等库的非致命降级警告，让终端输出更干净
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# 确保导入路径正确
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.services.separator.demucs_impl import DemucsSeparator
from backend.app.services.transcriber.basic_pitch_impl import BasicPitchTranscriber
from backend.app.plugins import registry


def main():
    print("======== 🚀 启动 [音源分离 + AI转谱 + 乐理改编] 终极集成测试 ========\n")

    # 0. 配置输入与输出路径
    input_mixed_audio = r"E:\project_py\audio2sheet\test_piano.wav"  # <--- 请在此处放一个钢琴+小提琴合奏的音频进行测试

    storage_dir = os.path.join(os.path.dirname(__file__), "storage")
    separated_dir = os.path.join(storage_dir, "separated")
    midi_output = os.path.join(storage_dir, "midi", "transcribed_piano.midi")
    violin_xml_output = os.path.join(storage_dir, "adapted", "violin_adapted_score.musicxml")

    if not os.path.exists(input_mixed_audio):
        print(f"[提示] 请先准备一个真实的【混音合奏音频】放置在: {input_mixed_audio}")
        print("（如果您手头没有双乐器音频，也可以先放一首普通的 mp3 或 wav 歌曲来测试音源拆分效果）")
        return

    # =========================================================================
    # 1. 【步骤一：音源分离】将混音音频拆分为独立音轨
    # =========================================================================
    separator = DemucsSeparator()
    try:
        # 分离结果字典，例如：{'vocals': '.../vocals.wav', 'other': '.../other.wav', ...}
        separated_tracks = separator.separate(input_mixed_audio, separated_dir)
    except Exception as e:
        print(f"[错误] 音源分离失败: {e}")
        return

    # =========================================================================
    # 2. 【步骤二：选取目标轨进行音高识别】
    # 对于钢琴+小提琴的合奏，我们通常选择提取钢琴（'other' 轨）或旋律（'vocals' 轨）
    # 这里我们默认提取 'other' 轨（代表钢琴伴奏）来进行转写
    # =========================================================================
    target_track_name = "other"  # 您也可以根据拆分效果，手动改为 "vocals" 进行测试
    if target_track_name not in separated_tracks:
        print(f"[错误] 分离结果中未找到目标音轨 '{target_track_name}'")
        return

    target_audio_path = separated_tracks[target_track_name]
    print(f"\n[流水线] 成功锁定目标音轨 [{target_track_name}]，准备进行音高转录...")

    # =========================================================================
    # 3. 【步骤三：音高识别】调用 Basic Pitch 将单轨 WAV 转为 MIDI
    # =========================================================================
    transcriber = BasicPitchTranscriber()
    try:
        transcriber.transcribe(target_audio_path, midi_output)
    except Exception as e:
        print(f"[错误] 音高转录失败: {e}")
        return

    # =========================================================================
    # 4. 【步骤四：加载并运行改编插件（带节奏量化）】
    # =========================================================================
    print("\n[流水线] 正在将转录后的 MIDI 加载入乐理改编引擎...")
    try:
        piano_score = music21.converter.parse(midi_output)
        adapter = registry.get_adapter("piano2violin")

        print(f"[流水线] 正在调用插件 [{adapter.plugin_id}] 进行小提琴适配（过滤杂音+节奏量化）...")
        violin_score = adapter.adapt(piano_score)

    except Exception as e:
        print(f"[错误] 乐谱改编转换失败: {e}")
        return

    # =========================================================================
    # 5. 【步骤五：导出最终小提琴谱 MusicXML】
    # =========================================================================
    try:
        os.makedirs(os.path.dirname(violin_xml_output), exist_ok=True)
        violin_score.write('musicxml', fp=violin_xml_output)
        print(f"\n🎉 [大成功] 完整音频到小提琴五线谱管线已全部跑通！")
        print(f"  -> 原始混音文件: {input_mixed_audio}")
        print(f"  -> 分离出的钢琴轨音频: {target_audio_path}")
        print(f"  -> 最终导出的规整小提琴谱: {violin_xml_output}")
    except Exception as e:
        print(f"[错误] 写入最终 MusicXML 失败: {e}")


if __name__ == "__main__":
    main()
