# 可组合教学画面

用于解释需要“看见关系或变化”的内容。先决定孩子要观察什么，再组合图形与动作；
不是根据题目关键词选择固定视频模板。无需调用图片或视频生成模型，也不生成可执行代码。
本文件只在编写 `scene` 画面时读一次；已经掌握格式或上下文中仍有它时不要重复读取。

## 画面设计

- 区分要讲的实体，用独立对象或组合图形表示；用位置、大小、连线、包含和分组表达关系。
  不用一个圆圈同时贴两个不同实体的名字，也不把整段旁白塞进标签。
- 动作要有教学作用：移动体现位置/数量变化；旋转体现方向或周期；缩放体现层级；
  显示/隐藏体现先后；高亮指出当前依据。拆分与合并用分组后的移动组合完成。
  不给无关物体加运动来冒充演示。
- 标题页、题干、必要算式和小结可以静止。核心解释优先使用图形变化，文字只作短标签、
  关键问题和结论。文本/表格确实更适合的内容仍可使用原有组件，不强凑某个动画比例。
- 一个口播段解释一个动作或紧密相关的动作组。希望动作精确对应一句话时，按句拆分配音，
  用 `continue_previous` 接续画面；不要猜词级时间戳。
- 示意图不是写实影像、真实比例或物理仿真。涉及比例或运动周期时说明是否只是示意。
  现有组件无法可靠表达的部分说明限制，不能用整屏文字代替后声称已经演示。

## `visual.type = "scene"`

完整层级是 `{"lesson":{...,"segments":[{"id":"s1","narration":"…","visual":{...}}]}}`。
段落自身只接受 `id`、可选 `role`、`narration`、`visual`；画面标题 `heading` 也属于 `visual`。

新画面定义 `objects`，可选 `groups`，再列 `actions`。每个对象 ID 在当前画面中唯一。
同一画面后续段只写 `continue_previous:true` 和新的动作，不重传对象。
接续不是“往上一段新增对象”：后面需要出现的对象先在首段定义为 `visible:false`，
后面通过 show 显示；如果本段需要重新定义对象或分组，就创建新画面，不使用 continue_previous。
一次连续画面先确定共用的对象 ID 与分组，再写各段动作；每个 target 必须来自这份声明。
新 scene 会切断原来的继承链，后续段不能再引用旧 scene 的对象。局部修复不要整块重写 visual，
尤其不要遗漏原有的 continue_previous；缺少后续对象时，应补在返回的声明源，而非接续段。
分组成员是固定 ID 集合；移动到另一组的位置不会自动改变成员。重新分组后按实际对象 ID 操作，
不能把旧分组名误当成当前空间位置中的那一组。

| 字段 | 内容 |
| --- | --- |
| `heading` / `caption` | 固定的短标题/说明，不参与图形缩放 |
| `objects` | 最多 32 个对象，每个只写需要覆盖的属性 |
| `groups` | 最多 12 个命名分组，`members` 引用对象 ID，不嵌套分组 |
| `actions` | 最多 32 个动作；只编写实际需要的动作，不追求数量 |
| `continue_previous` | 默认 false；true 时沿用紧邻上一段 scene 的全部对象、分组、最终位置与显隐状态，不写 objects/groups |

### 对象

```json
{"id":"bead","kind":"circle","at":[-2,0],"size":[0.8,0.8],"color":"#38BDF8","fill":0.8,"label":"一颗珠子"}
```

- `kind`：`circle`、`ellipse`、`rectangle`、`triangle`、`star`、`line`、`arrow`、`path`、`polygon`、`text`。
- `at` 是画面坐标中的中心，推荐 x 在 -5.5～5.5、y 在 -2.2～2.2；为对象尺寸及下方标签留空间。
  `size` 为宽高，默认 `[1,1]`，两个值都必须大于 0，即使是 line/arrow 也不能写 `[长度,0]`；圆应使用相同宽高。
- `color` 是六位十六进制颜色，`fill` 是填充透明度。`label` 是随物体移动、保持正向的短标签。
  尽量在 10 字以内，最多 32 字；说明句放到旁白或 caption。
- `visible:false` 表示开头隐藏，可在对应口播段通过 `show` 揭示。
- `text` 对象需给 `text`；建议显式设置足够的 `size`，例如 `[4,0.8]`，只放短语/算式。
- `line`/`arrow` 初始水平，长度由 `size[0]` 决定，需要方向变化时使用 rotate。
  对象没有 `rotate` 字段；斜线的初始构图可用 path 的两个端点表示，运动旋转才写入 actions。
