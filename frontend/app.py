# -*- coding: utf-8 -*-
# audio2sheet/frontend/app.py
import streamlit as st
import requests
import time
import streamlit.components.v1 as components

# 1. 配置后端 API 服务地址
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="智能音频转谱与乐谱改编系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎼 智能音频转五线谱与乐曲改编系统")
st.markdown("通过 Meta Demucs AI 拆分音源，并基于 Spotify Basic Pitch 音符识别与乐理引擎改编出规范的五线谱。")

# 使用 Session State 保存状态
if "sep_task_id" not in st.session_state:
    st.session_state.sep_task_id = None
if "separated_tracks" not in st.session_state:
    st.session_state.separated_tracks = {}
if "transcription_results" not in st.session_state:
    st.session_state.transcription_results = {}

# =========================================================================
# 【板块 A：侧边栏 - 动态渲染技术配置参数】
# =========================================================================
st.sidebar.header("🛠️ 乐理与算法配置")

# 自选是否改编成小提琴谱。提供一个直观的 Switch / Checkbox
st.sidebar.subheader("🎻 小提琴谱移植选项")
adapt_to_violin = st.sidebar.checkbox(
    "将该音轨改编/移植为小提琴五线谱",
    value=False,
    help="【勾选】：将音频旋律自动限制音域并移调为单声部小提琴谱。 \n【不勾选】：默认直接转写为对应乐器的专属五线谱（如：钢琴轨直接转为双行大谱表，贝斯轨自动应用低音谱号）。"
)

# 2. 音源分离模型选择
st.sidebar.markdown("---")
st.sidebar.subheader("🔊 音源分离场景配置")

# 设计“场景导向”的映射字典，直观、清晰
scenario_options = {
    "🎧 均衡合奏分离 (HTDemucs - 推荐)": {
        "engine": "demucs", "model": "htdemucs",
        "desc": "最均衡的 4 声部（人声、钢琴、鼓、贝斯）分离，适合大多数乐曲。"
    },
    "🎹 古典钢琴与吉他专门提取 (HTDemucs 6S)": {
        "engine": "demucs", "model": "htdemucs_6s",
        "desc": "高精度 6 声部模型，能将钢琴、吉他从复杂的合奏中彻底剥离。"
    },
    "⚡ 极速伴奏提取 - 无显卡推荐 (Spleeter 5S)": {
        "engine": "spleeter", "model": "5stems",
        "desc": "速度极快的 5 声部（人声、钢琴、吉他/其它、鼓、贝斯）分离，对 CPU 极度友好。"
    },
    "🎤 极致纯净人声提取 (Spleeter 2S)": {
        "engine": "spleeter", "model": "2stems",
        "desc": "极速剥离人声与所有伴奏，适合提取单纯的歌唱旋律线。"
    }
}

selected_scenario = st.sidebar.selectbox("选择您的音源分离场景：", list(scenario_options.keys()))
config_payload = scenario_options[selected_scenario]

# 提取对应的引擎名和模型名，提交时直接发送
selected_engine_name = config_payload["engine"]
selected_model_name = config_payload["model"]

# 在下方显示当前场景的提示
st.sidebar.info(config_payload["desc"])

# 3. 动态参数 Schema 渲染
st.sidebar.markdown("---")
st.sidebar.subheader("AI 敏感度与量化参数")

try:
    schema_res = requests.get(f"{BACKEND_URL}/api/transcribe/default-settings?lang=zh").json()
    params_schema = schema_res["data"]
except Exception:
    st.sidebar.error("未能加载参数 Schema 配置文件")
    st.stop()

