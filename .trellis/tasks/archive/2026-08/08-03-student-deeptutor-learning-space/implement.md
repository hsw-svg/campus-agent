# 实施计划：学生端交互式书本与学习空间

## 阶段 1：数据契约与本地状态

- [x] 扩展 `apps/web/src/api.ts` 的 DeepTutor book/page/block 归一化字段，保持现有调用兼容。
- [x] 新增 `apps/web/src/hooks/useDeepTutorStudyState.ts`，实现完成页、笔记、收藏问题、最近位置的安全 localStorage 读写。

## 阶段 2：学习空间概览

- [x] 新增 `DeepTutorLearningSpacePanel.tsx`，实现加载/错误/空态、统计卡、继续学习、书本和知识库摘要。
- [x] 在 `StudentWorkspace.tsx` 增加学习空间导航与面板挂载，并更新移动端导航和宽度逻辑。

## 阶段 3：交互书本阅读器

- [x] 重构 `DeepTutorBookPanel.tsx` 的书架布局，加入搜索、书本统计、选中态和创建书本表单。
- [x] 增加目录侧栏、页面 block 卡、阅读进度、上一页/下一页、页面完成和本地笔记。
- [x] 增加书本/页面切换时的请求竞态保护和 WebSocket 清理。
- [x] 将页面问答升级为带页面上下文的流式侧栏，并提供保存问题动作。

## 阶段 4：验证与交付

- [x] 运行 `npm.cmd run lint`。
- [x] 运行 `npm.cmd run build`。
- [x] 运行与现有 DeepTutor 适配层相关的后端测试或至少执行 API 单元测试子集。
- [x] 使用 `git diff --check`、Trellis check 和工作区状态检查，确认没有 `.env`、临时 clone、构建物或无关修改。
- [x] 提交前向用户确认后创建单主题 commit；完成后合并回 `master`，保留合并记录。
