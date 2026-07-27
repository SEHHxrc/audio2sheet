# -*- coding: utf-8 -*-
# audio2sheet/backend/app/api/endpoints/audio.py
import os
import uuid
import shutil
import logging
import music21
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.app import config
from backend.app.services.transcriber.basic_pitch_impl import BasicPitchTranscriber
from backend.app.services.separator.factory import SeparatorFactory


logger = logging.getLogger(__name__)
router = APIRouter()

SEPARATION_TASKS = {}
TRANSCRIBER_TASKS = {}


# --- 1. 数据结构验证：自选是否转换成小提琴谱 ---
class TranscribeRequest(BaseModel):
    parent_task_id: str = Field(..., description="关联的音源分离任务 ID")
    track_name: str = Field("piano", description="要转写的音轨名称（如 piano, vocals, bass）")
    adapt_to_violin: bool = Field(False, description="是否自选改编/移植为小提琴谱")  # <-- 核心功能：自选
    onset_threshold: float = Field(0.3, ge=0.0, le=1.0)
    frame_threshold: float = Field(0.25, ge=0.0, le=1.0)
    minimum_note_length: int = Field(100, ge=0)
    auto_transpose: bool = Field(True, description="是否在适配小提琴时进行自动移调")


# =========================================================================
# 【乐理引擎：乐器专属排谱与小提琴改编算法】
# =========================================================================

def format_score_by_instrument(score: music21.stream.Score, track_name: str) -> music21.stream.Score:
    """
    根据音轨名称，自动将 MIDI 格式化为对应乐器的标准五线谱排版
    """
    track_lower = track_name.lower()

    # 1. 钢琴轨 (piano 或 other伴奏轨) -> 自动格式化为钢琴双行大谱表 (Grand Staff)
    if "piano" in track_lower or "other" in track_lower:
        print(f"[乐理排谱] 检测到 [{track_name}] 音轨，正在生成钢琴双行大谱表...")

        right_hand = music21.stream.Part()
        right_hand.id = 'RightHand'
        right_hand.insert(0, music21.clef.TrebleClef())
        right_hand.insert(0, music21.instrument.Piano())

        left_hand = music21.stream.Part()
        left_hand.id = 'LeftHand'
        left_hand.insert(0, music21.clef.BassClef())
        left_hand.insert(0, music21.instrument.Piano())

        # 复制全局拍号和调号
        for el in score.flatten().getElementsByClass([music21.meter.TimeSignature, music21.key.KeySignature]):
            right_hand.insert(el.offset, el)
            left_hand.insert(el.offset, el)

        # 以中央 C (MIDI 60) 为界，拆分音符到左右手
        for element in score.flatten().notesAndRests:
            if isinstance(element, music21.note.Note):
                if element.pitch.midi >= 60:
                    right_hand.insert(element.offset, element)
                else:
                    left_hand.insert(element.offset, element)
            elif isinstance(element, music21.chord.Chord):
                # 拆分和弦的音符
                right_pitches = [p for p in element.pitches if p.midi >= 60]
                left_pitches = [p for p in element.pitches if p.midi < 60]

                if right_pitches:
                    rc = music21.chord.Chord(right_pitches)
                    rc.duration = element.duration
                    right_hand.insert(element.offset, rc)
                if left_pitches:
                    lc = music21.chord.Chord(left_pitches)
                    lc.duration = element.duration
                    left_hand.insert(element.offset, lc)
            elif isinstance(element, music21.note.Rest):
                right_hand.insert(element.offset, element)
                left_hand.insert(element.offset, element)

        grand_score = music21.stream.Score()
        grand_score.insert(0, right_hand)
        grand_score.insert(0, left_hand)
        return grand_score

    # 2. 贝斯轨 (bass) -> 自动应用低音谱表 (Bass Clef)
    elif "bass" in track_lower:
        print(f"[乐理排谱] 检测到 [{track_name}] 音轨，正在生成低音五线谱...")
        part = music21.stream.Part()
        part.insert(0, music21.clef.BassClef())
        part.insert(0, music21.instrument.ElectricBass())

        for el in score.flatten():
            part.insert(el.offset, el)

        bass_score = music21.stream.Score()
        bass_score.insert(0, part)
        return bass_score

    # 3. 其它音轨 (vocals/violin/guitar 等) -> 默认应用标准高音谱表
    else:
        print(f"[乐理排谱] 检测到 [{track_name}] 音轨，正在生成高音五线谱...")
        part = music21.stream.Part()
        part.insert(0, music21.clef.TrebleClef())

        # 根据名字尝试注入对应乐器标记
        if "guitar" in track_lower:
            part.insert(0, music21.instrument.AcousticGuitar())
        elif "vocals" in track_lower:
            part.insert(0, music21.instrument.Vocalist())

        for el in score.flatten():
            part.insert(el.offset, el)

        default_score = music21.stream.Score()
        default_score.insert(0, part)
        return default_score


