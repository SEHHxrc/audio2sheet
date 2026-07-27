# -*- coding: utf-8 -*-
# audio2sheet/backend/app/plugins/base.py
from abc import ABC, abstractmethod
import music21


class ScoreAdapter(ABC):
    """所有乐谱改编插件的抽象基类"""

    @property
    @abstractmethod
    def plugin_id(self) -> str: pass

    @property
    @abstractmethod
    def source_instrument(self) -> str: pass

    @property
    @abstractmethod
    def target_instrument(self) -> str: pass

    @abstractmethod
    def adapt(self, score: music21.stream.Score, **kwargs) -> music21.stream.Score:
        pass


class PolyToMonoAdapter(ScoreAdapter, ABC):
    """多声部转单声部（多音到单音）的通用模板类"""

    def extract_highest_melody(self, score: music21.stream.Score) -> music21.stream.Part:
        """
        利用 music21 的 chordify()，将输入的多声部乐谱塌陷为一轨和弦，
        并在每个时间点提取音高最高的音符，从而提炼出单声部主旋律。
        """
        # 1. 塌陷为单轨道和弦流，并进行 .flatten() 展平！
        # 展平后，小节结构被解散，所有音符的 offset 将变成相对于整首曲子开头的【绝对时间】
        chordified = score.chordify().flatten()

        # 2. 创建一个新的单轨声部
        mono_part = music21.stream.Part()

        # 3. 保留原谱的节拍和调号信息（如果存在）
        time_sigs = score.flatten().getElementsByClass(music21.meter.TimeSignature)
        if time_sigs:
            mono_part.insert(0, time_sigs[0])
        key_sigs = score.flatten().getElementsByClass(music21.key.KeySignature)
        if key_sigs:
            mono_part.insert(0, key_sigs[0])

        # 4. 遍历展平后的乐谱（直接遍历 chordified，不需要再用 .recurse()）
        for element in chordified:
            if isinstance(element, music21.chord.Chord):
                # 如果是和弦，按音高升序排列，取最顶部的音符（最高音）
                highest_note = element.sortAscending()[-1]

                new_note = music21.note.Note(highest_note.pitch)
                new_note.duration = element.duration
                mono_part.insert(element.offset, new_note)

            elif isinstance(element, music21.note.Note):
                # 如果原本就是单音，直接复制
                new_note = music21.note.Note(element.pitch)
                new_note.duration = element.duration
                mono_part.insert(element.offset, new_note)

            elif isinstance(element, music21.note.Rest):
                # 保持原有的休止符
                mono_part.insert(element.offset, element)

        return mono_part
