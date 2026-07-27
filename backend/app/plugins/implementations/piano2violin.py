# -*- coding: utf-8 -*-
# audio2sheet/backend/app/plugins/implementations/piano2violin.py
import music21
from backend.app.plugins.base import PolyToMonoAdapter


class PianoToViolinAdapter(PolyToMonoAdapter):
    plugin_id = "piano2violin"
    source_instrument = "piano"
    target_instrument = "violin"

    def adapt(self, score: music21.stream.Score, **kwargs) -> music21.stream.Score:
        """
        真实的钢琴转小提琴适配算法（带节奏量化与噪声过滤）
        """
        # 1. 提取单声部旋律
        mono_part = self.extract_highest_melody(score)

        # 2. 注入小提琴特定的乐器和谱号标记（高音谱号）
        mono_part.insert(0, music21.instrument.Violin())
        mono_part.insert(0, music21.clef.TrebleClef())

        # 3.1 节奏量化（Quantization）：强行对齐到合理的节奏网格（如 16分音符 和 三连音）
        # 这会把 AI 识别出来的怪异小休止符和碎音符，合并、对齐为人类可读的规整节奏
        mono_part = mono_part.quantize(
            quarterLengthDivisors=(4, 3),  # 4表示16分音符，3表示三连音
            processOffsets=True,
            processDurations=True,
            inPlace=False
        )

        # 3.2 过滤极短的杂音（Ghost Notes）
        # 钢琴共鸣产生的小于 0.15 拍（约 32分音符以下）的超短音符，通常是噪音，直接滤除
        clean_part = music21.stream.Part()
        clean_part.insert(0, music21.instrument.Violin())
        clean_part.insert(0, music21.clef.TrebleClef())

        # 复制拍号和调号
        for el in mono_part.flatten().getElementsByClass([music21.meter.TimeSignature, music21.key.KeySignature]):
            clean_part.insert(el.offset, el)

        for note_obj in mono_part.flatten().notesAndRests:
            # 如果是音符且时值足够长，或者本身就是休止符，则保留
            if isinstance(note_obj, music21.note.Note):
                if note_obj.duration.quarterLength >= 0.25:  # 0.25 拍即一个16分音符，短于此的音符直接抛弃
                    # 限制音域并移调
                    while note_obj.pitch.midi < 55:
                        note_obj.transpose(12, inPlace=True)
                    while note_obj.pitch.midi > 100:
                        note_obj.transpose(-12, inPlace=True)
                    clean_part.insert(note_obj.offset, note_obj)
            else:
                # 保持休止符
                clean_part.insert(note_obj.offset, note_obj)

        # 4. 封装并返回
        adapted_score = music21.stream.Score()
        adapted_score.insert(0, clean_part)
        return adapted_score
