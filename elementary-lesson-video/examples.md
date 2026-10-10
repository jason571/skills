# 示例

下面的 `tts.py` 命令仅准备参数，不合成声音。随后由 Agent 调用已启用的 TTS，保存
真实音频绑定，再运行 `render.py --audio-manifest ... --out ...`；详见主说明。

仓库里的 JSON 只说明「年级不同，稿子就不同」。一年级到六年级都走同一流程：读年级 → 按 [grades.md](grades.md) 写稿 → 渲染。没有单独示例的年级（一年级、三年级、五年级、六年级）同样现写，不要去套二年级或四年级的现成稿。

## 示例 A：二年级减法故事

用户：`二年级，树上有 8 只鸟，飞走了 3 只，还剩几只？做课件视频`

对着图数，算式出现在数完之后。完整 JSON：`examples/grade2_birds.json`。

```bash
python scripts/tts.py --lesson examples/grade2_birds.json --out /work/grade2-birds/tts_requests.json
```

## 示例 B：四年级分数加法

用户：`四年级，1/2 加 1/3 等于多少？帮我做小学课件视频`

先图后步骤。完整 JSON：`examples/fraction_add.json`。

```bash
python scripts/tts.py --lesson examples/fraction_add.json --out /work/fraction-add/tts_requests.json
```

## 其他年级同样处理（无现成 JSON 就现写）

二年级数量推理的完整讲解示例：`examples/grade2_chicken_rabbit.json`。它用一题演示读题、说明每步理由、验算及可读画面，不规定其他题目使用同一解法、数字或分段数。

同一句「还剩几只」：

- 一年级：只数，几乎不提算式名字。
- 三年级：可以先说「这是求还剩，用减法」，再列式，并补一道改数字。

同一句「1/2 加 1/3」：

- 一年级：只讲一半，不引入三分之一加法。
- 三年级：讲清平均分、取几份，比较谁更大，不做通分加法。
- 五年级：通分后可补「为什么格子要一样大」。
- 六年级：可收成最简、并点一句以后分数运算还会用到。

科学题「为什么天空是蓝色的」同样按当前年级改词，不要固定用二年级或四年级那一版。

## 产出路径

```
output/<slug>/
  lesson.json
  timeline.json
  subtitles.srt
  tts_raw.json
  audio/<source-sha256>.wav ...
  audio/speech.wav
  final.mp4
  validation.json
```

## 只改画面

```bash
python scripts/render.py --lesson output/<slug>/lesson.json --out output/<slug> --skip-tts
```
