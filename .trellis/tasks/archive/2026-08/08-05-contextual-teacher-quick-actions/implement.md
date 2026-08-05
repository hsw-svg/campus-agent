# 实施计划：课程切换驱动教师端快捷任务

## 变更步骤

1. 在 `TeacherWorkspace.tsx` 中增加快捷任务类型和基于当前课程名称的派生定义。
2. 为有课程和无课程分别提供通用、课程化的练习、课堂互动、薄弱点分析文案。
3. 替换欢迎区两个快捷入口的内联 prompt。
4. 替换学情分析报告后“继续生成课堂练习”按钮的内联 prompt。
5. 替换输入框上方三条标签的显示文案和发送 prompt，并为课程化标签提供完整文案的 `title`。
6. 搜索确认旧的固定快捷任务文案不再作为教师快捷任务入口使用，检查课程切换时的 state 依赖。

## 验证命令

- `cd apps/web; npm.cmd run lint`
- `cd apps/web; npm.cmd run build`
- `rg -n "根据本节课目标生成 Python 练习|帮我设计一个破冰环节|总结上周测试的薄弱知识点" apps/web/src/components/TeacherWorkspace.tsx`
- `git diff --check`

## 风险与回滚点

- 主要风险是只替换了某一个重复入口，造成同一页面的快捷任务不一致；实现后必须检查三个入口区域。
- 主要回滚点为 `TeacherWorkspace.tsx`，不涉及 API 或数据库迁移。
- 如果课程名称未加载，必须保持通用回退，不阻塞教师继续输入自定义任务。