- `path`/`polygon` 用 `points` 描述轮廓，至少 2/3 个不同点，最多 24 点；点列决定形状与大小，
  `at` 决定其包围框中心。path 是折线，不会偷偷变成样条曲线或物理轨迹。

### 动作

所有动作指定 `op`、`target`。target 是对象 ID、分组 ID，或 `"*"`（全部图形，不包括标题和说明）。
target 是一个字符串，不是 ID 数组；多个对象一起动作时先定义 groups，再引用分组 ID。
`start/end` 默认 0/1，是**本段真实配音时长的比例**，满足 `0 <= start < end <= 1`。
默认平滑起止；匀速运动用 `ease:"linear"`。比例是视觉节奏，不是假造的语音词戳。

| op | 额外字段 | 效果 |
| --- | --- | --- |
| `move` | `by:[dx,dy]` | 从当前状态相对平移 |
| `scale` | 必填数字 `factor`，可选 `about:[x,y]` | 相对缩放，例如 1.2；不是 `to:[1.2,1.2]` |
| `rotate` | 必填数字 `degrees`，可选 `about:[x,y]` | 相对旋转，例如 90；绕指定点运动时填写 about；标签保持正向 |
| `follow_path` | `points:[[0,0],…]` | 从当前中心沿相对偏移折线运动；按路径长度分配进度 |
| `show` / `hide` | 无 | 从当前透明度显示/隐藏，最终状态保留 |
| `highlight` | 可选 `color` | 在本动作中突出目标，结束后还原颜色 |

影响同一物体的位移/旋转/缩放/路径动作不能时间重叠，需依次执行；不同物体可以并行。
同一物体的两段显隐动作或两段高亮动作也不能重叠；高亮、显隐、位移这三类之间可以并行。
`show/hide` 不是瞬时开关，省略 `end` 会淡入/淡出到本段结束。例如先出现再消失，应写
`show start=0.2 end=0.4`、`hide start=0.6 end=0.8`；0.4～0.6 之间保持可见。
这些时间只是格式示例，按实际画面安排；分组与 `*` 也会影响成员，需检查展开后的对象是否重叠。
缩放过大或把物体移出画面会影响理解，应先按构图检查。

## 完整调用示例（参数层级示范，不是题目模板）

以下是完整 `prepare_lesson` 参数，不是可以直接塞进 segments 的 visual 片段。
题目、口播、对象和动作按实际教学任务编写；这里只展示首段定义与后续接续：

```json
{
  "lesson": {
    "title":"观察物体位置",
    "question":"物体移动后，怎样判断它的新位置？",
    "subject":"数学",
    "grade":"小学一年级",
    "segments":[
      {"id":"question","narration":"物体移动后，怎样判断它的新位置？",
       "visual":{"type":"title","title":"观察物体位置","subtitle":"物体移动后，怎样判断它的新位置？"}},
      {"id":"observe","narration":"先看左边的圆形。另一件物体稍后出现。",
       "visual":{"type":"scene","heading":"先找到圆形",
         "objects":[
           {"id":"a","kind":"circle","at":[-2,0],"fill":0.8,"label":"圆形"},
           {"id":"b","kind":"triangle","at":[2,0],"fill":0.8,"label":"三角形","visible":false}
         ],
         "groups":[{"id":"pair","members":["a","b"]}],
         "actions":[{"op":"highlight","target":"a"}]}},
      {"id":"move","narration":"三角形出现了。圆形向中间移动，它的位置变了。",
       "visual":{"type":"scene","continue_previous":true,"heading":"观察移动后的新位置",
         "actions":[
           {"op":"show","target":"b","start":0,"end":0.25},
           {"op":"move","target":"a","by":[1,0],"start":0.25,"end":1}
         ]}},
      {"id":"turn","narration":"观察三角形转过一个方向，再把图放大看清楚。",
       "visual":{"type":"scene","continue_previous":true,"heading":"方向和大小的变化",
         "actions":[
           {"op":"rotate","target":"b","degrees":90,"start":0,"end":0.5},
           {"op":"scale","target":"pair","factor":1.2,"start":0.5,"end":1}
         ]}}
    ]
  }
}
```

每段仍有自己的 narration，后端使用各自真实 TTS 时长，不用重复合成前一段。
若中间切换到了 title/table 等非 scene 画面，下一次 scene 重新定义对象。
ID 引用、动作冲突、无效类型和跨段接续在 `prepare_lesson` 时校验，错误只修正相关字段，
不要更换题目、重写整课或额外调用视频生成工具。