submitted_params = {}
for param in params_schema:
    key = param["key"]
    label = param["display_name"]
    ui_type = param["ui_type"]
    default_val = param["value"]

    if ui_type == "slider":
        val = st.sidebar.slider(
            label=label,
            min_value=param["min"],
            max_value=param["max"],
            value=default_val,
            step=param["step"]
        )
        submitted_params[key] = val
    elif ui_type == "input_number":
        val = st.sidebar.number_input(
            label=label,
            min_value=param["min"],
            max_value=param["max"],
            value=default_val,
            step=param["step"]
        )
        submitted_params[key] = val
    elif ui_type == "switch":
        # 如果是 auto_transpose 选项，我们只在用户勾选了 adapt_to_violin 时才让其生效
        if key == "auto_transpose":
            val = st.sidebar.checkbox(label=label, value=default_val, disabled=not adapt_to_violin)
        else:
            val = st.sidebar.checkbox(label=label, value=default_val)
        submitted_params[key] = val

# =========================================================================
# 【板块 B：主界面第一步 - 混音上传与异步分离】
# =========================================================================
st.header("混音音频上传与声部拆分")

uploaded_file = st.file_uploader("请上传您想要拆分转谱的合奏音频文件（支持 mp3, wav）", type=["wav", "mp3"])

col1, col2 = st.columns([1, 4])
with col1:
    btn_separate = st.button("🚀 开始音源分离", disabled=(uploaded_file is None))

if btn_separate and uploaded_file:
    # 状态复位
    st.session_state.transcription_results = {}

    with st.spinner("正在上传音频并提交后台分离..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/audio/separate",
                files=files,
                data={
                    "engine_name": selected_engine_name,
                    "model_name": selected_model_name
                }
            )
            task_id = res.json()["task_id"]
            st.session_state.sep_task_id = task_id
            st.info(f"分离任务已成功提交！任务 ID: {task_id}")
        except Exception as e:
            st.error(f"任务提交failed: {e}")
            st.stop()

    progress_bar = st.progress(10)
    status_text = st.empty()

    while True:
        try:
            status_res = requests.get(f"{BACKEND_URL}/api/tasks/separate/{st.session_state.sep_task_id}").json()
            status = status_res["status"]

            if status == "processing":
                status_text.text(f"AI 正在使用 [{selected_model_name}] 模型拆分音轨中...")
                progress_bar.progress(50)
            elif status == "completed":
                status_text.text("音源分离完成！")
                progress_bar.progress(100)
                st.session_state.separated_tracks = status_res["output_tracks"]
                st.success(f"声部拆分完毕，已使用模型 [{selected_model_name}] 为您成功提取并渲染了所有分离音轨！")
                break
            elif status == "failed":
                st.error(f"音源分离失败！错误详情: {status_res['error']}")
                break
        except Exception as e:
            st.error(f"轮询状态出错: {e}")
            break
        time.sleep(2)

# 如果分离成功，展示分离后的音轨，供用户点击播放
if st.session_state.separated_tracks:
    st.markdown("##### 🎧 分离音轨在线试听与选择：")

    stems = list(st.session_state.separated_tracks.keys())
    track_cols = st.columns(len(stems))

    selected_track = st.radio("请选择一个您想要进行五线谱转录的音轨：", stems, index=0)

    for i, stem in enumerate(stems):
        with track_cols[i]:
            st.markdown(f"**音轨: {stem.upper()}**")
            track_url = f"{BACKEND_URL}{st.session_state.separated_tracks[stem]}"
            st.audio(track_url, format="audio/wav")