# =========================================================================
# 【音源分离 (Separation) 异步接口】
# =========================================================================

def run_separation_background(task_id: str, file_path: str, output_dir: str, engine_name: str, model_name: str):
    try:
        # 通过工厂类，动态获取对应的分离器
        separator = SeparatorFactory.get_separator(engine_name=engine_name, model_name=model_name)
        output_tracks = separator.separate(file_path, output_dir)

        relative_tracks = {}
        for stem, abs_path in output_tracks.items():
            file_name = os.path.basename(abs_path)
            relative_tracks[stem] = f"/api/files/download?category=separated&task_id={task_id}&file_name={file_name}"

        SEPARATION_TASKS[task_id] = {
            "status": "completed",
            "progress": 100.0,
            "error": None,
            "output_tracks": relative_tracks
        }
        logger.info(f"[异步分离] 任务 {task_id} 使用模型 {model_name} 成功完成。")
    except Exception as e:
        logger.error(f"[异步分离] 任务 {task_id} 发生异常: {str(e)}")
        SEPARATION_TASKS[task_id] = {
            "status": "failed", "progress": 0.0, "error": str(e), "output_tracks": {}
        }


@router.post("/audio/separate")
def submit_separation(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        engine_name: str = Form("demucs"),
        model_name: str = Form("htdemucs")
):
    """上传音频并提交音源分离异步任务"""
    task_id = f"sep_{uuid.uuid4().hex[:12]}"
    file_extension = os.path.splitext(file.filename)[1]
    input_filename = f"{task_id}_original{file_extension}"
    input_file_path = os.path.join(config.UPLOAD_DIR, input_filename)

    try:
        with open(input_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传音频文件保存失败: {str(e)}")

    task_output_dir = os.path.join(config.SEPARATED_DIR, task_id)

    SEPARATION_TASKS[task_id] = {
        "status": "processing", "progress": 10.0, "error": None, "output_tracks": {}
    }

    background_tasks.add_task(
        run_separation_background,
        task_id,
        input_file_path,
        task_output_dir,
        engine_name,
        model_name
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已在后台启动。"}


@router.get("/tasks/separate/{task_id}")
def get_separation_status(task_id: str):
    """查询音源分离任务的状态"""
    if task_id not in SEPARATION_TASKS:
        raise HTTPException(status_code=404, detail="未找到指定的任务 ID")
    return SEPARATION_TASKS[task_id]


# =========================================================================
# 【转谱与乐器改编 (Transcription) 异步接口】
# =========================================================================

def run_transcription_background(
        task_id: str,
        parent_task_id: str,
        track_name: str,
        adapt_to_violin: bool,
        onset_threshold: float,
        frame_threshold: float,
        minimum_note_length: int,
        auto_transpose: bool
):
    """后台线程：执行 AI 转谱与乐谱适配逻辑"""
    try:
        source_wav = os.path.abspath(os.path.join(config.SEPARATED_DIR, parent_task_id, f"{track_name}.wav"))
        if not os.path.exists(source_wav):
            raise FileNotFoundError(f"未在分离任务中找到指定的 '{track_name}.wav' 轨")

        task_midi_dir = os.path.join(config.MIDI_DIR, task_id)
        os.makedirs(task_midi_dir, exist_ok=True)
        midi_filename = f"{track_name}.midi"
        output_midi_path = os.path.join(task_midi_dir, midi_filename)

        # 1. 运行 AI 音高转录
        transcriber = BasicPitchTranscriber()
        transcriber.transcribe(
            source_wav,
            output_midi_path,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            minimum_note_length=minimum_note_length
        )

        # 2. 读取转录出的 MIDI
        raw_score = music21.converter.parse(output_midi_path)

        xml_filename = "score.musicxml"
        task_adapted_dir = os.path.join(config.ADAPTED_DIR, task_id)
        os.makedirs(task_adapted_dir, exist_ok=True)
        final_xml_path = os.path.join(task_adapted_dir, xml_filename)

        # 3. 核心乐理判定：如果用户【勾选了适配小提琴】，则运行 PianoToViolin 算法
        if adapt_to_violin:
            from backend.app.plugins import registry
            adapter = registry.get_adapter("piano2violin")
            print(f"[异步转谱] 用户勾选改编：正在将 [{track_name}] 轨转写适配为小提琴专属谱...")
            final_score = adapter.adapt(raw_score, auto_transpose=auto_transpose)
        else:
            # 4. 如果没有勾选小提琴，直接将其格式化为该乐器的【标准专属乐谱】（如钢琴双行大谱表）
            final_score = format_score_by_instrument(raw_score, track_name)

        # 5. 写入最终五线谱 XML 格式
        final_score.write('musicxml', fp=final_xml_path)

        output_files = {
            "midi": f"/api/files/download?category=midi&task_id={task_id}&file_name={midi_filename}",
            "musicxml": f"/api/files/download?category=adapted&task_id={task_id}&file_name={xml_filename}"
        }

        TRANSCRIBER_TASKS[task_id] = {
            "status": "completed",
            "progress": 100.0,
            "error": None,
            "output_files": output_files
        }
        logger.info(f"[异步转谱] 任务 {task_id} 转换成功。")

    except Exception as e:
        logger.error(f"[异步转谱] 任务 {task_id} 失败: {str(e)}")
        TRANSCRIBER_TASKS[task_id] = {
            "status": "failed", "progress": 0.0, "error": str(e), "output_files": {}
        }


@router.post("/audio/transcribe")
def submit_transcription(
        payload: TranscribeRequest,
        background_tasks: BackgroundTasks
):
    """提交音高识别与乐器改编异步任务"""
    task_id = f"trans_{uuid.uuid4().hex[:12]}"

    TRANSCRIBER_TASKS[task_id] = {
        "status": "processing",
        "progress": 15.0,
        "error": None,
        "output_files": {}
    }

    background_tasks.add_task(
        run_transcription_background,
        task_id,
        payload.parent_task_id,
        payload.track_name,
        payload.adapt_to_violin,  # <-- 传入自选选项
        payload.onset_threshold,
        payload.frame_threshold,
        payload.minimum_note_length,
        payload.auto_transpose
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "五线谱转换与改编任务已成功提交，正在后台分析音频。"
    }


@router.get("/tasks/transcribe/{task_id}")
def get_transcription_status(task_id: str):
    """查询五线谱转谱与改编任务的状态"""
    if task_id not in TRANSCRIBER_TASKS:
        raise HTTPException(status_code=404, detail="未找到指定的转谱任务 ID")
    return TRANSCRIBER_TASKS[task_id]


# =========================================================================
# 【统一、安全的文件下载接口】
# =========================================================================

@router.get("/files/download")
def download_file(
        category: str = Query(..., description="文件分类，可选 'uploads' | 'separated' | 'midi' | 'adapted'"),
        task_id: str = Query(..., description="关联的任务 ID"),
        file_name: str = Query(..., description="文件名")
):
    """安全文件下载与读取接口。统一支持原曲、WAV 分离轨、中间 MIDI、最终 MusicXML 五线谱的下载。"""
    if category == "uploads":
        base_dir = config.UPLOAD_DIR
        target_file_path = os.path.abspath(os.path.join(base_dir, file_name))

        if file_name.lower().endswith(".mp3"):
            media_type = "audio/mpeg"
        else:
            media_type = "audio/wav"
    else:
        if category == "separated":
            base_dir = config.SEPARATED_DIR
            media_type = "audio/wav"
        elif category == "midi":
            base_dir = config.MIDI_DIR
            media_type = "audio/midi"
        elif category == "adapted":
            base_dir = config.ADAPTED_DIR
            media_type = "application/vnd.recordare.musicxml+xml"
        else:
            raise HTTPException(status_code=400, detail="非法的下载 category 类目")

        target_file_path = os.path.abspath(os.path.join(base_dir, task_id, file_name))

    if not target_file_path.startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=403, detail="越权访问系统资源已被拒绝")

    if not os.path.exists(target_file_path):
        raise HTTPException(status_code=404, detail="请求下载的文件不存在")

    return FileResponse(
        target_file_path,
        media_type=media_type,
        filename=file_name,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )
