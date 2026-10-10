---
name: yongjia-product-promo
description: "制作最长 3 分钟的永嘉宣传片，超过 3 分钟须在创作或生成前拒绝。对象随用户指定（文旅、农产品、服装、工艺、工业等）；按 MiniMax H3 写连续分段视频，配中文解说，交付完整 MP4。Use for Yongjia promotional videos, not unrelated documents or an uploaded-song MV."
---

# 永嘉宣传片

默认 **2 分钟**、16:9、512p、普通话解说 MP4。只交付成片。用户只要脚本则停在计划；明确静音则不做 TTS。

## Required capabilities

- `minimax-h3-mcp`：只读获取视频模型和实时默认参数；视频生成由媒体工作流代为提交。
- `media-workflow`：一次登记完整计划，并负责分段生成和最终合成。
- 已启用且获助理授权的 TTS 模型工具：为各段生成解说音频；明确静音时不调用。

**不要读取本技能的其他文件。** 创作计划前，用当前宿主的工具目录确认只读视频模型查询、计划保存、TTS 配音和最终渲染能力均已获授权；只需要查到名称，不必提前加载全部 Schema。原生宿主使用 `search_capabilities` 的 `kind: "tool"` 查询，复制返回的 `name`，不要凭服务名称拼接调用名。未找到时只再列一次已授权工具；确实缺少则停止并说明具体缺项。不要 `probe_media` / `submit_video_generation` / `generate_video`，不要调用 generate-video-prompts 或 h3-prompt-writing。`generate_video` 即使只传「占位」也是一次真实视频生成，绝不能拿它试探默认时长、Schema 或服务状态。缺文件不要换名重试，不要编造路径或字段。

## 禁止瞎猜

- 段长只信视频生成 Schema 的 `duration_seconds.default`、只读 `list_video_models` 返回的 `defaults.duration_seconds`，或 `prepare_narrated_video` 返回的 `clip_duration_seconds`。不要猜 15 或 30；若当前上下文没有默认值，先调用一次只读模型查询工具，绝不能调用生成工具来探测。
- 用户未明确指定首帧时，不要填 `first_frame_url`。仅说“参考图片”不是首帧指令；持续参考只能使用实时工具 Schema 明确支持的参考图字段，不要用 `first_frame_url` 冒充。只用当前用户附件元数据中实际返回的图片 URL，不要需要聊天登录的 `/v1/run-artifacts/`。
- `plan` 每段只能有技能列出的键。不要加 `segment_id_note` 等额外字段。
- 不要编认证、销量、票价、疗效、不存在的场所。用户没给的数字不要编。

## 对象

以用户这句话为准。用对永嘉的已有知识写分镜和解说，只取与本次主题相关的风貌、场所和工序。不要预装某一种成片，不要全县特产集锦。用户给的名称、素材、口径优先。不编认证、销量、票价、疗效。

## 时长

成片最长 3 分钟。超过 180 秒：写提示词或提交前停止，回复「宣传视频最长支持 3 分钟，请将时长调整到 180 秒以内。」

段长**不要写死 15 或 30 秒**。以视频生成工具实时 Schema 的 `duration_seconds.default` 为准；未加载该 Schema 时，调用一次目录中实际登记的只读 `list_video_models` 取 `defaults.duration_seconds`。`prepare_narrated_video` 成功时也会返回 `clip_duration_seconds`。取得真实默认值后再一次写完全片，按该默认值切段：

- 余量 ≤ 默认值的 40%：并入上一段（例如默认 15s 时 6s 并入，末段 21s；默认 30s 时 12s 并入，末段 42s，且不超过 Schema maximum）。
- 余量更大：拆成「默认时长 + 余量」两段（例如 15+7 或 30+13）。

未说时长则 120 秒。明确更短则按其秒数。全片是连续多段，不是单次 120 秒。一次 `prepare_narrated_video` 交全片。

**先确定全部时间窗口，再写剧情。** 在同一次创作中计算 `q = floor(T / D)`、`r = T - q × D`：`T` 为全片秒数，`D` 为服务实际默认秒数。先列 `q` 个 `D` 秒窗口；`r=0` 时没有尾段，`r>0` 时按上面的尾段规则处理（总长小于 `D` 时只有一个 `T` 秒窗口，且须在服务支持范围内）。窗口数 `N` 就是必须提交的段数，不由景点数、章节数或写作长度决定。

例如，全片 120 秒且服务返回默认 15 秒时，窗口是 `[15,15,15,15,15,15,15,15]`，必须写齐 `segment-001` 至 `segment-008`；默认 30 秒时是四个 30 秒窗口。这些是计算示例，不是固定默认值。可把一个剧情章节分配给多个连续窗口，但不能写完六个景点就漏掉其余窗口。

