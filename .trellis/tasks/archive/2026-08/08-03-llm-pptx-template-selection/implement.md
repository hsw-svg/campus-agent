# 实施计划

## Ordered Checklist

1. [x] 审计并固化两份模板 manifest：确认候选源页、递归记录 shape ID/name、标注 `rewrite/delete/keep`、容量和支持的逻辑 layout；排除主题截图、原始数据图和授权说明页。
2. [x] 新增 `pptx_templates/catalog.py` 与两个 manifest，提供模板名称别名解析、白名单 ID 校验、默认模板和 `development_only` 元数据；增加 catalog/manifest 单测。
3. [x] 扩展 `SlideDeckJsonSkill`，保留规范化的可选 `template_id`，确保历史 payload 不受影响。
4. [x] 修改 `CourseIterationExecutor`：把模板清单注入现有 JSON prompt；实现“显式名称 > 上一版 > LLM > ai_tech 回退”；写入稳定模板元数据；覆盖首次选择、续改沿用和显式切换测试。
5. [x] 为 PPTX 导出新增确定性 frame planner：处理 cover、bullets、two_column、callout、summary，按容量选择 frame，避免相邻重复，并修复 title 页重复封面。
6. [x] 实现内存 OOXML 源页面复制器：顺序复制 slide XML/relationships，保留 layout/master/theme/media，移除源 notes 关系，重写 presentation relationships/content types，并以 `python-pptx` 可重新打开作为门槛。
7. [x] 实现 manifest 驱动的递归对象定位和文字替换：保留源 run/paragraph 样式，处理多段/多槽位内容、删除示例文字、写入独立 speaker notes；不使用全局文本清空。
8. [x] 重构 `SlideDeckPptxSkill` 串联 catalog、frame planner、slide cloner 和 text filler；移除运行时 `_THEME_KEYWORDS` 选择，但保留现有导出返回类型与 API 调用方式。
9. [x] 扩展 PPTX 回归：两种模板均可生成；页数规则正确；页面尺寸/母版关系保留；课程文字存在；AI/物联网/第一PPT/网址/授权页样例文字不存在；重复构图策略正确；历史 Artifact 回退 AI科技。
10. [x] 运行目标后端测试和完整 pytest；用生成样例做 ZIP/XML 检查，并以 `python-pptx` 重新打开。不新增或运行 PNG 预览链路，最终视觉由下载 PPTX 后查看。
11. [x] 完成 PRD 收敛检查、Trellis 质量检查和比赛前替换提醒；不提交 Git commit，等待用户明确确认。

## Validation Commands

```powershell
cd apps/api
..\..\.venv\Scripts\python.exe -m pytest tests/skills/test_slide_deck_json.py tests/skills/test_slide_deck_pptx.py tests/agents/test_course_iteration_executor.py tests/api/test_artifacts_export.py
..\..\.venv\Scripts\python.exe -m pytest
```

若未修改前端，无需运行前端构建；如果实现过程中新增前端可见模板信息，再执行：

```powershell
cd apps/web
npm.cmd run lint
npm.cmd run build
```

最终额外检查：

```powershell
git diff --check -- .env.example apps/api apps/web
```

## Review Gates

- [x] 用户已审阅 `prd.md`、`design.md`、`implement.md` 并同意进入实现。
- [x] `task.py start` 前保持任务状态为 `planning`。
- [x] 模板 manifest 中不存在未分类的可见示例文字对象。
- [x] 不以空白主题或旧四模板作为静默降级路径。
- [x] 不新增任意文件路径加载、模板上传或前端管理范围。
- [x] 不新增 PPTX 转 PNG、截图目录或预览接口；现有下载接口保持唯一最终视觉查看路径。
- [x] 当前两份模板保持 `development_only`，并保留比赛前人工替换门槛。

## Risky Files / Rollback Points

- `apps/api/app/skills/slide_deck_pptx.py`：核心导出行为替换；保留 `SlideDeckPptxSkill.run()` 和 `ExportedBinaryArtifact` 外部契约作为回滚边界。
- `apps/api/app/skills/pptx_templates/`：模板文件与 shape manifest 强绑定；模板被重新保存后需重新审计 ID。
- `apps/api/app/agents/executors/course_iteration.py`：Prompt/schema 和上一版复用逻辑；模型返回仍必须经过白名单覆盖。
- `apps/api/app/skills/slide_deck_json.py`：只增加可选字段，禁止改变现有 slide 归一化语义。
- OOXML 复制器：任何关系异常都应失败并报告，不生成可能损坏的 PPTX。

## Rollback Shape

1. 恢复旧 `SlideDeckPptxSkill` 关键词主题实现。
2. 保留或忽略 Artifact 中新增的可选模板元数据，不需要数据库迁移。
3. 删除 catalog/manifests/复制器及其测试即可回到旧导出路径。
