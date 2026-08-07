# 演示视频执行计划

## 有序清单

1. [x] 按用户提供的逐秒标注复核原始视频的 6 个区间边界，抽取首尾帧确认没有黑屏、腾讯会议残留、敏感信息或未完成加载。
2. [x] 删除 00:00–00:02；将 A–F 按设计中的跳切策略剪辑为 `project-demo-cut.mp4`，保留原始分辨率并确保总时长小于 300 秒。
3. [x] 根据 `docs/赛题要求.md` 和 `docs/设计方案.md` 编写 `timeline.md`，记录目标时间轴、画面证据、评分点和逐段解说。
4. [x] 使用 Edge TTS 中文女声逐段生成并对齐为 `narration.wav`，检查每段音频均短于对应字幕窗口。
5. [x] 生成 `narration.srt`，将中文解说按目标时间轴分段并检查每行长度。
6. [x] 将解说与底片混音、烧录带半透明深色背景的中文字幕，封装为 `project-demo-final.mp4`；原声降至 8%，解说增益至 1.25。
7. [x] 用 ffmpeg 重新读取最终文件元数据：时长 00:04:38.14、1920×1080、H.264 High 视频和 AAC 单声道音频。
8. [x] 抽帧检查 00:04、01:38、04:20，确认 14 号白字、约三分之一不透明的深色背景清晰，位于下方安全区且未遮挡主要功能区域。

## 验证命令

```powershell
$ffmpeg = 'C:\Users\hsw\AppData\Local\JianyingPro\Apps\5.5.0.11332\ffmpeg.exe'
& $ffmpeg -hide_banner -i artifacts\project-demo-video\project-demo-final.mp4
```

验收条件：最终时长不超过 00:05:00；至少包含 H.264 视频流和 AAC 音频流；时间轴与 `timeline.md` 的片段顺序一致。

## 风险文件与回滚点

- 输入文件：`C:\Users\hsw\Desktop\meeting_01.mp4`（只读，不覆盖）。
- 生成目录：`artifacts/project-demo-video/`（可整体移除并重建，不影响应用代码）。
- 规划文件：本任务目录内的 `prd.md`、`design.md`、`implement.md`。
- 如果语音或剪辑效果不合格，保留原片和脚本，仅重做中间底片/音频/封装步骤。