先为 `N` 个窗口逐一分配剧情起点、推进和结尾，再在一次调用中填写每个窗口的四镜提示词和对应解说。提交前核对 `len(segments)==N`、段 ID 无遗漏、`sum(segments[].duration_seconds)==T`，以及每段内外两处 `duration_seconds` 相等。缺少窗口时补齐缺段再提交，不提交半份计划，也不把全片总时长改短来掩盖漏段。这个核对无需增加模型请求或执行脚本。

## 章节与分镜

一次写完全片。先按用户主题确定一条主线与起点、发展、收束；可以是游览体验、产品工序或人物行动，不强加人物或固定路线。每段推进一个新体验、工序或情绪变化，不重复开场或用空泛风景堆满时长。风格全片一份，用户指定的剧情、身份、服装、色彩与素材优先。

**段长是执行窗口，不是剧情重启点。** 在同一次创作中逐对检查「上一段 Shot 4 → 下一段 Shot 1」：

- 末镜留下具体可接续的主体、位置、动作、光线和镜头方向；下一段首镜明确沿用这些可见状态，并从该动作继续。不要一边写参考上一帧，一边把首镜直接换成另一处景点、另一人物或另一时段。没有人物时可用水流、道路、产品或工序串联，不凭空添加主人公。
- 场所变化安排在接续首镜之后：写清可见移动或有意的剪辑过渡及新场景的建立镜头。新地点若不能从原画面自然显露，就明确切镜，不能让原景点或人物变形成新地点；不要假装跨段首尾是相同画面。
- 非线性叙事服从用户明确要求；普通游览或工序按合理时间推进。夜景后回到清晨等时间跳跃必须有可见的转场或新一天线索，不因换段反复日出、黄昏、夜晚。固定主体的身份、服装、材质和色彩不能随段漂移。
- 收尾服务下一段，不要求每段都静止、渐黑或像完整结局。最后一段才完成全片收束；中间段保留能继续的动作或视线。解说跟随该段真实画面，避免画面在制作、解说却已到消费结果，或每段重说口号。

这些检查直接体现在既有 H3 四镜正文中，**不新增计划字段、独立剧情表或第二份完整提示词**。提交前只在同一次创作中改冲突的镜头及相邻衔接，不额外调用模型自评或逐段重写；计划持久化并开始渲染后，不因审美调整重建计划或重新生成成功片段。

每段恰好 4 镜，切点按**该段实际秒数**均分，不要写死 00:07 / 00:15 / 00:23。运镜写完整句子，不要 `[push]`。

用户上传了图片并要求参考时，先通过已授权的读图能力确认可见的人物、场景、构图与光线，让剧情和分镜与这些事实相容。只有用户明确要求把图片作为开场首帧时，第一段才填 `first_frame_url`，Shot 1 从该静帧开始。普通“参考图片”需要持续参考字段；如果实时工具没有该能力，生成前明确说明，不要擅自改成首帧。没有参考图片时，按照用户文字描述创作剧情。

## H3 与解说

`prompt_mode: "h3"`，`audio_enabled: false`。首段默认 T2VA（不要填 `first_frame_url`）。仅当用户明确指定图片为首帧时，首段使用 I2VA 并增加 `first_frame_url`。单纯视觉参考走实时工具声明的持续参考模式，不得伪装为 I2VA。后续段的段间首帧由服务接上一段末帧；在该模式下 prompt 先写：

`For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`

然后空一行：

```text
integrated_multimodal_description: [Shot 1] Live-action, cinematic, a wide shot frames <place, materials, light, developing action, camera; for a continuation, retain the preceding final shot's visible state before advancing>. [Shot 2] At <cut 1 of this segment>, the camera cuts to <new scale or step; establish any intentional location transition>. [Shot 3] At <cut 2>, the camera cuts to <new detail advancing this chapter>. [Shot 4] At <cut 3>, the camera cuts to <a concrete end state and motion the next chapter can continue, or the final chapter's closing image>. Silent visuals throughout.

overall_soundscape: N/A

non_diegetic_music: N/A
```

画面英文；解说中文。换位置只写该镜头里看得见的路径，不要把人瞬移进车、出车、跨过空隙或迈下边缘。每段四句短句对应四镜，但**字数不能固定为 70–90 字**。提交计划前按
`floor((duration_seconds - audio_offset_seconds) × 4)` 计算该段口播上限；例如 15 秒、偏移
0.8 秒时最多 56 个字符（含标点），建议写 42–52 字并保留自然停顿。30 秒段也按公式计算，
不要为了用满预算堆砌文字。`prepare_narrated_video` 返回的
`recommended_max_characters` 是该段最终上限；若出现 `likely_too_long`，不要调用 TTS，先仅缩短
对应段落并重新提交一次完整计划。不要造字幕/Logo。

