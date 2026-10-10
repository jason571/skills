# 参考：讲解稿、视觉类型、TTS、对齐

## lesson.json

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | 是 | 课题 |
| `question` | 是 | 学生原问题 |
| `subject` | 是 | 数学 / 语文 / 英语 / 科学 等 |
| `grade` | 是 | 必须是 `小学一年级` … `小学六年级` |
| `language` | 否 | 默认 `zh-CN` |
| `style` | 否 | `background` `primary` `accent` `text` 颜色 |
| `segments` | 是 | 分镜数组 |

### segment

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | `s01` 起 |
| `role` | 否 | `hook` `concept` `demo` `example` `practice` `summary`；默认 `demo` |
| `narration` | 是 | TTS 原文 |
| `visual` | 是 | 见下节 |

## visual.type

### `scene`（图解动画）

支持多个独立图形、命名分组及移动、旋转、缩放、路径、高亮、显隐动作。
同一对象跨口播段可延续最终位置和状态；标题/说明不随图形缩放。
格式、构图和跨段示例见 [animation.md](animation.md)，不需要把此处的所有静态组件一起加载。
数据契约和位置计算在 `scripts/scene_contract.py`，MCP 的实时 Schema 与任务快照复用这同一份契约。
图形实际渲染在 `scripts/scene_visual.py`；不解释或执行调用方代码。

渲染器在 `scripts/manim_lesson.py`。时间轴到了就切下一段，不要在 visual 里写估计秒数。模型列表的 TTS 配置是唯一声音来源；旧稿里的 `voice`/`speech_rate` 不会被转发，也不代表已经改变声音。

### `title`

```json
{ "type": "title", "title": "示例题：还剩多少本书", "subtitle": "书架上有 8 本书，小明拿走 3 本。书架上还剩多少本书？" }
```

开场用完整题干作副标题，而非只填年级或欢迎语。长题目拆成连续题目页；后续解题页再展开答案。

### `talking_text`

展示口播，有词级时间戳时按词高亮。长文字自动换行；教学视频更适合用短句和关键字。MCP 中 `visual` 必填。

```json
{ "type": "talking_text", "heading": "先记住" }
```

### `bullets`

```json
{ "type": "bullets", "heading": "通分三步", "items": ["找共同的分母", "改写分子", "再相加"] }
```

### `formula`

```json
{ "type": "formula", "heading": "通分", "lines": ["1/2 = 3/6", "1/3 = 2/6", "3/6 + 2/6 = 5/6"] }
```

### `steps`

```json
{ "type": "steps", "heading": "做法", "items": ["通分", "分子相加", "能约分就约分"] }
```

### `fraction_pies`

```json
{
  "type": "fraction_pies",
  "heading": "1/2 + 1/3",
  "items": [
    { "n": 1, "d": 2, "label": "1/2" },
    { "n": 1, "d": 3, "label": "1/3" }
  ]
}
```

### `number_line`

```json
{ "type": "number_line", "heading": "数轴", "min": 0, "max": 6, "step": 1, "marks": [ { "value": 3, "label": "一半" } ] }
```

### `compare`

```json
{
  "type": "compare",
  "heading": "谁更大",
  "left": { "title": "1/2", "body": "一块披萨的一半" },
  "right": { "title": "1/3", "body": "一块披萨的三分之一" }
}
```

### `geometry`

```json
{ "type": "geometry", "shape": "triangle|circle|rectangle", "caption": "直角三角形", "labels": ["A", "B", "C"] }
```

三角形和长方形使用实际顶点标签；圆没有顶点，最多四个标签依次放在上、右、下、左侧边界外。

### `quiz`

```json
{ "type": "quiz", "question": "1/2 + 1/4 = ?", "answer": "3/4", "reveal_at": 0.55 }
```

`reveal_at` 是本段时长比例（0–1），只用于用户明确需要的定时揭晓，不是逐字同步。讲解中需要答案随对应口播出现时，把问题和答案拆成两个 segment。

## 音频绑定

### 在 ExoHarness 中使用已登记 MCP

1. `prepare_lesson(lesson)` 保存草稿并校验。`needs_repair` 时按 [draft-repair.md](draft-repair.md) 修复局部；只有 `prepared` 才返回 `lesson_id` 和 `speech_requests`。
2. 当前 TTS 工具执行每段 `arguments`（含 `artifact_visibility: "internal"`）。新版返回 `audio.url`，渲染时原样绑定到 `artifact_url`；旧版实际返回附件 ID 时，原样绑定到 `attachment_id`。该标记只影响对话展示，文件和执行证据仍保留，TTS 文本保持不变。
3. `submit_lesson_render` 使用以下绑定，不需要模型计算摘要或访问服务器文件：

```json
{"lesson_id":"prepare_lesson 返回的 ID","audio":[{"segment_id":"s01","artifact_url":"该段 TTS 返回的完整 audio.url"}]}
```

失败任务默认仍使用自己的渲染组件快照。管理员发布组件修复后，若工具明确提示有新渲染器，
可在原提交上同时设置 `retry_failed=true` 和 `refresh_renderer=true`，显式采用修复版。
服务保留旧代码、原请求、失败状态及版本变更记录；题目、计划、配音和 `lesson_id` 不变，不重新调用 TTS。
普通查询、未显式刷新、运行中或已完成的任务不会自动换版本。

