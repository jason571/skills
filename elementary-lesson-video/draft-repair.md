# 已保存草稿的局部修复

只在 `prepare_lesson` 返回 `needs_repair` 时使用。完整草稿已保存在 MCP，模型只需要草稿 ID、最新版本、错误与必要局部字段，不需要重写正确旁白和画面。

`errors[].path` 是相对于 lesson 的 JSON Pointer，数组下标从 0 开始。
先利用 `current`、`expected` 和检查点 `repair_context.focus` 中已经返回的原始局部数据；结构错误的必要资料齐全时直接 patch。工具声明允许补充读取且信息不足时调用 `get_lesson_draft`，例如：

```json
{"draft_id":"使用工具返回的 ID","paths":["/segments/1/heading","/segments/3/visual/actions/0"]}
```

它返回所选字段与约束；同一版本保留最近至多 8 个路径、16 KiB 的修复资料，避免连续查询互相丢失。`missing=true` 表示尚不存在；`too_large` 表示应选择更具体的子路径，不代表字段为空。先修复当前页，不为发现全部错误扫描整课。错误列表每页 8 条，用 `error_offset:8` 等读取后续错误；省略时保留当前页。补丁产生新版本后，旧版局部资料自动退出下一步上下文。

## 原生补丁

`patch_lesson_draft` 接受 add、replace、remove、move。add/replace 的 value 使用实际数字、对象或数组，不能包成 JSON 字符串；move 用 `from_path`，不带 value。

例如把放错层级的标题移入 visual，再为按本次设计应旋转 90 度的动作补充 degrees：

```json
{
  "draft_id":"使用工具返回的 ID",
  "expected_revision":1,
  "patches":[
    {"op":"move","from_path":"/segments/1/heading","path":"/segments/1/visual/heading"},
    {"op":"add","path":"/segments/3/visual/actions/0/degrees","value":90}
  ]
}
```

角度仅为补丁格式示例，实际值取决于要展示的变化。额外字段先判断应移动还是确实无用再删除；不要为通过校验删掉用户要求的画面内容。

`missing_scene_target` 会给出全部缺失的 targets、当前实际可用的 `scene.object_ids/groups`、
声明源 `scene.source_path` 和受影响的 `dependent_paths`。`related` 与 focus 指向原始声明和动作，
不要从相邻段猜对象名。原草稿没有定义的实体，应按教学意图在声明源补充对象（需要稍后出现时
设 visible=false）及分组，保留现有定义和动作；定义曾存在则按历史路径恢复。
只改 target 的场景限于已确认拼写错误，不能改成另一个实体或删除动作来通过校验。
整体替换接续 visual 时必须明确保留 continue_previous:true；确需断开时显式 false，并核对后续依赖。
`inherited_scene_declarations` 表示把新增声明放在了接续段：根据 source_path 把已有对象/分组逐项
move 到源数组，保留原值与源数组中的其他项，再移除空的错误父数组；不要重新生成这些对象。
源 groups 缺失时先按 expected 创建原生数组，不使用 `groups/名称` 这样的映射路径。

`action_overlap` 会返回冲突动作的 `related[].path`、生效的 `effective_timing`（包括省略后采用的默认值），
以及 `repair_context.focus` 中两处原始动作。只调整这些动作的时间，不删除动作、替换 target 或修改无关对象。
例如显示动作未写 end、随后又隐藏同一对象，应按画面意图补充显示结束时间，使其不晚于隐藏开始；
不要把所有动作都挪到同一时间。已给出两处动作时直接 patch，不需要重新读取整段或整课。

一次最多 32 个操作，按顺序原子应用。不能替换根节点或整个已存在的 segments 数组；只有根层 segments 缺失时可 add/move 补入。误多包一层时，从保存的错误父层 move 正确字段，不重写数组。数组局部插入/删除会改变后续下标，按操作顺序处理。补丁本身无效则整批不应用。合法补丁即使留下其他校验错误也会保存为新版本。

- `needs_repair`：使用返回的最新 revision，只继续处理剩余错误。
- `prepared`：计划已完整校验并冻结，继续返回的 speech_requests，不再修改此草稿。
- `patch_rejected` 包含 revision_conflict：其他修改已提交。读取当前相关路径，再决定是否仍需修复；不能仅更换版本号强行覆盖。
- 相同版本与相同补丁重送返回当前状态并标记 `idempotent_replay`，不会再次插入/删除，也不会回退后续修复。
- `no_change` 不产生新版本；修复进展按实际消除的约束判断，不按 revision 增长判断。
- 错误仍相同且不理解约束时，读取该局部并说明阻塞原因，不循环提交无变化补丁。

服务重启后用 draft_id 读取；完整草稿、修订记录和组件快照仍在。若服务明确报告契约版本变化，需要管理员处理迁移，不能把旧草稿当成新契约下已校验的数据。此阶段不会产生配音或渲染任务。

如果修复时误删了原数据，用 `get_lesson_draft(paths=[具体路径], at_revision=旧版本号)` 读取那一处原始值，再局部补回当前版本；不要重新编写对象和旁白，也不要回滚其余已经修好的字段。返回的 `revision` 仍是当前版本，`focus[].source_revision` 标明所读数据来源。遇到“动作 target 不存在”等跨段引用错误时，核对对象定义和接续关系，不能把用户要求的动作删除或改指向另一个实体来绕过校验。定义丢失则从历史版本恢复；只有明确是 ID 拼写错误时才改引用。原草稿自身缺少的内容不是可恢复数据，应按本次教学设计补充并说明，不声称是找回的原值。