# =========================================================================
# 【板块 C： Fountain 音乐喷泉播放器】
# =========================================================================
if st.session_state.separated_tracks:
    st.markdown("---")
    st.header("⛲ 创意空间：多音轨虚拟“音乐喷泉”播放器")
    st.markdown("这里是您的乐学音乐喷泉！切换音轨并播放，观察不同声部的物理振动是如何在水花中起舞的。")

    fountain_tracks = {
        "原谱混音 (Original Mix)": f"{BACKEND_URL}/api/files/download?category=uploads&task_id={st.session_state.sep_task_id}&file_name={st.session_state.sep_task_id}_original.wav",
    }
    for stem in stems:
        fountain_tracks[f"纯【{stem.upper()}】声部轨道"] = f"{BACKEND_URL}{st.session_state.separated_tracks[stem]}"

    fountain_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                background-color: #0d1117;
                color: white;
                font-family: -apple-system, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                overflow: hidden;
            }}
            #controls {{
                margin: 10px 0;
                display: flex;
                gap: 15px;
                align-items: center;
                z-index: 10;
            }}
            select, button {{
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                cursor: pointer;
                font-size: 14px;
            }}
            select:focus, button:hover {{
                border-color: #58a6ff;
                outline: none;
            }}
            canvas {{
                border: 1px solid #30363d;
                background: linear-gradient(to bottom, #07090e, #0e1626);
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            }}
        </style>
    </head>
    <body>
        <div id="controls">
            <label for="track-select">选择注入喷泉的音轨: </label>
            <select id="track-select">
                {"".join([f'<option value="{url}">{name}</option>' for name, url in fountain_tracks.items()])}
            </select>
            <button id="play-btn">▶ 启动喷泉</button>
            <span id="playing-status" style="font-size: 13px; color: #8b949e;">已暂停</span>
        </div>

        <canvas id="fountain-canvas" width="1000" height="400"></canvas>
        <audio id="fountain-audio" crossOrigin="anonymous"></audio>

        <script>
            const audio = document.getElementById("fountain-audio");
            const select = document.getElementById("track-select");
            const playBtn = document.getElementById("play-btn");
            const statusText = document.getElementById("playing-status");
            const canvas = document.getElementById("fountain-canvas");
            const ctx = canvas.getContext("2d");

            audio.src = select.value;

            let audioCtx = null;
            let analyser = null;
            let dataArray = null;
            let source = null;

            const particles = [];
            const GRAVITY = 0.18;

            audio.addEventListener("error", (e) => {{
                console.error("Audio error:", e);
                statusText.innerText = "❌ 浏览器跨域拦截：请检查后端 CORS 或使用标准 WAV";
                statusText.style.color = "#ff7b72";
            }});

            audio.addEventListener("ended", () => {{
                playBtn.innerText = "▶ 启动喷泉";
                statusText.innerText = "已暂停";
                statusText.style.color = "#8b949e";
            }});

            function initAudio() {{
                if (audioCtx) return;
                try {{
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 128;
                    const bufferLength = analyser.frequencyBinCount;
                    dataArray = new Uint8Array(bufferLength);

                    source = audioCtx.createMediaElementSource(audio);
                    source.connect(analyser);
                    analyser.connect(audioCtx.destination);
                }} catch (err) {{
                    console.error("AudioContext init failed:", err);
                }}
            }}

            select.addEventListener("change", () => {{
                const wasPlaying = !audio.paused;
                audio.src = select.value;
                audio.load();
                if (wasPlaying) {{
                    audio.play().catch(err => console.error("Play failed on change:", err));
                }}
            }});

            playBtn.addEventListener("click", () => {{
                initAudio();
                if (audioCtx && audioCtx.state === 'suspended') {{
                    audioCtx.resume();
                }}

                if (audio.paused) {{
                    audio.play()
                        .then(() => {{
                            playBtn.innerText = "⏸ 暂停喷泉";
                            statusText.innerText = "⛲ 音乐喷泉正在舞动中...";
                            statusText.style.color = "#8b949e";
                        }})
                        .catch(err => {{
                            console.error("Play failed:", err);
                            statusText.innerText = "❌ 启动失败：请检查后端服务是否畅通。";
                            statusText.style.color = "#ff7b72";
                        }});
                }} else {{
                    audio.pause();
                    playBtn.innerText = "▶ 启动喷泉";
                    statusText.innerText = "已暂停";
                    statusText.style.color = "#8b949e";
                }}
            }});

            class WaterDrop {{
                constructor(x, y, vx, vy, size, color) {{
                    this.x = x;
                    this.y = y;
                    this.vx = vx;
                    this.vy = vy;
                    this.size = size;
                    this.color = color;
                    this.alpha = 1.0;
                }}
                update() {{
                    this.x += this.vx;
                    this.y += this.vy;
                    this.vy += GRAVITY;
                    this.alpha -= 0.02;
                }}
                draw(c) {{
                    c.save();
                    c.globalAlpha = Math.max(0, this.alpha);
                    c.beginPath();
                    c.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                    c.fillStyle = this.color;
                    c.fill();
                    c.restore();
                }}
            }}

            function render() {{
                requestAnimationFrame(render);
                ctx.fillStyle = "rgba(7, 9, 14, 0.25)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.fillStyle = "rgba(0, 119, 255, 0.05)";
                ctx.fillRect(0, canvas.height - 20, canvas.width, 20);

                const hasMusic = analyser && dataArray && !audio.paused;
                if (hasMusic) {{
                    analyser.getByteFrequencyData(dataArray);
                }}

                const barWidth = 14;
                const gap = 8;
                const bottomY = canvas.height - 20;

                const numPillars = 20;
                for (let i = 0; i < numPillars; i++) {{
                    let val = hasMusic ? dataArray[i] : (Math.sin(Date.now() * 0.003 + i) * 10 + 15);
                    const height = (val / 255) * (canvas.height - 100);

                    const gradient = ctx.createLinearGradient(0, bottomY, 0, bottomY - height);
                    gradient.addColorStop(0, "rgba(0, 50, 200, 0.7)");
                    gradient.addColorStop(0.6, "rgba(0, 191, 255, 0.8)");
                    gradient.addColorStop(1, "rgba(230, 248, 255, 0.95)");

                    const leftX = canvas.width / 2 - (i * (barWidth + gap)) - 10;
                    const rightX = canvas.width / 2 + (i * (barWidth + gap)) + 10;

                    drawWaterPillar(leftX, bottomY, barWidth, height, gradient);
                    drawWaterPillar(rightX, bottomY, barWidth, height, gradient);

                    if (val > 100 && Math.random() < 0.45) {{
                        // 🌟 传统的 JS 拼接字符串（完全不含大括号），完美避开 Python F-String 解释器误判
                        const splashColor = "hsla(" + (200 + Math.random() * 20) + ", 90%, 85%, 0.8)";
                        spawnParticles(leftX + barWidth/2, bottomY - height, splashColor);
                        spawnParticles(rightX + barWidth/2, bottomY - height, splashColor);
                    }}
                }}

                for (let i = particles.length - 1; i >= 0; i--) {{
                    const p = particles[i];
                    p.update();
                    p.draw(ctx);
                    if (p.alpha <= 0 || p.y > canvas.height) {{
                        particles.splice(i, 1);
                    }}
                }}
            }}

            function drawWaterPillar(x, y, w, h, color) {{
                ctx.save();
                ctx.fillStyle = color;

                if (ctx.roundRect) {{
                    ctx.beginPath();
                    ctx.roundRect(x, y - h, w, h, [w/2, w/2, 0, 0]);
                    ctx.fill();
                }} else {{
                    ctx.fillRect(x, y - h, w, h);
                }}

                ctx.shadowBlur = 12;
                ctx.shadowColor = "rgba(135, 206, 250, 0.6)";
                ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                ctx.beginPath();
                ctx.arc(x + w/2, y - h, w/2 + 2, 0, Math.PI, true);
                ctx.fill();
                ctx.restore();
            }}

            function spawnParticles(x, y, color) {{
                const count = Math.floor(Math.random() * 3) + 3;
                for (let k = 0; k < count; k++) {{
                    const vx = (Math.random() - 0.5) * 4.5;
                    const vy = -Math.random() * 4 - 2;
                    const size = Math.random() * 3 + 1.5;
                    particles.push(new WaterDrop(x, y, vx, vy, size, color));
                }}
            }}

            render();
        </script>
    </body>
    </html>
    """
    components.html(fountain_html, height=470, scrolling=False)

# =========================================================================
# 【板块 D：主界面第二步 - AI 转谱与各声部乐器改编（支持多声部独立并行转换）】
# =========================================================================
if st.session_state.separated_tracks:
    st.markdown("---")
    st.header("选择目标声部并进行 AI 转谱与改编")

    # 根据用户勾选自动变更按钮名称，提升可读性
    btn_text = "🎻 开始一键转谱并改编为小提琴" if adapt_to_violin else "📝 开始生成该音轨的专属五线谱"
    btn_transcribe = st.button(btn_text)

    if btn_transcribe:
        with st.spinner(f"正在转写 [{selected_track}] 声部的音高事件并组织排谱..."):
            # 将 plugin_id 更换为自选的 adapt_to_violin 布尔值
            payload = {
                "parent_task_id": st.session_state.sep_task_id,
                "track_name": selected_track,
                "adapt_to_violin": adapt_to_violin,  # 传入用户的自选值（True / False）
                **submitted_params
            }
            try:
                res = requests.post(f"{BACKEND_URL}/api/audio/transcribe", json=payload)
                trans_task_id = res.json()["task_id"]
            except Exception as e:
                st.error(f"提交转谱任务失败: {e}")
                st.stop()

        trans_progress = st.progress(15)
        trans_status_text = st.empty()

        while True:
            try:
                status_res = requests.get(f"{BACKEND_URL}/api/tasks/transcribe/{trans_task_id}").json()
                status = status_res["status"]

                if status == "processing":
                    trans_status_text.text("AI 正在解析音符并进行音域八度适配和节奏量化，请稍候...")
                    trans_progress.progress(60)
                elif status == "completed":
                    trans_status_text.text("该声部转换和排谱成功！")
                    trans_progress.progress(100)

                    # 写入对应的页签字典
                    xml_relative_url = status_res["output_files"]["musicxml"]
                    st.session_state.transcription_results[selected_track] = f"{BACKEND_URL}{xml_relative_url}"

                    label_msg = "小提琴改编谱" if adapt_to_violin else "专属标准五线谱"
                    st.success(f"音轨 [{selected_track.upper()}] 的{label_msg}已成功生成！可在下方对应页签中预览。")
                    break
                elif status == "failed":
                    st.error(f"转谱改编失败！错误详情: {status_res['error']}")
                    break
            except Exception as e:
                st.error(f"查询转谱进度出错: {e}")
                break
            time.sleep(2)

# =========================================================================
# 【板块 E：高光时刻 - 多声部五线谱独立并行渲染页签（Tabs）】
# =========================================================================
if st.session_state.transcription_results:
    st.markdown("---")
    st.subheader("🎼 已生成的改编五线谱预览（OSMD 矢量动态页签组件）")

    transcribed_tracks = list(st.session_state.transcription_results.keys())

    # 动态渲染多音轨 Tab，互不影响
    tabs = st.tabs([f"🎵 {track.upper()} 轨道乐谱" for track in transcribed_tracks])

    for idx, track in enumerate(transcribed_tracks):
        with tabs[idx]:
            xml_url = st.session_state.transcription_results[track]

            # 使用带有 track 命名空间后缀的容器，防止多 Tabs 间 Canvas 混乱
            osmd_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.8/build/opensheetmusicdisplay.min.js"></script>
            </head>
            <body style="margin: 0; padding: 10px; background-color: #fcfcfc; font-family: sans-serif;">
                <div id="osmd-container-{track}" style="width: 100%;"></div>
                <script>
                    const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay("osmd-container-{track}", {{
                        autoResize: true,
                        backend: "svg",
                        drawTitle: true,
                        drawSubtitle: true
                    }});

                    fetch("{xml_url}")
                        .then(response => response.text())
                        .then(xmlText => {{
                            return osmd.load(xmlText);
                        }})
                        .then(() => {{
                            osmd.render();
                        }})
                        .catch(err => {{
                            document.getElementById("osmd-container-{track}").innerHTML = "<p style='color:red;'>五线谱渲染器加载失败: " + err + "</p>";
                        }});
                </script>
            </body>
            </html>
            """

            components.html(osmd_html, height=750, scrolling=True)
            st.markdown(f"[📥 下载该声部（{track.upper()} 轨）的 MusicXML 格式五线谱]({xml_url})")
