# ExoHarness Skills

[English](README.md) | 简体中文

可复用的智能体技能集合，包括任务说明、参考资料、脚本和设计资源。Skill 定义任务如何规划和完成；实际执行由宿主框架授权的工具、模型 API、MCP 服务及隔离运行环境提供。

可用于 [ExoHarness](https://github.com/jason571/Exoharness)，也可在核对格式和工具兼容性后接入其他智能体。现有目录覆盖多个领域，并非限制框架用途；新增 Skill 的业务规则不需要写入框架代码。

## 技能目录

| 分类 | 技能 | 用途 |
| --- | --- | --- |
| 网页与视觉设计 | [web-site-builder](web-site-builder/)、[frontend-design](frontend-design/)、[canvas-design](canvas-design/)、[theme-factory](theme-factory/) | 网站交付、界面设计、视觉构图、字体与主题 |
| 视频导演与 MV | [minimax-h3-director](minimax-h3-director/)、[music-video-from-audio](music-video-from-audio/) | 剧情、H3 提示词与分镜、参考图角色和多段 MV 规划 |
| 地域宣传 | [yongjia-product-promo](yongjia-product-promo/) | 产品、文化与旅游宣传视频及解说 |
| 音乐创作 | [yue2-song-production](yue2-song-production/) | 调用已授权的 YuE2 服务创作演唱歌曲，可选封面 |
| 教学动画 | [elementary-lesson-video](elementary-lesson-video/) | 适龄讲解、课程计划和音画同步动画 |
| 空间娱乐 | [clhh-space-entertainment](clhh-space-entertainment/) | 娱乐场馆与空间工作流领域资料 |
| 扩展开发 | [skill-creator](skill-creator/)、[mcp-builder](mcp-builder/)、[find-skills](find-skills/) | 创建 Skill、开发 MCP 服务、查找现有技能 |
| 搜索与提取 | [tavily-search](tavily-search/)、[tavily-dynamic-search](tavily-dynamic-search/)、[tavily-extract](tavily-extract/) | 搜索规划、聚焦查询与网页内容提取 |
| 网站探索与研究 | [tavily-crawl](tavily-crawl/)、[tavily-map](tavily-map/)、[tavily-research](tavily-research/) | 网站爬取、链接映射和研究流程 |
| Tavily 集成 | [tavily-best-practices](tavily-best-practices/)、[tavily-cli](tavily-cli/) | 接入说明与 CLI 使用 |

本次公开版本包含 21 个技能包。目录中存在 Skill，不代表其依赖的模型服务已在本机安装。

## 安装与导入

```bash
git clone git@github.com:jason571/skills.git
```

在 ExoHarness 中：

1. 在技能导入页面选择包含 `SKILL.md` 的**单个技能目录**，例如 `skills/web-site-builder`。保留同目录下的参考资料、脚本、字体和其他资源。
2. 登记并启用 Skill，授权给需要使用它的助理。
3. 登记并授权该技能依赖的 MCP、TTS/图片/视频模型或沙盒运行环境。
4. 如果技能包含可执行脚本，先准备经过批准的隔离运行环境。导入说明本身不会执行代码或安装依赖。
5. 完成一个代表性任务，检查 Trace 和最终产物。

其他智能体使用各自的技能安装机制，并核对工具兼容性。复制技能目录不会自动提供它引用的模型 API 或执行服务。

## 目录结构

```text
package-name/
  SKILL.md       # 必需：名称、描述和任务说明
  references/    # 可选：按需读取的资料
  scripts/       # 可选：辅助执行脚本
  assets/        # 可选：字体、图片、模板等资源
  LICENSE*       # 技能作者提供的许可证
```

不同包的资源目录可能不同。保持包内相对路径；只导入 `SKILL.md` 可能丢失必要资源。宿主按需求发现技能、读取当前任务需要的说明，再按需加载执行工具的 Schema。

## 执行依赖

- 网页与代码任务使用宿主工作区和隔离代码工具。宿主已有原生工具时，不要求安装旧的 `skill-workspace` MCP。
- 教学动画需要课件渲染服务和 TTS 能力；单独登记技能不会生成语音或执行 Manim。
- 音乐、图片和视频任务需要对应的模型服务，多段视频还需要媒体合成服务。执行参数以实时工具 Schema 为准。
- Tavily 技能需要对应的 Tavily 集成和 API 密钥；CLI 示例还依赖 CLI 及其运行环境。搜索和 Research 的耗时、计费方式不同。
- 脚本需要的 Python/Node 依赖安装在经过批准的隔离环境内。任务文件保存在工作区，最终产物通过宿主发布，不直接运行用户宿主 Shell。

部分配套服务可在 [MCP 仓库](https://github.com/jason571/mcp)找到。此仓库不包含模型权重、私有密钥、实际运行环境或生成文件。

## 许可证与分发范围

每个技能保留自己的许可证和来源声明，集合不使用统一许可证覆盖上游条款。详见 [THIRD_PARTY.md](THIRD_PARTY.md)，设计字体等资源也适用各自许可证。

本地 `docx`、`pptx`、`pdf`、`xlsx` 包附带的上游许可证限制再分发，因此**未包含在公开仓库中**；本次发布不修改或删除它们的本地副本。需要这些包时，应从发布方按其条款获取。该分发限制不影响框架使用其他具有适当许可的文档生成技能。

## 相关项目

- [ExoHarness 主框架](https://github.com/jason571/Exoharness)：智能体、权限、Trace、沙盒及文件交付
- [MCP 服务集合](https://github.com/jason571/mcp)：独立服务实现和导入示例
