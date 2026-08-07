# DeepTutor 交互教材对照研究

核查日期：2026-08-05

## 参考来源

- 上游仓库：<https://github.com/HKUDS/DeepTutor>
- 上游交互教材文档：<https://docs.deeptutor.info/explore/book/>
- 上游学习空间文档：<https://docs.deeptutor.info/explore/space/>
- 本机临时源码副本：`C:\Users\hsw\AppData\Local\Temp\deeptutor-reference`

## 上游定义

- Book 是由类型化内容块组成的“活教材”，不是单一长文本；正文、提示、测验、闪卡、代码、时间轴、图形、交互块、动画、深度解析和用户笔记使用不同的块类型。
- 页面阅读器使用固定高度的内部滚动容器，正文宽度受限；页头会在向下滚动后收起，减少长页面的垂直占用。
- `PageOutlineNav` 根据当前页面块生成可折叠的浮动结构导航，并通过 IntersectionObserver 标记当前可见块，点击后跳转到对应块。
- `BookChatPanel` 是独立的页面级聊天面板；页面变化时重新加载该 session 的消息，流式输出只追加合格的 content 事件，用户问题和回答都在面板中保留。
- Learning Space 是持久化资料层，不仅展示数量：Notebook 保存可复用记录，Question Bank 保存问题、用户答案、参考答案、正确性和解析，并支持收藏/分类/回到上下文。

## 当前项目差异

- 当前项目已复用书架、目录、页面块、页面问答和学习空间的概念，但阅读器仍由外层工作台主滚动区承载，没有上游的内部阅读滚动和块级导航。
- 当前问答仅存于 `DeepTutorBookPanel` 的 React state；`useDeepTutorStudyState` 只保存问题文本，不保存回答、会话 id 或页面级聊天记录。
- 当前学习空间只展示笔记和待复习问题的数量，无法查看内容或从记录定位回书本页面。
- 当前项目的演示状态明确是浏览器本地状态，不应在本轮扩大为新账号、数据库或跨设备同步能力。

## 采用的最小改进

- 在现有三列工作台内增加桌面端独立阅读滚动区和页面块跳转条，借鉴上游 Reader/Outline 的定位模型，不复制整套上游 UI。
- 将页面级问答消息和 session id 纳入现有本地学习状态，按 `bookId:pageId` 隔离，并保留向后兼容的旧 localStorage 数据解析。
- 在学习空间直接列出最近笔记和待复习问题，点击后回到对应书本/页面；没有后端同步时明确保持本地演示语义。
- 将服务内部名称从发送按钮的处理中提示中移除，只呈现学生可理解的问答状态。