## 提交格式

`prepare_narrated_video` 的 `plan` 必须是原生对象。每段**只能**有下列键，禁止 `segment_id_note`、`note`、`label`、`description` 或任何未列出的字段。下面只是字段结构，`D_i` 代表该段按实时默认值算出的数字，不是可直接提交的 JSON。窗口总和等于 `target_duration_seconds`，内外两个 `duration_seconds` 都必须填该段实际数字。不要从示例抄出固定 30 秒或固定字数。若服务返回了不同窗口，只改段长和对应内容，不调用视频生成来试探。

```text
plan.title = 成片标题
plan.target_duration_seconds = 用户要求的总秒数（未指定则 120）
plan.segments = 按实时默认时长和尾段规则一次列齐所有段
每段.segment_id = segment-001、segment-002……
每段.duration_seconds = D_i（实际数字）
每段.generation = {prompt: 本段完整 H3 四镜正文, prompt_mode: h3,
  aspect_ratio: 16:9, resolution: 512p, duration_seconds: D_i（实际数字）,
  audio_enabled: false}
每段.narration = 与该段 D_i 相称的中文短解说
每段.audio_offset_seconds = 0.8
```

后续段 `generation` 不要填 `first_frame_url`。`generation.duration_seconds` 必须等于该段窗口。

`render_narrated_video` 的 `narration` 每段只能是：

```json
{
  "plan_digest": "prepare 返回的 64 位 hex",
  "narration": [
    {"segment_id": "segment-001", "audio_url": "TTS 实际返回的签名音频 URL", "sha256": "64位hex"}
  ]
}
```

原生 TTS 使用真实返回的 `audio.url`（或 `audio.download_url`）填入实时 Schema 支持的 `audio_url`。如果旧版 TTS 实际返回合法 `att_...`，才使用 `attachment_id`，两者不能同时填写；原生 `artifact-...` 不能冒充 `att_...`。禁止虚构 URL 或使用需要聊天登录的 `/v1/run-artifacts/` 地址。静音计划 `narration` 为空数组。

## 制作

原生宿主使用 `activate_tools` 的 `names` 数组加载当前阶段工具，名称从工具目录查询结果逐字复制。计划阶段只加载计划保存工具；默认时长未知时先加载只读模型查询工具。计划保存成功并返回 `plan_digest` 后，再加载已确认的 TTS 与最终渲染工具。加载只改变下轮可见 Schema，不执行工具。**不要调用视频生成工具代替 TTS 或试探默认值；直接视频提交不属于本技能的执行链。** 不提交旧加载器名称或 `mode`、`tool_names` 参数。

1. `prepare_narrated_video` 一次交全片。保存 `plan_digest` 与各段 `narrations.text`。计划落库不是成片。
2. **每段单独一次**调用目录返回的 TTS 工具，同一模型与声音，`artifact_visibility: "internal"`。当前原生工具通常名为 `model_synthesize_speech`，但实际调用仍复制查询结果。输入 `text` 使用对应 `narrations.text`；模型与音频格式沿用配置，未确认格式时不要猜 `filename` 扩展名。记下实际 `audio.url`、`audio.sha256`，按实时 Schema 传给媒体服务。旧版附件 ID 仅在工具确实返回该 ID 时使用。不要把多段解说拼成一个音频。
3. 立刻 `render_narrated_video`，按上面的 `narration` 绑定全部有解说的段。保持这次调用直到返回最终 MP4；不要自己 submit 或轮询。

没有最终 MP4 不得结束。不要把脚本、海报、PPT 当交付。恢复用原 `plan_digest`。

若 `render_narrated_video` 返回 `status: needs_narration_repair`，这是已保存的正常检查点，不是视频
失败：一次读取完整 `repairs`，只把每项 `source_text` 缩短到其 `suggested_max_characters` 以内，并且
只为 `required_narration_segment_ids` 各调用一次 TTS。随后仍使用原 `plan_digest`，`narration` 只传
这些新附件；`retained_narration_segment_ids` 必须省略，其他段也不要重新合成。不得原样重试
`render_narrated_video`，不得把全部配音再做一遍。

已失败视频 job 才 `retry_failed=true`。未知提交结果先核对原任务。字幕/Logo/BGM 先确认后期能力。