下列本地文件清单由 MCP 创建，仅管理员调试独立执行器时需要阅读。

`tts_requests.json` 是本地生成的调用清单，`arguments` 交给当前启用 TTS 的真实工具。
模型不计算 SHA-256。保留清单中脚本生成的 `narration_sha256`，与该调用的实际产物绑定：

```json
{
  "schema_version": 1,
  "segments": [{
    "id": "s01",
    "narration_sha256": "从该段 tts_requests 复制的 SHA-256",
    "invocation_id": "真实调用 ID",
    "artifact": {
      "id": "ToolResult 返回的 Artifact ID",
      "local_path": "downloaded/s01.mp3",
      "sha256": "ToolResult 返回的文件 SHA-256"
    }
  }]
}
```

`local_path` 相对 manifest 所在目录，或为执行器授权可读的绝对路径。
不接受 URL 伪装文件路径；下载/鉴权由已授权的产物传输能力完成。
不能把整个服务器文件系统挂给不可信 Skill，不能让模型选任意宿主路径。
必填：完整且唯一的 id、文本摘要、音频路径和真实文件摘要；Artifact/invocation ID 可选但建议保留。
manifest 是执行数据，不需要把完整内容在每次模型调用里重复加载。

如果服务真实返回词级时间戳，可在段记录中添加：

```json
"words": [{"text": "小朋友", "start_sec": 0.0, "end_sec": 0.46}]
```

明确为本段音频内的秒数；`0` 是有效时间。拒绝 NaN、乱序和越界。
服务没有词戳就省略，脚本不会按字数伪造。

## 时间轴和校验

先解码每段为 48kHz 单声道 PCM16 WAV，再读取整数采样数。
`fps` 支持 15、24、25、30、50、60（默认 30），每帧对应整数采样数。
每段的音频末尾最多补不足一帧的静音；画面也占用同样的整数帧。
累计 `start_sample` 与 `start_frame` 完全来自同一时钟，不会逐段累计浮点舍入误差。
MP3 只作原始输入，不直接 `-c copy` 拼接；输出口播 WAV，最终视频 AAC。

`timeline.json` 由脚本生成，包含 `schema_version=2`、`fps`、`sample_rate`、
`total_samples`、`total_frames`，以及每段的 `start/end_frame`、`samples`、
`slot_samples`、`silence_samples`、`start/end/speech_end` 和文件摘要。
SRT 以真实口播结束点结束，不延伸到补齐静音。

Manim 使用同一个 fps，渲染后必须校验实际帧数等于时间轴帧数。
合成前验证音频采样时长；合成后分别验证音视频流起点/时长和帧数。
允许的封装尾差最多为一帧或一个 AAC 编码包（取较大者，再加 1ms 测量余量）。
超过即失败，不用长冻帧、拉伸或 `-shortest` 掩盖问题。

## 环境与 ExoHarness 接入

- 渲染环境：Python 3.11+、Manim 0.20.1、Pydantic 2.13.5、ffmpeg/ffprobe、Pango/Cairo 和中文字体。
  `scripts/requirements.txt` 固定 Manim 版本；Python 的原生依赖应在独立 Conda/OCI 环境提前准备。
- Linux 默认 `Noto Sans CJK SC`，Windows `Microsoft YaHei`，macOS `PingFang SC`。
  `check_env.py` 检查字体是否实际可用，不只打印建议名称。
- 依赖安装须管理员单独确认；导入 Skill 和正式渲染期间不自动 pip/conda install。
- 配套独立服务为 `lesson-renderer`，源码在 ExoHarness 的 `examples/lesson-renderer-mcp`。
  管理员构建独立 OCI 运行时、启动并登记 MCP 后使用；单独导入 Skill 不会隐式部署它。
  控制服务只按附件 ID 从管理员指定地址读取文件；Manim/FFmpeg 工作进程禁止联网，
  没有模型 Key、登录 Cookie、数据库或宿主 Docker Socket。
- 现有 TTS 模型工具在 Agent 中调用；渲染器不另外读取模型配置、Secret 或调用供应商。
  `render.py` 输出的 `files` 是本地文件交接清单，包含 MIME、SHA-256 和字节数，
  由独立 MCP 校验后发布为标准媒体结果，通过部署配置的统一媒体入口在 Chat 播放。

## 新增的参数化图形

### `table`

```json
{"type":"table","heading":"验算","columns":["动物","只数","脚数"],"rows":[["鸡","3","6"],["兔","2","8"],["合计","5","14"]]}
```

### `bar_model`

各行共享长度比例尺，`value` 是实际数量；`label` 是显示文字，不把不同数量画成相同长度。

```json
{"type":"bar_model","heading":"数量关系","rows":[{"label":"原来","parts":[{"value":10,"label":"10"}]},{"label":"现在","parts":[{"value":10,"label":"原有10"},{"value":4,"label":"增加4"}]}]}
```

## 本地验证

```bash
python scripts/check_env.py
python -B -m unittest discover -s scripts/tests -v
python -B scripts/tests/smoke_render.py --out /tmp/study-lesson-smoke
```

回归使用合成测试音频，不调用真实 TTS/LLM，不宣称完成线上模型调用。
Smoke 使用真实 Manim 和 FFmpeg，生成包含不同画面的短片并检查段落边界和最终流时长。

实现参考：[Manim Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)、
[FFmpeg](https://ffmpeg.org/ffmpeg.html)。
