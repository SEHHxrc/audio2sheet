# -*- coding: utf-8 -*-
# audio2sheet/backend/tests/piano2xml_test.py
import os
import sys
import music21

# 确保导入路径正确
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.services.transcriber.basic_pitch_impl import BasicPitchTranscriber
from backend.app.plugins import registry


def main():
    print("======== 启动音频到五线谱集成流水线测试 ========\n")

    # 0. 配置输入音频路径与中间/最终文件的输出路径
    input_audio = r"D:\audio2sheet\test_piano.wav"  # <--- 请确保在这个路径下放一个您的测试音频文件

    storage_dir = os.path.join(os.path.dirname(__file__), "storage")
    midi_output = os.path.join(storage_dir, "midi", "transcribed_piano.mid")
    violin_xml_output = os.path.join(storage_dir, "adapted", "violin_adapted_score.musicxml")

    if not os.path.exists(input_audio):
        print(f"提示: 请先准备一个真实的音频文件并放置在 {input_audio}")
        print("（您可以录制一段简短的钢琴、吉他或哼唱音频存为 wav/mp3 格式进行测试）")
        return

    # 1. 【步骤一：音频转 MIDI】
    # 实例化我们的音高转录服务并运行
    transcriber = BasicPitchTranscriber()
    try:
        transcriber.transcribe(input_audio, midi_output)
    except Exception as e:
        print(f"[错误] 音频转录失败: {e}")
        return

    # 2. 【步骤二：加载生成的 MIDI 进行改编】
    print("\n正在将转录的 MIDI 加载入乐理引擎...")
    try:
        # 使用 music21 解析刚才生成的 MIDI 文件
        piano_score = music21.converter.parse(midi_output)
    except Exception as e:
        print(f"[错误] 乐理引擎解析 MIDI 失败: {e}")
        return

    # 3. 【步骤三：调用钢琴转小提琴插件】
    try:
        adapter = registry.get_adapter("piano2violin")
    except KeyError:
        print("[错误] 未找到 piano2violin 改编插件。")
        return

    print(f"正在调用插件 [{adapter.plugin_id}] 进行小提琴音域适配...")
    try:
        # 进行多声部塌陷、最高音提取、小提琴音域约束和移调
        violin_score = adapter.adapt(piano_score)
    except Exception as e:
        print(f"[错误] 改编转换失败: {e}")
        return

    # 4. 【步骤四：输出改编后的 MusicXML 五线谱】
    try:
        os.makedirs(os.path.dirname(violin_xml_output), exist_ok=True)
        violin_score.write('musicxml', fp=violin_xml_output)
        print(f"\n🎉 [大成功] 完整管线执行完毕！")
        print(f"最终小提琴谱已生成至: {violin_xml_output}")
    except Exception as e:
        print(f"[错误] 写入 MusicXML 失败: {e}")


if __name__ == "__main__":
    main()
