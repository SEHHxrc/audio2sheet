# -*- coding: utf-8 -*-
# audio2sheet/backend/tests/piano2violin_test.py
import os
import sys
import music21

# 确保导入路径正确
backend_path = os.path.join(os.path.dirname(__file__), "..")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.app.plugins import registry


def generate_mock_piano_score() -> music21.stream.Score:
    """
    用代码动态生成一段“钢琴多声部和弦”乐谱，用来做测试输入
    """
    score = music21.stream.Score()
    part = music21.stream.Part()
    part.insert(0, music21.instrument.Piano())

    # 构造两个超低音钢琴和弦（低于小提琴音域 G3/MIDI 55）：
    # 和弦 1: C2 (36), E2 (40), G2 (43)  --> 理论上最高音是 G2 (43)
    # 和弦 2: F2 (41), A2 (45), C3 (48)  --> 理论上最高音是 C3 (48)
    chord1 = music21.chord.Chord(["C2", "E2", "G2"])
    chord1.duration.type = 'half'  # 二分音符

    chord2 = music21.chord.Chord(["F2", "A2", "C3"])
    chord2.duration.type = 'half'  # 二分音符

    part.append(chord1)
    part.append(chord2)
    score.insert(0, part)
    return score


def main():
    print("--- 启动真实乐理适配转换测试 ---")

    # 1. 生成模拟的输入乐谱（钢琴多声部超低音区）
    mock_piano_score = generate_mock_piano_score()
    print("已成功在内存中生成测试钢琴谱（包含低音和弦 C2-E2-G2 和 F2-A2-C3）。")

    # 2. 从插件注册中心获取“钢琴转小提琴”插件
    try:
        adapter = registry.get_adapter("piano2violin")
    except KeyError:
        print("未找到 piano2violin 插件，请确认 implementations 是否放置了 piano_to_violin.py")
        return

    # 3. 执行适配算法
    print(f"\n正在执行插件 [{adapter.plugin_id}] 对乐谱进行转换...")
    adapted_violin_score = adapter.adapt(mock_piano_score)

    # 4. 验证和输出结果
    print("\n--- 转换结果分析 ---")
    for note_obj in adapted_violin_score.flatten().notes:
        if isinstance(note_obj, music21.note.Note):
            # 打印转换后的音名和其 MIDI 编号，验证是否移调成功
            print(f"转换后保留的音符: {note_obj.pitch.nameWithOctave} (MIDI 编号: {note_obj.pitch.midi})")

    # 5. 将转换后的小提琴谱保存为标准 MusicXML 格式
    output_dir = os.path.join(os.path.dirname(__file__), "../../storage", "adapted")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "test_violin_score.musicxml")

    adapted_violin_score.write('musicxml', fp=output_path)
    print(f"\n[成功] 转换完成！生成的小提琴五线谱已保存至: {output_path}")
    print("（提示：您可以使用 MuseScore, Overture 等打谱软件直接打开此 .musicxml 文件查看五线谱效果）")


if __name__ == "__main__":
    main()
