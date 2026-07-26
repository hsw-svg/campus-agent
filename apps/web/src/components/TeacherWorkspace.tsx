import { useState, useEffect, useMemo, useRef, type FormEvent } from 'react';
import { 
  GraduationCap, 
  MessageSquarePlus, 
  History, 
  FolderOpen, 
  MoreVertical, 
  ShieldCheck, 
  Search, 
  Activity, 
  Bell, 
  UserRoundCheck, 
  UploadCloud, 
  ArrowRight, 
  Send, 
  Paperclip, 
  Mic, 
  Image as ImageIcon, 
  TrendingUp, 
  ChevronUp, 
  FileSpreadsheet, 
  Link as LinkIcon, 
  Download, 
  Sparkles, 
  FolderClosed,
  FileText, 
  Check, 
  BookOpen, 
  CheckSquare, 
  Brain, 
  HelpCircle,
  Copy,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { createCourse, deleteCourse, exportArtifact, listCourses, updateCourse, type Artifact, type Attachment, type Course, type CourseContext } from '../api';
import { Role, Message } from '../types';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import ConversationHistory from './ConversationHistory';
import TeacherAgentHistoryPanel from './TeacherAgentHistoryPanel';

interface TeacherWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

function isLearningTable(attachment: Attachment): boolean {
  return /\.(csv|xlsx?|xls)$/i.test(attachment.filename)
    || /csv|spreadsheet|excel/i.test(attachment.content_type);
}

export default function TeacherWorkspace({ token, onBackToRoles }: TeacherWorkspaceProps) {
  // States: 'welcome' | 'analyzing' | 'report'
  const [stage, setStage] = useState<'welcome' | 'analyzing' | 'report'>('welcome');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [isUploadingCourseMaterial, setIsUploadingCourseMaterial] = useState(false);
  const [activeTab, setActiveTab] = useState<'workbench' | 'resources' | 'analytics'>('workbench');
  const [courses, setCourses] = useState<Course[]>([]);
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null);
  const [expandedCourseId, setExpandedCourseId] = useState<string | null>(null);
  const [showInteractionPanel, setShowInteractionPanel] = useState(false);
  const [showCreateCourseDialog, setShowCreateCourseDialog] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDescription, setNewCourseDescription] = useState('');
  const [editingCourseName, setEditingCourseName] = useState('');
  const [showDeleteCourseDialog, setShowDeleteCourseDialog] = useState(false);
  const [isSavingCourse, setIsSavingCourse] = useState(false);

  // Interactive Quiz State
  const [quizAnswers, setQuizAnswers] = useState<Record<string, number>>({});
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Chat/Input states
  const [inputVal, setInputVal] = useState('');
  const [analysisActionNotice, setAnalysisActionNotice] = useState<string | null>(null);
  const activeCourse = courses.find((course) => course.id === activeCourseId) ?? null;

  // Auto-clear notice after 3 seconds
  useEffect(() => {
    if (!analysisActionNotice) return;
    const timer = setTimeout(() => setAnalysisActionNotice(null), 3000);
    return () => clearTimeout(timer);
  }, [analysisActionNotice]);
  const courseContext: CourseContext = {
    courseId: activeCourse?.id ?? null,
    courseName: activeCourse?.name ?? '任务',
    workflowId: activeCourse ? 'learning-analysis-to-activity' : 'standalone-task',
    workflowName: activeCourse ? '学情分析 → 课堂活动包' : '不关联课程',
  };
  const {
    chatMessages,
    isAiTyping,
    sendMessage,
    clearChat,
    uploadFile,
    error,
    conversations,
    activeConversationId,
    openConversation,
    removeConversation,
    attachments,
    artifacts,
    agentHistory,
    route,
    selectedArtifactIds,
    toggleArtifact,
    stopStreaming,
  } = useWorkspaceChat(token, courseContext);
  const visibleCourseAttachments = useMemo(
    () => attachments.filter((attachment) => attachment.course_id === activeCourseId || attachment.course_id === null),
    [activeCourseId, attachments],
  );
  const [progressBarWidth, setProgressBarWidth] = useState('w-0');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatScrollRef = useRef<HTMLElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const learningAnalysisReportRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const courseMaterialInputRef = useRef<HTMLInputElement>(null);
  const activeCourseIdRef = useRef<string | null>(activeCourseId);

  useEffect(() => {
    activeCourseIdRef.current = activeCourseId;
  }, [activeCourseId]);

  useEffect(() => {
    if (!token) return;
    void listCourses(token).then((items) => {
      setCourses(items);
      setActiveCourseId((current) => current ?? items[0]?.id ?? null);
      setExpandedCourseId((current) => current ?? items[0]?.id ?? null);
    }).catch(() => setAnalysisActionNotice('无法读取课程列表，请稍后重试。'));
  }, [token]);

  const openCreateCourseDialog = () => {
    setNewCourseName('');
    setNewCourseDescription('');
    setShowCreateCourseDialog(true);
  };

  const handleCreateCourse = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !newCourseName.trim()) return;
    try {
      const course = await createCourse(token, newCourseName.trim(), newCourseDescription.trim() || undefined);
      setCourses((current) => [course, ...current]);
      setActiveCourseId(course.id);
      setExpandedCourseId(course.id);
      setShowCreateCourseDialog(false);
      clearChat();
    } catch (reason) {
      setAnalysisActionNotice(reason instanceof Error ? reason.message : '创建课程失败，请重试。');
    }
  };

  const openCourseManagement = () => {
    setEditingCourseName(activeCourse?.name ?? '');
    setActiveTab('analytics');
  };

  const handleRenameCourse = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !activeCourse || !editingCourseName.trim()) return;
    setIsSavingCourse(true);
    try {
      const updated = await updateCourse(token, activeCourse.id, editingCourseName.trim(), activeCourse.description);
      setCourses((current) => current.map((course) => course.id === updated.id ? updated : course));
      setAnalysisActionNotice('课程名称已更新。');
    } catch (reason) {
      setAnalysisActionNotice(reason instanceof Error ? reason.message : '课程名称更新失败，请重试。');
    } finally {
      setIsSavingCourse(false);
    }
  };

  const handleDeleteCourse = async () => {
    if (!token || !activeCourse) return;
    setIsSavingCourse(true);
    try {
      await deleteCourse(token, activeCourse.id);
      const remaining = courses.filter((course) => course.id !== activeCourse.id);
      setCourses(remaining);
      setActiveCourseId(remaining[0]?.id ?? null);
      setExpandedCourseId(remaining[0]?.id ?? null);
      setShowDeleteCourseDialog(false);
      setActiveTab('workbench');
      // Let the course context switch before clearing resources; otherwise the
      // hook can briefly reload attachments for the just-deleted course (404).
      window.setTimeout(() => clearChat(), 0);
      setAnalysisActionNotice('课程已删除。');
    } catch (reason) {
      // A previous delete may have completed while the browser retried the
      // request. Treat a confirmed absence as success instead of leaving a
      // stale course card with a misleading 404.
      if (reason instanceof Error && 'status' in reason && (reason as { status?: number }).status === 404) {
        const latest = await listCourses(token).catch(() => null);
        if (latest && !latest.some((course) => course.id === activeCourse.id)) {
          setCourses(latest);
          setActiveCourseId(latest[0]?.id ?? null);
          setExpandedCourseId(latest[0]?.id ?? null);
          setShowDeleteCourseDialog(false);
          setActiveTab('workbench');
          setAnalysisActionNotice('课程已删除。');
          return;
        }
      }
      setAnalysisActionNotice(reason instanceof Error ? reason.message : '课程删除失败，请重试。');
    } finally {
      setIsSavingCourse(false);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputVal]);

  // Scroll to bottom on chat update
  useEffect(() => {
    const container = chatScrollRef.current;
    if (!container) return;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceToBottom < 200) chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAiTyping]);

  useEffect(() => {
    if (isAiTyping) {
      setStage('analyzing');
      return;
    }
    if (artifacts.some((artifact) => artifact.type === 'learning_analysis')) {
      setStage('report');
      return;
    }
    setStage('welcome');
  }, [artifacts, isAiTyping]);

  const startAnalysis = (_fileName?: string) => {
    setActiveTab('workbench');
    if (!courseContext.courseId) {
      setAnalysisActionNotice('请先选择一门课程，课程资料会自动用于学情分析。');
      return;
    }
    const hasLearningTable = attachments.some((attachment) =>
      isLearningTable(attachment) && ['indexed', 'degraded'].includes(attachment.status),
    );
    if (!hasLearningTable) {
      setAnalysisActionNotice('当前课程暂无可用的匿名学情表，请先上传并等待资料解析完成。');
      return;
    }
    setAnalysisActionNotice(null);
    setStage('analyzing');
    void sendMessage('分析学情', 'learning_analysis');
  };

  const handleCourseMaterialUpload = async (file: File) => {
    const uploadCourseId = courseContext.courseId;
    if (!uploadCourseId) {
      setAnalysisActionNotice('请先选择一门课程，再上传课程资料。');
      return;
    }
    setIsUploadingCourseMaterial(true);
    try {
      const attachment = await uploadFile(file, 'workspace', uploadCourseId);
      if (attachment && activeCourseIdRef.current === uploadCourseId) {
        const parsedSuccessfully = ['indexed', 'degraded'].includes(attachment.status);
        setAnalysisActionNotice(parsedSuccessfully
          ? `“${attachment.filename}”已上传到当前课程资料库。`
          : `“${attachment.filename}”已保存，但解析失败：${attachment.status_message ?? '请检查文件内容后重试。'}`);
      }
    } finally {
      setIsUploadingCourseMaterial(false);
    }
  };

  // Preset Responses for smart interactive tasks
  const getAiResponse = (prompt: string): Partial<Message> => {
    const p = prompt.trim();
    if (p.includes('小测') || p.includes('quiz') || p.includes('Quiz')) {
      return {
        type: 'quiz',
        content: '我已经为您生成了针对 Python Slicing 和 Tuple 的针对性随堂小测，包含3道核心高频错题。您可以直接在下方测试并向学生展示讲解：',
        metadata: {
          title: 'Python 切片与元组基础小测',
          questions: [
            {
              id: 'q1',
              question: '1. 给定列表 `lst = [10, 20, 30, 40, 50]`，以下哪项切片操作会输出 `[40, 20]`？',
              options: [
                'A) lst[3:0:-2]',
                'B) lst[3:1:-2]',
                'C) lst[-2:-5:-2]',
                'D) lst[3::-2]'
              ],
              correct: 3, // D is lst[3::-2] which starts at 40 (index 3), steps backwards by 2 to index 1 (20) -> [40, 20]
              explanation: '正解为 D。lst[3::-2] 表示从索引 3 (元素 40) 开始，向左步长为 2 切片，依次获取索引 3 和 1 的元素，即 40 和 20。'
            },
            {
              id: 'q2',
              question: '2. 执行以下代码会发生什么？\n`tup = (1, 2, 3)`\n`tup[1] = 4`',
              options: [
                'A) 元组变为 (1, 4, 3)',
                'B) 抛出 TypeError 异常',
                'C) 抛出 ValueError 异常',
                'D) 静默失败，元组保持不变'
              ],
              correct: 1, // B is TypeError
              explanation: '正解为 B。元组 (Tuple) 在 Python 中是不可变对象 (Immutable)。尝试修改其内部元素的指向会直接抛出 TypeError 异常。'
            }
          ]
        }
      };
    } else if (p.includes('邮件') || p.includes('mail') || p.includes('撰写')) {
      return {
        type: 'text',
        content: `### 📧 班级学情汇报邮件草稿已准备就绪：

您可以直接复制此内容发送给课程组或教研室负责人：

***

**主题**: 关于 2026年春季《Python 程序设计》班级学情分析及教学调整建议

**收件人**: 课程教学组全体老师 / 教务处

各位老师好，

基于本周对各班提交的匿名学情表（包含单元测试及平时作业完成度）的最新分析，目前我们班级的整体学情呈现以下特征，特此向课程组进行简要汇报：

1. **核心优势**:
   - **出勤率稳步提升**: 整体出勤率达到 **95%**（较上月提升 2%）。
   - **学习积极性**: 课堂互动参与度保持在 **High (高活跃)**，整体均分呈 Rising (上升) 态势。
   - **作业进度**: 当前单元作业完成度在 **88%** 左右。

2. **核心教学薄弱点**:
   - 绝大多数同学在 **Python Array Slicing（切片越界与负步长）**、**Tuple Immutability（元组不可变性底层报错）** 存在明显的理解混淆。
   - 单元 3 均分虽高达 94，但近期随着复合结构的引入，极少数学生的及格线出现轻微浮动。

3. **下一步教学节奏优化策略**:
   - **放缓核心算子进度**: 下周安排 **15分钟专门巩固** 切片的逆向步长和元组操作，多设计随堂实操代码练习。
   - **强化课件图形化演示**: 将在课件中补充三页内存指针变化图，直观展示元组与列表在内存堆栈中的区别。

请大家结合各班实际情况，针对薄弱知识点微调教案。如有建议，欢迎随时交流！

祝，教祺！
**Dr. Smith**
课程组负责人
`
      };
    } else if (p.includes('课件') || p.includes('课件更新') || p.includes('教案')) {
      return {
        type: 'plan',
        content: '我已根据薄弱环节，为您在“切片章节”和“元组底层机制”设计了三页精细化课件更新方案与图示：',
        metadata: {
          slides: [
            {
              title: 'Slide 1: 切片的三个魔术参数 [Start : Stop : Step]',
              bullets: [
                '利用**直观色块图**展示列表元素索引：正向(0 至 N)与负向(-1 至 -N)对照。',
                '**负步长机制解析**: 当 Step < 0 时，默认起点为末尾，终点为开头。结合 `lst[::-1]`（逆序）进行可视化。'
              ]
            },
            {
              title: 'Slide 2: 内存透视：元组 (Tuple) 真的绝对不可变吗？',
              bullets: [
                '**内存结构连线图**: 区分元组作为“容器指针数组”的存储模型。',
                '演示典型误区：`tup = (1, [2, 3], 4)` 中，修改 `tup[1].append(5)` 为何能成功？（因为元组存储的列表指针未变，但列表本身可变）。'
              ]
            }
          ]
        }
      };
    } else if (p.includes('破冰') || p.includes('互动') || p.includes('ice')) {
      return {
        type: 'text',
        content: `### 🎯 破冰游戏方案：首尾接龙 Python 链 (15分钟)

为了缓解大课前期的沉闷气氛，并顺便复习切片与元组，建议在下堂课开始时进行此项互动：

* **玩法名称**:  “Debug 极速火线”
* **游戏规则**:
  1. 教师在屏幕展示一段故意写错切片步长的 Python 语句（例如：'print("Python"[3:0:-1])' 问会输出什么，或者为什么输出的是空字符）。
  2. 采用小组抢答，获胜的小组需要立即出一道新切片谜题，指名另一个小组作答。
  3. **奖励机制**: 连续答对 3 次的小组，本周编程作业可免除最难的附加编程挑战！
* **成效预期**: 游戏能迅速调动学生对于“边缘细节（Edge cases）”的关注，用活泼的方式突破 Python Array Slicing 的难点。`
      };
    } else {
      // General fallbacks
      return {
        type: 'text',
        content: `收到您的教学任务指令：“${prompt}”。

我已经通过大语言模型进行了评估，针对该要求建议采取以下步骤：
1. **内容聚焦**: 重点结合我们班级当前 **88% 的作业完成度** 和在 **Python Array Slicing** 的薄弱表现，针对性强化该点。
2. **教学建议**: 建议您可以在本节课 workbench 的“已选资料”中，选中《智能教学助手》参考文档，自动融合本学期大纲进行定制。

如果您需要，我可以随时为您**生成小测题**、**更新教学课件方案**，或者**拟写一份具体的汇报邮件**！请直接点击下方 Smart Follow-up 的快捷指令开始。`
      };
    }
  };

  const handleSendMessage = (textToSend?: string, requestedAgentId?: string | null) => {
    const finalMsg = textToSend || inputVal;
    if (!finalMsg.trim()) return;
    setAnalysisActionNotice(null);
    setInputVal('');
    const trimmed = finalMsg.trim();
    const agentId = requestedAgentId !== undefined
      ? requestedAgentId
      : trimmed === '分析学情'
        ? 'learning_analysis'
        : null;
    void sendMessage(finalMsg, agentId);
  };

  const handleQuizAnswer = (questionId: string, optionIdx: number) => {
    setQuizAnswers(prev => ({
      ...prev,
      [questionId]: optionIdx
    }));
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleExportArtifact = async (artifact: Artifact, format: 'markdown' | 'csv') => {
    if (!token) return;
    try {
      const blob = await exportArtifact(token, artifact.id, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${artifact.title || artifact.id}.${format === 'csv' ? 'csv' : 'md'}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setAnalysisActionNotice(reason instanceof Error ? `导出失败：${reason.message}` : '导出失败，请重试。');
    }
  };

  const renderInteractionPanel = () => (
    <TeacherAgentHistoryPanel
      courseContext={courseContext}
      attachments={attachments}
      artifacts={artifacts}
      agentHistory={agentHistory}
      activeAgentId={route?.agentId ?? null}
      activeConversationId={activeConversationId}
      selectedArtifactIds={selectedArtifactIds}
      onToggleArtifact={toggleArtifact}
      onPrompt={handleSendMessage}
      onExport={handleExportArtifact}
      onOpenConversation={(conversationId) => void openConversation(conversationId)}
      isBusy={isAiTyping}
    />
  );
  const learningAnalysisArtifact = [...artifacts].reverse().find((artifact) => artifact.type === 'learning_analysis') ?? null;

  useEffect(() => {
    if (!learningAnalysisArtifact || isAiTyping) return;
    learningAnalysisReportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [chatMessages.length, learningAnalysisArtifact?.id, isAiTyping]);

  return (
    <div className="flex h-screen w-full font-sans antialiased bg-[#EEF3F0] text-on-surface overflow-hidden">
      
      {/* 1. SIDEBAR NAVIGATION */}
      {showCreateCourseDialog && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/25 p-4" role="dialog" aria-modal="true" aria-labelledby="create-course-title">
          <form onSubmit={handleCreateCourse} className="w-full max-w-md rounded-2xl border border-outline-variant bg-surface p-6 shadow-2xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="mb-1 text-[11px] font-bold tracking-widest text-primary">课程空间</p>
                <h2 id="create-course-title" className="font-display text-xl font-extrabold text-on-surface">新建课程</h2>
                <p className="mt-1 text-xs leading-5 text-on-surface-variant">课程资料会在课程下的所有任务中共享。</p>
              </div>
              <button type="button" onClick={() => setShowCreateCourseDialog(false)} className="rounded-lg p-2 text-outline transition-colors hover:bg-surface-container-high hover:text-on-surface" aria-label="关闭新建课程弹窗">×</button>
            </div>
            <label className="block text-xs font-bold text-on-surface" htmlFor="course-name">课程名称</label>
            <input id="course-name" autoFocus value={newCourseName} onChange={(event) => setNewCourseName(event.target.value)} placeholder="例如：Python 程序设计" className="mt-2 w-full rounded-xl border border-outline-variant bg-surface-container-low px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" required />
            <label className="mt-4 block text-xs font-bold text-on-surface" htmlFor="course-description">课程说明 <span className="font-normal text-outline">（可选）</span></label>
            <textarea id="course-description" value={newCourseDescription} onChange={(event) => setNewCourseDescription(event.target.value)} placeholder="补充年级、章节或教学目标" rows={3} className="mt-2 w-full resize-none rounded-xl border border-outline-variant bg-surface-container-low px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setShowCreateCourseDialog(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-on-surface-variant transition-colors hover:bg-surface-container-high">取消</button>
              <button type="submit" disabled={!newCourseName.trim()} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50">创建课程</button>
            </div>
          </form>
        </div>
      )}
      {showDeleteCourseDialog && activeCourse && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-on-surface/30 p-4" role="dialog" aria-modal="true" aria-labelledby="delete-course-title">
          <div className="w-full max-w-md rounded-2xl border border-error/20 bg-surface p-6 shadow-2xl">
            <p className="mb-1 text-[11px] font-bold tracking-widest text-error">危险操作</p>
            <h2 id="delete-course-title" className="font-display text-xl font-extrabold text-on-surface">确认删除课程？</h2>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">将删除“{activeCourse.name}”课程。课程任务会解除课程归属，课程资料也不再作为该课程资料提供。此操作不可撤销。</p>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setShowDeleteCourseDialog(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-on-surface-variant transition-colors hover:bg-surface-container-high">取消</button>
              <button type="button" disabled={isSavingCourse} onClick={() => void handleDeleteCourse()} className="rounded-xl bg-error px-4 py-2.5 text-sm font-semibold text-on-error transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50">确认删除</button>
            </div>
          </div>
        </div>
      )}

      <aside className="fixed left-0 top-0 z-50 hidden h-screen w-72 flex-col border-r border-white/70 bg-surface-container-low/90 px-3 py-4 shadow-[8px_0_30px_rgba(25,28,26,0.04)] backdrop-blur-xl lg:flex">
        
        {/* Header Identity */}
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-white shadow-sm">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-display text-lg font-extrabold text-primary leading-tight">校园智能助手</h1>
            <p className="text-xs text-on-surface-variant font-medium">教师工作台</p>
          </div>
        </div>

        {/* Action Button */}
        <button 
          onClick={() => {
            setStage('welcome');
            clearChat();
          }}
          className="flex items-center justify-center gap-2 w-full py-3 mb-6 bg-primary text-on-primary rounded-xl font-semibold text-sm hover:opacity-95 transition-all active:scale-95 shadow-sm cursor-pointer"
        >
          <MessageSquarePlus className="w-4.5 h-4.5" />
          新建任务
        </button>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1 overflow-y-auto">
          <div className="px-3 py-1 mb-1 text-[11px] text-outline font-bold tracking-wider">导航</div>
          
          <button 
            onClick={() => {
              setStage('welcome');
              clearChat();
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              stage === 'welcome' 
                ? 'text-primary bg-primary-container/10 border-r-4 border-primary' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <MessageSquarePlus className="w-4.5 h-4.5" />
            <span>新建任务</span>
          </button>

          <button 
            onClick={() => startAnalysis()}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              stage === 'report' 
                ? 'text-primary bg-primary-container/10 border-r-4 border-primary' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <History className="w-4.5 h-4.5" />
            <span>最近会话</span>
          </button>

          <div className="mt-5 border-t border-outline-variant pt-4">
            <div className="flex items-center justify-between px-3 py-1">
              <span className="text-[11px] text-outline font-bold tracking-wider">课程</span>
              <button type="button" onClick={openCreateCourseDialog} className="rounded p-1 text-primary hover:bg-primary/10" aria-label="新建课程">+</button>
            </div>
            <div className="mt-1 space-y-1">
              {courses.map((course) => {
                const isExpanded = expandedCourseId === course.id;
                const courseTasks = conversations.filter((conversation) => conversation.course_id === course.id);
                return (
                  <div key={course.id}>
                    <button type="button" onClick={() => { setActiveCourseId(course.id); setExpandedCourseId(isExpanded ? null : course.id); clearChat(); }} className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs font-semibold ${activeCourseId === course.id ? 'bg-primary/10 text-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`} aria-expanded={isExpanded}>
                      {isExpanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
                      <BookOpen className="h-3.5 w-3.5 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{course.name}</span>
                      <span className="text-[10px] font-medium text-outline">{courseTasks.length}</span>
                    </button>
                    {isExpanded && (
                      <ConversationHistory conversations={courseTasks} activeConversationId={activeConversationId} onOpen={(id) => { void openConversation(id); }} onDelete={(id) => { void removeConversation(id); }} accentClass="text-primary" compact />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <ConversationHistory conversations={conversations.filter((conversation) => conversation.course_id === null)} activeConversationId={activeConversationId} onOpen={(id) => { void openConversation(id); }} onDelete={(id) => { void removeConversation(id); }} accentClass="text-primary" heading="任务" />
        </nav>

        {/* User Info Section */}
        <div className="mt-auto p-2 bg-surface-container/50 rounded-xl border border-outline-variant flex items-center gap-3">
          <div aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-primary-fixed bg-primary/10 text-sm font-black text-primary">教</div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold truncate">匿名教师</p>
            <p className="text-[10px] text-on-surface-variant truncate font-semibold tracking-wider">独立工作空间</p>
          </div>
          <button type="button" aria-label="更多工作空间选项" className="rounded-lg p-1 text-outline hover:bg-surface-container hover:text-primary"><MoreVertical className="w-4 h-4" /></button>
        </div>
      </aside>

      {/* 2. MAIN WORKSPACE CONTENT */}
      <main className="relative flex min-h-screen flex-1 flex-col overflow-hidden bg-background lg:ml-72">
        {error && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{error}</div>}
        
        {/* Top App Bar */}
        <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-white/70 bg-surface/80 px-10 shadow-[0_1px_20px_rgba(25,28,26,0.04)] backdrop-blur-xl">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1 px-3 py-1 bg-surface-container-high rounded-full border border-outline-variant shadow-xs">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold text-on-surface-variant font-sans">匿名教师工作空间</span>
            </div>
            <div className="hidden sm:flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[10px] font-bold text-primary">
              <BookOpen className="h-3.5 w-3.5" />
              <span>{courseContext.courseName}</span>
              <span className="text-primary/60">·</span>
              <span>{courseContext.workflowName}</span>
            </div>
            
            <nav className="hidden md:flex gap-6">
              <button 
                onClick={() => setActiveTab('workbench')}
                className={`text-sm font-bold pb-1 cursor-pointer transition-colors ${
                  activeTab === 'workbench' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                工作台
              </button>
              <button 
                onClick={() => setActiveTab('resources')}
                className={`text-sm font-bold pb-1 cursor-pointer transition-colors ${
                  activeTab === 'resources' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                资料
              </button>
              <button 
                onClick={openCourseManagement}
                className={`text-sm font-bold pb-1 cursor-pointer transition-colors ${
                  activeTab === 'analytics' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                课程管理
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative hidden lg:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline" />
              <input 
                className="w-64 rounded-full border border-outline-variant bg-surface-container-low/80 py-1.5 pl-10 pr-4 text-xs outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                placeholder="搜索数据指标……" 
                type="text"
              />
            </div>
            <div className="flex items-center gap-2">
              <button type="button" aria-label="查看任务状态" className="p-2 text-on-surface-variant hover:text-primary transition-colors cursor-pointer rounded-full hover:bg-surface-container">
                <Activity className="w-4.5 h-4.5" />
              </button>
              <button type="button" aria-label="查看通知" className="p-2 text-on-surface-variant hover:text-primary transition-colors relative cursor-pointer rounded-full hover:bg-surface-container">
                <Bell className="w-4.5 h-4.5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full border-2 border-surface"></span>
              </button>
              <div className="h-6 w-[1px] bg-outline-variant mx-1"></div>
              
              <button 
                onClick={onBackToRoles}
                className="flex items-center gap-1 px-4 py-2 bg-primary-container text-on-primary-container rounded-full font-semibold text-xs hover:bg-opacity-95 transition-all active:scale-95 cursor-pointer"
              >
                <UserRoundCheck className="w-3.5 h-3.5" />
                 切换角色
              </button>
              <button
                type="button"
                onClick={() => setShowInteractionPanel(true)}
                aria-label="打开智能体历史聚合面板"
                className="inline-flex items-center gap-1 rounded-full border border-outline-variant px-3 py-2 text-xs font-bold text-primary hover:bg-surface-container"
              >
                <FolderClosed className="w-3.5 h-3.5" />智能体历史
              </button>
            </div>
          </div>
        </header>

        {/* Tab content controller */}
        <div className="flex-1 flex overflow-hidden">
          
          {activeTab === 'workbench' ? (
            <div className="flex-1 flex flex-col h-full overflow-hidden">
              {/* Left Column: Interactive Chat & Analysis View */}
              <section ref={chatScrollRef} className="flex-1 flex flex-col p-6 overflow-y-auto max-w-4xl mx-auto w-full space-y-6">
                {analysisActionNotice && <p role="alert" className="rounded-xl border border-tertiary/30 bg-tertiary-container/15 px-4 py-3 text-xs font-bold leading-relaxed text-tertiary">{analysisActionNotice}</p>}
                
                {/* 2A. WELCOME / INITIAL STATE (Screen 2) */}
                {stage === 'welcome' && chatMessages.length === 0 && (
                  <div className="flex-grow flex flex-col items-center justify-center text-center py-10 space-y-8 max-w-2xl mx-auto">
                    <div className="relative w-32 h-32">
                      <div className="absolute inset-0 bg-primary/5 rounded-full animate-pulse"></div>
                      <div className="absolute inset-4 bg-primary/10 rounded-full flex items-center justify-center">
                        <UploadCloud className="w-12 h-12 text-primary" />
                      </div>
                    </div>
                    <div className="space-y-3">
                      <h2 className="font-display text-2xl font-bold text-on-surface">准备开始您的教学辅助任务</h2>
                      <p className="text-sm text-on-surface-variant font-medium">
                        上传一份匿名学情表，先看看班级整体情况。您可以根据分析结果直接进行教学设计。
                      </p>
                    </div>

                    {/* Quick Start Buttons */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full pt-4">
                      <button 
                        onClick={() => startAnalysis('匿名学情表.xlsx')}
                        className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-primary hover:shadow-md transition-all group cursor-pointer"
                      >
                        <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                          <Activity className="w-6 h-6" />
                        </div>
                        <span className="font-bold text-sm text-on-surface">分析学情</span>
                      </button>

                      <button 
                        onClick={() => {
                          handleSendMessage('根据本节课目标生成 Python 练习');
                        }}
                        className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-primary hover:shadow-md transition-all group cursor-pointer"
                      >
                        <div className="w-12 h-12 rounded-full bg-tertiary-container/20 text-tertiary flex items-center justify-center group-hover:scale-105 transition-transform">
                          <Brain className="w-6 h-6" />
                        </div>
                        <span className="font-bold text-sm text-on-surface">生成课堂练习</span>
                      </button>

                      <button 
                        onClick={() => {
                          handleSendMessage('帮我设计一个破冰环节');
                        }}
                        className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-primary hover:shadow-md transition-all group cursor-pointer"
                      >
                        <div className="w-12 h-12 rounded-full bg-primary-container/20 text-primary flex items-center justify-center group-hover:scale-105 transition-transform">
                          <BookOpen className="w-6 h-6" />
                        </div>
                        <span className="font-bold text-sm text-on-surface">设计课堂互动</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* 2B. ANALYSIS ANIMATION STATE (Processing flow) */}
                {stage === 'analyzing' && (
                  <div className="flex-grow flex flex-col items-center justify-center py-16">
                    <div className="w-full max-w-lg space-y-8">
                      {/* Interactive processing bar */}
                      <div className="flex flex-col items-center space-y-2">
                        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center animate-spin">
                          <Sparkles className="w-8 h-8 text-primary" />
                        </div>
                        <h3 className="font-bold text-lg text-primary">智能学情分析引擎正在全力处理中...</h3>
                        <p className="text-xs text-on-surface-variant font-medium">正在读取匿名电子表格并提炼教学薄弱点</p>
                      </div>

                      {/* Horizontal timeline of checklist */}
                      <div className="relative py-8 bg-[#FBFDFB] border border-[#D9E4DF] rounded-2xl px-6 shadow-xs">
                        <div className="absolute top-1/2 left-8 right-8 h-0.5 bg-outline-variant -translate-y-1/2 z-0"></div>
                        <div className="absolute top-1/2 left-8 right-8 h-0.5 bg-primary -translate-y-1/2 z-0 origin-left transition-all duration-500" style={{ width: `${analysisProgress}%` }}></div>
                        
                        <div className="relative z-10 flex justify-between">
                          {[
                            { name: '解析资料', activeStep: 0 },
                            { name: '识别字段', activeStep: 1 },
                            { name: '计算统计', activeStep: 2 },
                            { name: '生成建议', activeStep: 3 },
                          ].map((s, i) => {
                            const isDone = analysisStep >= s.activeStep;
                            return (
                              <div key={i} className="flex flex-col items-center">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                                  isDone ? 'bg-primary text-on-primary scale-110 shadow-sm' : 'bg-surface-container-high text-on-surface-variant'
                                }`}>
                                  {isDone ? <Check className="w-4 h-4 stroke-[3]" /> : i + 1}
                                </div>
                                <span className={`text-xs mt-2 font-bold transition-colors ${
                                  isDone ? 'text-primary' : 'text-on-surface-variant'
                                }`}>{s.name}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Legacy visual mockup retained as a fallback reference, not rendered. */}
                {false && stage === 'report' && (
                  <motion.div 
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="bg-[#FBFDFB] border border-[#D9E4DF] rounded-2xl overflow-hidden shadow-xs w-full"
                  >
                    {/* Card Header */}
                    <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/40">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                          <Activity className="w-4.5 h-4.5" />
                        </div>
                        <h2 className="font-display font-extrabold text-base md:text-lg">班级整体学情分析</h2>
                      </div>
                      <div className="flex items-center gap-1.5 bg-primary/10 text-primary px-3 py-1 rounded-full border border-primary/20">
                        <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
                         <span className="text-[10px] font-extrabold tracking-wider font-sans">已完成</span>
                      </div>
                    </div>

                    {/* Card Body: Bento Grid Layout */}
                    <div className="p-6 grid grid-cols-1 md:grid-cols-12 gap-4">
                      {/* Row 1 Metrics: Attendance */}
                      <div className="col-span-12 sm:col-span-6 md:col-span-3 p-4 bg-surface-container rounded-2xl border border-outline-variant flex flex-col justify-between shadow-xs hover:border-primary/40 transition-colors">
                         <span className="text-xs font-bold text-on-surface-variant font-sans">出勤率</span>
                        <div className="mt-4">
                          <span className="text-3xl font-black text-primary font-display">95%</span>
                          <div className="flex items-center gap-0.5 text-primary-container mt-1">
                            <ChevronUp className="w-3.5 h-3.5" />
                             <span className="text-[10px] font-bold">较上月 2%</span>
                          </div>
                        </div>
                      </div>

                      {/* Engagement Metric */}
                      <div className="col-span-12 sm:col-span-6 md:col-span-3 p-4 bg-surface-container rounded-2xl border border-outline-variant flex flex-col justify-between shadow-xs hover:border-primary/40 transition-colors">
                         <span className="text-xs font-bold text-on-surface-variant font-sans">课堂参与度</span>
                        <div className="mt-4 flex items-end gap-3">
                           <span className="text-3xl font-black text-primary font-display">高</span>
                          <div className="flex gap-0.5 mb-1 items-end">
                            <div className="h-3 w-1 bg-primary rounded-full animate-pulse"></div>
                            <div className="h-5 w-1 bg-primary rounded-full animate-pulse delay-75"></div>
                            <div className="h-6 w-1 bg-primary rounded-full animate-pulse delay-150"></div>
                            <div className="h-4 w-1 bg-primary/40 rounded-full"></div>
                          </div>
                        </div>
                      </div>

                      {/* Homework Completion Metric */}
                      <div className="col-span-12 sm:col-span-6 md:col-span-3 p-4 bg-surface-container rounded-2xl border border-outline-variant flex flex-col justify-between shadow-xs hover:border-primary/40 transition-colors">
                         <span className="text-xs font-bold text-on-surface-variant font-sans">作业完成率</span>
                        <div className="mt-4">
                          <span className="text-3xl font-black text-primary font-display">88%</span>
                          <div className="w-full bg-outline-variant/30 h-1.5 rounded-full mt-3 overflow-hidden">
                            <div className="bg-primary h-full rounded-full w-[88%]"></div>
                          </div>
                        </div>
                      </div>

                      {/* Score Trend Metric */}
                      <div className="col-span-12 sm:col-span-6 md:col-span-3 p-4 bg-surface-container rounded-2xl border border-outline-variant flex flex-col justify-between shadow-xs hover:border-primary/40 transition-colors">
                         <span className="text-xs font-bold text-on-surface-variant font-sans">成绩趋势</span>
                        <div className="mt-4 flex items-center justify-between">
                           <span className="text-3xl font-black text-primary font-display">上升</span>
                          <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <TrendingUp className="w-5 h-5 stroke-[2.5]" />
                          </div>
                        </div>
                      </div>

                      {/* Row 2: Visual High-Fidelity SVG Bar Chart */}
                      <div className="col-span-12 md:col-span-7 bg-[#FBFDFB] border border-[#D9E4DF] p-5 rounded-2xl shadow-xs">
                        <div className="flex justify-between items-center mb-3">
                           <h3 className="font-display font-extrabold text-sm text-on-surface">单元平均成绩</h3>
                           <span className="text-[10px] font-bold text-primary bg-primary-container/20 px-2 py-0.5 rounded-full">第三单元最高</span>
                        </div>
                        
                        {/* Custom Interactive SVG/Flex Chart */}
                        <div className="h-60 flex items-end justify-between px-3 pt-6 gap-4 relative">
                          {[
                             { name: '第一单元', score: 72, height: '72%' },
                             { name: '第二单元', score: 85, height: '85%' },
                             { name: '第三单元', score: 94, height: '94%', active: true },
                             { name: '第四单元', score: 78, height: '78%' },
                             { name: '当前', score: 82, height: '82%' },
                          ].map((bar, idx) => (
                            <div key={idx} className="flex-1 flex flex-col items-center group relative">
                              
                              {/* Hover Floating Tooltip */}
                              <div className="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 bg-inverse-surface text-inverse-on-surface text-[10px] py-1 px-2 rounded-md font-bold shadow-sm whitespace-nowrap">
                                均分: {bar.score}
                              </div>

                              {/* Interactive Bar */}
                              <div 
                                className={`w-full rounded-t-lg transition-all duration-300 relative cursor-pointer ${
                                  bar.active 
                                    ? 'bg-primary shadow-xs' 
                                    : 'bg-primary/20 hover:bg-primary/50'
                                }`}
                                style={{ height: bar.height }}
                              >
                                {bar.active && (
                                  <span className="absolute -top-7 left-1/2 -translate-x-1/2 text-xs font-black text-primary">
                                    94
                                  </span>
                                )}
                              </div>
                              <span className="mt-3 text-[11px] font-bold text-on-surface-variant whitespace-nowrap">{bar.name}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Column 3: Insight Panels */}
                      <div className="col-span-12 md:col-span-5 space-y-4">
                        {/* Weak points */}
                        <div className="bg-surface-container-low border border-outline-variant p-4 rounded-2xl shadow-xs">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="w-1.5 h-4 bg-error rounded-full"></span>
                            <span className="text-xs font-extrabold text-on-surface-variant uppercase tracking-wider">薄弱知识点</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                             <span className="bg-error-container text-on-error-container px-3 py-1 rounded-full font-bold text-xs">Python 数组切片</span>
                             <span className="bg-error-container text-on-error-container px-3 py-1 rounded-full font-bold text-xs">元组不可变性</span>
                             <span className="bg-outline-variant/30 text-on-surface-variant px-3 py-1 rounded-full font-bold text-xs">列表推导式</span>
                          </div>
                        </div>

                        {/* Suggestions */}
                        <div className="bg-surface-container-low border border-outline-variant p-4 rounded-2xl shadow-xs">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="w-1.5 h-4 bg-primary rounded-full"></span>
                            <span className="text-xs font-extrabold text-on-surface-variant uppercase tracking-wider">教学节奏建议</span>
                          </div>
                          <ul className="space-y-3">
                            <li className="flex items-start gap-2.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0"></div>
                              <p className="text-xs text-on-surface-variant leading-relaxed">
                                放慢<strong className="text-on-surface">索引</strong>练习进度；40%的学生对负索引掌握不牢。
                              </p>
                            </li>
                            <li className="flex items-start gap-2.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0"></div>
                              <p className="text-xs text-on-surface-variant leading-relaxed">
                                增加<strong className="text-on-surface">字符串处理</strong>的实践编程时间。
                              </p>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>

                    {/* Card Footer Actions */}
                    <div className="px-6 py-4 bg-surface-container-highest/20 border-t border-outline-variant flex flex-col sm:flex-row justify-between items-center gap-4">
                      <div className="flex items-center gap-5 text-on-surface-variant">
                        <div className="flex items-center gap-1.5">
                          <FileText className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold">数据来源: 匿名学情表.xlsx</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <LinkIcon className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold">引用了 1 份资料</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                        <button type="button" aria-label="导出 Markdown"
                          onClick={() => copyToClipboard('**班级学情分析报告**\n- 出勤率: 95%\n- 作业完成度: 88%\n- 难点: Python Array Slicing, Tuple Immutability', 999)}
                          className="flex items-center gap-1.5 px-4 py-2 border border-outline text-on-surface font-semibold text-xs rounded-xl hover:bg-surface-container-high transition-all active:scale-[0.98] cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" />
                          {copiedIndex === 999 ? '已复制 Markdown' : '导出 Markdown'}
                        </button>
                        <button 
                          onClick={() => handleSendMessage('根据本节课目标生成 Python 练习')}
                          className="flex items-center gap-1.5 px-4 py-2 bg-primary text-on-primary font-semibold text-xs rounded-xl hover:bg-primary-container transition-all active:scale-[0.98] cursor-pointer"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          继续生成课堂练习
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* 2D. RENDER ACTIVE INTERACTIVE CHAT MESSAGES */}
                {chatMessages.length > 0 && (
                  <div className="space-y-6 pt-4 border-t border-outline-variant/50">
                    <div className="text-[10px] text-center tracking-widest uppercase font-bold text-outline">对话进行中</div>
                    {chatMessages.map((msg, index) => {
                      const isUser = msg.sender === 'user';
                      const isLearningAnalysisMessage = isLearningAnalysisArtifactMessage(msg);
                      return (
                        <div key={msg.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                          
                          {/* Assistant Profile picture */}
                          {!isUser && (
                            <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container shrink-0 shadow-sm">
                              <Brain className="w-4 h-4" />
                            </div>
                          )}

                          {/* Message Content Bubble */}
                          <div className={`${isLearningAnalysisMessage ? 'max-w-[98%]' : 'max-w-[85%]'} rounded-2xl px-5 py-4 shadow-xs ${
                            isUser 
                              ? 'bg-primary text-on-primary rounded-tr-none' 
                              : 'bg-[#FBFDFB] text-on-surface rounded-tl-none'
                          }`}>
                            <div className="text-xs opacity-70 mb-1 flex items-center justify-between">
                              <span>{isUser ? '用户（您）' : '校园智能助手'}</span>
                              <span>{msg.timestamp}</span>
                            </div>

                            <div className="text-sm leading-relaxed prose prose-sm max-w-none">
                              {/* Standard text renderer */}
                              {!isLearningAnalysisMessage && msg.type !== 'quiz' && msg.type !== 'plan' ? (
                                <div className="whitespace-pre-line">{msg.content}</div>
                              ) : null}

                              {isLearningAnalysisMessage && (
                                <div ref={learningAnalysisReportRef} className="mt-2">
                                  <LearningAnalysisReport artifact={learningAnalysisArtifact} onCopy={(content) => copyToClipboard(content, 999)} onGenerate={() => handleSendMessage('根据学情分析生成课程迭代方案')} />
                                </div>
                              )}

                              {/* Interactive Quiz renderer */}
                              {msg.type === 'quiz' && (
                                <div className="space-y-4">
                                  <div className="font-bold text-on-surface">{msg.content}</div>
                                  <div className="p-4 bg-surface-container rounded-xl border border-outline-variant space-y-6">
                                    <h4 className="font-bold text-primary flex items-center gap-1.5 border-b border-outline-variant pb-2 text-sm">
                                      <HelpCircle className="w-4.5 h-4.5 text-secondary" />
                                      {msg.metadata.title}
                                    </h4>

                                    {msg.metadata.questions.map((q: any, qIdx: number) => {
                                      const selectedOption = quizAnswers[q.id];
                                      const isCorrect = selectedOption === q.correct;
                                      return (
                                        <div key={q.id} className="space-y-2">
                                          <p className="font-bold text-xs text-on-surface">{q.question}</p>
                                          <div className="grid grid-cols-1 gap-2">
                                            {q.options.map((opt: string, oIdx: number) => {
                                              const isThisOptionSelected = selectedOption === oIdx;
                                              let optionStyle = 'bg-surface-container-lowest border-outline-variant text-on-surface hover:border-primary/50';
                                              if (isThisOptionSelected) {
                                                optionStyle = oIdx === q.correct 
                                                  ? 'bg-primary-container/20 border-primary text-primary font-bold' 
                                                  : 'bg-error-container/20 border-error text-error font-bold';
                                              }
                                              return (
                                                <button
                                                  key={oIdx}
                                                  onClick={() => handleQuizAnswer(q.id, oIdx)}
                                                  className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all cursor-pointer ${optionStyle}`}
                                                >
                                                  {opt}
                                                </button>
                                              );
                                            })}
                                          </div>
                                          {selectedOption !== undefined && (
                                            <div className={`p-3 rounded-lg text-[11px] leading-relaxed border ${
                                              isCorrect ? 'bg-primary-container/15 border-primary-container text-primary-container' : 'bg-error-container/15 border-error-container text-on-error-container'
                                            }`}>
                                              <span className="font-bold">{isCorrect ? '🎉 回答正确！' : '❌ 回答有误。'}</span>
                                              {q.explanation}
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Slide outline renderer */}
                              {msg.type === 'plan' && (
                                <div className="space-y-4">
                                  <div className="font-bold text-on-surface">{msg.content}</div>
                                  <div className="space-y-3">
                                    {msg.metadata.slides.map((slide: any, sIdx: number) => (
                                      <div key={sIdx} className="p-4 bg-surface-container rounded-xl border border-outline-variant">
                                        <h5 className="font-bold text-xs text-primary mb-2 flex items-center gap-1.5">
                                          <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
                                          {slide.title}
                                        </h5>
                                        <ul className="space-y-1.5 pl-4 list-disc text-xs text-on-surface-variant">
                                          {slide.bullets.map((b: string, bIdx: number) => (
                                            <li key={bIdx}>{b}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Easy-copy action for pre-formatted emails or templates */}
                            {!isUser && msg.content.includes('主题') && (
                              <button 
                                onClick={() => copyToClipboard(msg.content, index)}
                                className="mt-3 flex items-center gap-1.5 px-3 py-1.5 bg-surface-container hover:bg-surface-container-high rounded-lg text-xs font-semibold cursor-pointer border border-outline-variant"
                              >
                                <Copy className="w-3.5 h-3.5" />
                                {copiedIndex === index ? '复制成功！' : '复制邮件草稿'}
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {/* AI Thinking Animation */}
                    {isAiTyping && (
                      <div className="flex gap-3 justify-start items-center">
                        <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container shrink-0">
                          <Brain className="w-4 h-4" />
                        </div>
                        <div className="bg-[#FBFDFB] border border-[#D9E4DF] rounded-2xl px-5 py-4 text-xs font-semibold text-on-surface-variant flex items-center gap-2">
                          <span className="animate-pulse">校园智能助手正在梳理教学思路</span>
                          <span className="flex gap-0.5">
                            <span className="w-1 h-1 bg-primary rounded-full animate-bounce"></span>
                            <span className="w-1 h-1 bg-primary rounded-full animate-bounce [animation-delay:0.2s]"></span>
                            <span className="w-1 h-1 bg-primary rounded-full animate-bounce [animation-delay:0.4s]"></span>
                          </span>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                )}

                {/* 2E. SMART FOLLOW-UP AREA (Shown below the main analysis report) */}
                {stage === 'report' && !isAiTyping && (
                  <div className="pt-8 border-t border-outline-variant">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container">
                        <Sparkles className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-display font-extrabold text-sm md:text-base">智能追问</h3>
                        <p className="text-xs text-on-surface-variant font-medium">根据当前分析，我可以继续帮您完成以下任务：</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <button
                        onClick={() => handleSendMessage('针对本次学情分析结果生成一份包含 5 道选择题的针对性小测，并给出评分量规。', 'lesson_design')}
                        className="p-4 bg-white border border-outline-variant rounded-xl text-left hover:border-primary hover:shadow-xs transition-all group cursor-pointer"
                      >
                        <HelpCircle className="w-6 h-6 text-primary mb-2" />
                        <h4 className="font-bold text-xs text-on-surface mb-1">生成针对性小测</h4>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">针对薄弱知识点生成 5 道选择题</p>
                      </button>

                      <button
                        onClick={() => handleSendMessage('结合本次学情分析结果，给出当前课件的更新建议与可视化图表补充点。', 'course_iteration')}
                        className="p-4 bg-white border border-outline-variant rounded-xl text-left hover:border-primary hover:shadow-xs transition-all group cursor-pointer"
                      >
                        <BookOpen className="w-6 h-6 text-primary mb-2" />
                        <h4 className="font-bold text-xs text-on-surface mb-1">更新教学课件</h4>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">自动在索引章节加入可视化图表建议</p>
                      </button>

                      <button
                        onClick={() => handleSendMessage('基于当前学情分析结果，撰写一份发给课程组的学情概况邮件草稿。', 'teaching_report')}
                        className="p-4 bg-white border border-outline-variant rounded-xl text-left hover:border-primary hover:shadow-xs transition-all group cursor-pointer"
                      >
                        <FileText className="w-6 h-6 text-primary mb-2" />
                        <h4 className="font-bold text-xs text-on-surface mb-1">撰写学情概况邮件</h4>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">生成一份发给课程组的汇总报告草稿</p>
                      </button>
                    </div>
                  </div>
                )}
              </section>

              {/* 2F. STATIONARY CHAT INPUT FOOTER AREA */}
              <div className="mt-auto px-10 pb-8 shrink-0 bg-background pt-2 z-10 border-t border-outline-variant/10">
                <div className="max-w-4xl mx-auto space-y-3">
                  
                  {/* Suggestion tags list */}
                  <div className="flex gap-2 mb-2 overflow-x-auto scrollbar-hide py-1">
                    <button 
                      onClick={() => handleSendMessage('根据本节课目标生成 Python 练习')}
                      className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                    >
                      ⚡ 根据本节课目标生成 Python 练习
                    </button>
                    <button 
                      onClick={() => handleSendMessage('帮我设计一个破冰环节')}
                      className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                    >
                      💡 帮我设计一个破冰环节
                    </button>
                    <button 
                      onClick={() => handleSendMessage('总结上周测试的薄弱知识点')}
                      className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                    >
                      📝 总结上周测试的薄弱知识点
                    </button>
                  </div>

                  {/* Primary text entry form */}
                  <div className="bg-[#FBFDFB] rounded-2xl shadow-xs border-2 border-outline-variant focus-within:border-primary transition-all p-3">
                    <textarea 
                      ref={textareaRef}
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      className="w-full bg-transparent border-none outline-none focus:outline-hidden text-sm p-1 resize-none font-sans leading-relaxed text-on-surface scrollbar-hide min-h-[44px]" 
                      placeholder="输入您的教学任务..." 
                      rows={2}
                    />
                    <div className="flex items-center justify-between pt-2 border-t border-outline-variant/35">
                      <div className="flex gap-1">
                        <button type="button" aria-label="上传课堂资料"
                          onClick={() => fileInputRef.current?.click()}
                          className="p-1.5 text-outline hover:text-primary transition-colors rounded-lg hover:bg-surface-container cursor-pointer"
                          title="上传本地 Excel 数据表进行分析"
                        >
                          <Paperclip className="w-4 h-4" />
                        </button>
                        <input ref={fileInputRef} type="file" className="hidden" accept=".txt,.md,.docx,.pdf,.xlsx,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadFile(file, courseContext.courseId ? 'workspace' : 'conversation'); event.currentTarget.value = ''; }} />
                        <button type="button" aria-label="录音输入" className="p-1.5 text-outline hover:text-primary transition-colors rounded-lg hover:bg-surface-container cursor-pointer">
                          <Mic className="w-4 h-4" />
                        </button>
                        <button type="button" aria-label="添加图片" className="p-1.5 text-outline hover:text-primary transition-colors rounded-lg hover:bg-surface-container cursor-pointer">
                          <ImageIcon className="w-4 h-4" />
                        </button>
                      </div>
                      
                      <button 
                        onClick={() => isAiTyping ? stopStreaming() : handleSendMessage()}
                        className="bg-primary text-on-primary px-5 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer hover:bg-primary-container shadow-sm"
                      >
                        <span>{isAiTyping ? '停止生成' : '发送任务'}</span>
                        {isAiTyping ? <span className="h-3 w-3 rounded-sm bg-on-primary" /> : <Send className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                  <p className="text-[10px] text-center text-outline">智能生成内容仅供参考，请结合实际教学情况进行调整。</p>
                </div>
              </div>
            </div>
          ) : null}

          {/* Fallback tabs (Resources and Analytics mockup states) */}
          {activeTab === 'resources' && (
            <div className="mx-auto flex-1 max-w-5xl space-y-6 overflow-y-auto p-10">
              <div className="flex items-start justify-between gap-6">
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-primary">{courseContext.courseName}</p>
                  <h2 className="mt-1 font-display text-xl font-black text-primary">课程资料库</h2>
                  <p className="mt-2 text-xs font-medium leading-relaxed text-on-surface-variant">这里只显示当前课程和通用资料，其他课程的文件不会出现在这里。支持 TXT、Markdown、DOCX、PDF、XLSX 和 CSV，单个文件不超过 25 MB。</p>
                </div>
                <div className="shrink-0">
                  <button
                    type="button"
                    disabled={!courseContext.courseId || isUploadingCourseMaterial}
                    onClick={() => courseMaterialInputRef.current?.click()}
                    className="flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-extrabold text-on-primary shadow-sm transition hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <UploadCloud className="h-4 w-4" />
                    {isUploadingCourseMaterial ? '上传中…' : '上传课程资料'}
                  </button>
                  <input
                    ref={courseMaterialInputRef}
                    type="file"
                    className="hidden"
                    accept=".txt,.md,.docx,.pdf,.xlsx,.csv"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) void handleCourseMaterialUpload(file);
                      event.currentTarget.value = '';
                    }}
                  />
                </div>
              </div>

              {visibleCourseAttachments.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-outline-variant bg-white/70 px-6 py-12 text-center shadow-xs">
                  <FolderOpen className="mx-auto h-8 w-8 text-outline" />
                  <p className="mt-3 text-sm font-extrabold text-on-surface">当前课程暂无资料</p>
                  <p className="mt-1 text-xs text-on-surface-variant">上传课程资料后，它们会自动出现在这里。</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {visibleCourseAttachments.map((attachment) => {
                    const learningTable = isLearningTable(attachment);
                    const ready = ['indexed', 'degraded'].includes(attachment.status);
                    return (
                      <article key={attachment.id} className="group space-y-3 rounded-2xl border border-outline-variant bg-white p-5 shadow-xs transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${learningTable ? 'bg-secondary/10 text-secondary' : 'bg-primary/10 text-primary'}`}>
                          {learningTable ? <FileSpreadsheet className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                        </div>
                        <div className="min-w-0">
                          <h4 className="truncate text-xs font-extrabold text-on-surface" title={attachment.filename}>{attachment.filename}</h4>
                          <p className="mt-1 text-[10px] text-on-surface-variant">{attachment.scope === 'workspace' ? '课程资料' : '当前任务附件'} · {attachment.status === 'indexed' ? '已完成解析' : attachment.status === 'degraded' ? '已完成解析（降级）' : attachment.status === 'parsing' ? '解析中' : attachment.status === 'failed' ? '解析失败' : '等待处理'}</p>
                          {attachment.status === 'failed' && attachment.status_message && (
                            <p className="mt-1 truncate text-[10px] font-medium text-error" title={attachment.status_message}>失败原因：{attachment.status_message}</p>
                          )}
                        </div>
                        {learningTable && (
                          <button type="button" disabled={!ready} onClick={() => startAnalysis(attachment.filename)} className="text-xs font-extrabold text-primary transition-colors hover:text-primary-container disabled:cursor-not-allowed disabled:text-outline">
                            {ready ? '回到工作台进行学情分析 →' : '资料解析完成后可分析'}
                          </button>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="mx-auto flex-1 max-w-3xl space-y-6 overflow-y-auto p-10">
              <div>
                <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-primary">课程空间</p>
                <h2 className="mt-1 font-display text-xl font-black text-primary">课程管理</h2>
                <p className="mt-2 text-xs font-medium leading-relaxed text-on-surface-variant">修改当前课程名称，或删除不再使用的课程。删除前会再次确认。</p>
              </div>
              {!activeCourse ? (
                <div className="rounded-2xl border border-dashed border-outline-variant bg-white/70 px-6 py-12 text-center shadow-xs">
                  <BookOpen className="mx-auto h-8 w-8 text-outline" />
                  <p className="mt-3 text-sm font-extrabold text-on-surface">暂无课程</p>
                  <p className="mt-1 text-xs text-on-surface-variant">请先创建课程，再进行课程管理。</p>
                  <button type="button" onClick={openCreateCourseDialog} className="mt-4 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary">新建课程</button>
                </div>
              ) : (
                <div className="rounded-2xl border border-outline-variant bg-white p-6 shadow-xs">
                  <form onSubmit={handleRenameCourse}>
                    <label className="block text-xs font-bold text-on-surface" htmlFor="manage-course-name">课程名称</label>
                    <input id="manage-course-name" value={editingCourseName} onChange={(event) => setEditingCourseName(event.target.value)} className="mt-2 w-full rounded-xl border border-outline-variant bg-surface-container-low px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" maxLength={160} required />
                    <div className="mt-5 flex justify-end">
                      <button type="submit" disabled={isSavingCourse || !editingCourseName.trim() || editingCourseName.trim() === activeCourse.name} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50">保存名称</button>
                    </div>
                  </form>
                  <div className="mt-8 border-t border-outline-variant pt-5">
                    <h3 className="text-sm font-extrabold text-error">删除课程</h3>
                    <p className="mt-1 text-xs leading-5 text-on-surface-variant">删除课程后，相关任务将不再归属于该课程。</p>
                    <button type="button" onClick={() => setShowDeleteCourseDialog(true)} className="mt-3 rounded-xl border border-error/40 px-4 py-2.5 text-sm font-semibold text-error transition-colors hover:bg-error-container/40">删除“{activeCourse.name}”</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 3. RIGHT PANEL: course-scoped agent history and the active workflow. */}
          {showInteractionPanel && (
            <aside className="w-96 h-full border-l border-outline-variant bg-surface-container-low flex flex-col overflow-y-auto shrink-0 hidden xl:flex">
              <div className="flex h-12 items-center justify-between border-b border-outline-variant px-4 shrink-0">
                <p className="text-sm font-extrabold text-on-surface">智能体历史聚合</p>
                <button type="button" onClick={() => setShowInteractionPanel(false)} aria-label="关闭智能体历史面板" className="rounded-lg px-2 py-1 text-xs font-bold text-outline hover:bg-surface-container">关闭</button>
              </div>
              <div className="flex-1 overflow-y-auto">{renderInteractionPanel()}</div>
            </aside>
          )}

          <AnimatePresence>
          {showInteractionPanel && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} className="fixed inset-0 z-[60] bg-on-surface/25 backdrop-blur-sm xl:hidden" role="dialog" aria-modal="true" aria-label="智能体历史聚合面板" onClick={() => setShowInteractionPanel(false)}>
              <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', bounce: 0, duration: 0.42 }} className="absolute right-0 top-0 h-full w-full max-w-md border-l border-white/70 bg-surface/90 shadow-2xl backdrop-blur-xl" onClick={(event) => event.stopPropagation()}>
                <div className="flex h-12 items-center justify-between border-b border-outline-variant px-4">
                  <p className="text-sm font-extrabold text-on-surface">智能体历史聚合</p>
                  <button type="button" onClick={() => setShowInteractionPanel(false)} aria-label="关闭课堂互动面板" className="rounded-lg px-2 py-1 text-xs font-bold text-outline hover:bg-surface-container">关闭</button>
                </div>
                <div className="h-[calc(100%-3rem)] overflow-y-auto">{renderInteractionPanel()}</div>
               </motion.div>
            </motion.div>
          )}
          </AnimatePresence>

        </div>
      </main>

    </div>
  );
}

function isLearningAnalysisArtifactMessage(message: Message): boolean {
  if (message.sender !== 'assistant') return false;
  if (Array.isArray(message.metadata) && message.metadata.some((item) => (
    item && typeof item === 'object' && (item as Record<string, unknown>).type === 'learning_analysis'
  ))) return true;
  return message.content.trimStart().startsWith('# 班级整体学情分析');
}

function LearningAnalysisReport({
  artifact,
  onCopy,
  onGenerate,
}: {
  artifact: Artifact | null
  onCopy: (content: string) => void
  onGenerate: () => void
}) {
  const data = artifact?.data ?? {}
  const attendance = asRecord(data.attendance)
  const activity = asRecord(data.activity)
  const trend = asRecord(data.trend)
  const relationships = asRecord(data.relationships)
  const assignments = asRecordList(data.assignments)
  const weakPoints = asRecordList(data.weak_points)
  const bands = asRecordList(relationships.attendance_bands)
  const diagnosis = asStringList(data.teaching_diagnosis)
  const strategies = asStringList(data.iteration_strategy)
  const attendanceRate = percentValue(attendance.rate)
  const assignmentAverage = percentValue(relationships.assignment_score_average)
  const finalAverage = percentValue(relationships.final_score_average)
  const activityAverage = numberValue(activity.average)
  const correlations = asRecordList(relationships.correlations)
  const assignmentsForChart = assignments.filter((item) => numberValue(item.average_percent) !== null)
  const maxAssignment = Math.max(100, ...assignmentsForChart.map((item) => numberValue(item.average_percent) ?? 0))
  const chartBarColors = ['bg-primary/55', 'bg-secondary/60', 'bg-tertiary/60', 'bg-[#4F8FA8]/60', 'bg-[#C87864]/60']
  const correlationTints = ['bg-primary/5', 'bg-secondary/10', 'bg-tertiary/10']
  const bandColors = ['bg-primary', 'bg-secondary', 'bg-tertiary', 'bg-[#4F8FA8]']
  const markdown = artifact?.content || '学情分析结果尚未同步。'

  return (
    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full overflow-hidden rounded-2xl bg-[#FBFDFB] shadow-sm">
      <div className="flex items-center justify-between bg-surface-container-low/40 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary"><Activity className="h-4.5 w-4.5" /></div>
          <div><h2 className="font-display text-base font-extrabold md:text-lg">班级整体学情分析</h2><p className="mt-0.5 text-[10px] text-on-surface-variant">多维指标、关联关系与课程迭代证据</p></div>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[10px] font-extrabold tracking-wider text-primary"><span className="h-2 w-2 animate-pulse rounded-full bg-primary" />已完成</span>
      </div>

      {!artifact ? (
        <div className="p-8 text-center text-xs text-outline">正在同步学情分析结果…</div>
      ) : (
        <div className="space-y-4 p-5 md:p-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <AnalysisMetric label="出勤率" value={formatPercent(attendanceRate)} hint={`${numberValue(attendance.sessions) ?? 0} 个考勤观测`} valueClass="text-primary" />
            <AnalysisMetric label="作业得分率" value={formatPercent(assignmentAverage)} hint="全部作业均值" valueClass="text-secondary" />
            <AnalysisMetric label="期末成绩" value={formatPercent(finalAverage)} hint={typeof relationships.final_score_field === 'string' ? relationships.final_score_field : '未识别期末字段'} valueClass="text-tertiary" />
            <AnalysisMetric label="课堂参与度" value={activityAverage === null ? '—' : activityAverage.toFixed(1)} hint={activity.scale === '5-point' ? '五级量表' : '课堂观测均值'} valueClass="text-[#4F8FA8]" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-7">
            <section className="rounded-2xl bg-white p-4 shadow-xs lg:col-span-4">
              <div className="mb-3 flex items-center justify-between"><div><h3 className="text-sm font-extrabold">作业与知识点成绩</h3><p className="mt-0.5 text-[10px] text-on-surface-variant">横向比较各次作业得分率，识别难度拐点</p></div><span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-bold text-primary">{assignmentsForChart.length} 项测评</span></div>
              {assignmentsForChart.length === 0 ? <EmptyAnalysis text="未识别到可视化作业成绩" /> : <div className="flex h-56 items-end gap-2 px-2 pb-0 pt-5">{assignmentsForChart.map((item, index) => { const score = numberValue(item.average_percent) ?? 0; const barColor = chartBarColors[index % chartBarColors.length]; return <div key={`${String(item.name)}-${index}`} className="group flex h-full min-w-0 flex-1 flex-col items-center justify-end"><div className="relative flex w-full max-w-14 flex-1 items-end"><span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-black text-primary opacity-0 transition-opacity group-hover:opacity-100">{score.toFixed(0)}%</span><div className={`w-full rounded-t-lg ${barColor} transition-all group-hover:opacity-80`} style={{ height: `${Math.max(4, score / maxAssignment * 100)}%` }} /></div><span className="mt-2 line-clamp-2 w-full text-center text-[9px] font-bold text-on-surface-variant">{String(item.name ?? '测评')}</span></div> })}</div>}
            </section>

            <section className="rounded-2xl bg-white p-4 shadow-xs lg:col-span-3">
              <div className="mb-3 flex items-center justify-between"><div><h3 className="text-sm font-extrabold">成绩趋势</h3><p className="mt-0.5 text-[10px] text-on-surface-variant">从首项测评到末项测评</p></div><TrendingUp className="h-5 w-5 text-primary" /></div>
              <div className="flex items-center gap-3 rounded-xl bg-surface-container-low p-3"><span className={`text-2xl font-black ${trend.direction === 'declining' ? 'text-error' : 'text-primary'}`}>{trend.direction === 'improving' ? '上升' : trend.direction === 'declining' ? '下降' : trend.direction === 'stable' ? '稳定' : '—'}</span><span className="text-xs leading-relaxed text-on-surface-variant">变化幅度：{numberValue(trend.delta) === null ? '数据不足' : `${numberValue(trend.delta)?.toFixed(1)} 个百分点`}</span></div>
              <div className="mt-4 space-y-2">{weakPoints.length > 0 ? weakPoints.map((item, index) => <div key={`${String(item.name)}-${index}`} className="flex items-center justify-between gap-2 text-[10px]"><span className="truncate font-bold text-on-surface-variant">薄弱点 · {String(item.name ?? '未命名')}</span><span className="shrink-0 font-black text-error">{formatPercent(numberValue(item.average_percent))}</span></div>) : <EmptyAnalysis text="暂无薄弱点" />}</div>
            </section>
          </div>

          <section className="rounded-2xl bg-primary/5 p-4">
            <div className="mb-3 flex items-center justify-between"><div><h3 className="text-sm font-extrabold">出勤率与学习结果关系</h3><p className="mt-0.5 text-[10px] text-on-surface-variant">按匿名数据分组聚合，避免展示学生个体画像</p></div><span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold text-primary">相关性分析</span></div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">{correlations.map((item, index) => { const coefficient = numberValue(item.coefficient); const tint = correlationTints[index % correlationTints.length]; const valueColor = coefficient !== null && coefficient >= 0.3 ? 'text-primary' : coefficient !== null && coefficient <= -0.3 ? 'text-error' : 'text-secondary'; return <div key={`${String(item.x)}-${String(item.y)}-${index}`} className={`rounded-xl ${tint} p-3 shadow-xs`}><p className="text-[10px] font-bold text-on-surface-variant">{String(item.x ?? '')} × {String(item.y ?? '')}</p><p className={`mt-1 text-2xl font-black ${valueColor}`}>{coefficient === null ? '—' : coefficient.toFixed(2)}</p><p className="mt-1 text-[10px] leading-relaxed text-outline">{String(item.interpretation ?? '样本不足')} · n={String(item.sample_count ?? 0)}</p></div> })}</div>
            {bands.length > 0 && <div className="mt-4 rounded-xl bg-white p-3 shadow-xs"><p className="mb-3 text-[10px] font-extrabold text-on-surface-variant">不同出勤区间的结果对比</p><div className="space-y-2.5">{bands.map((band, index) => <div key={`${String(band.label)}-${index}`} className="grid grid-cols-[7rem_1fr_3rem] items-center gap-2 text-[10px]"><span className="truncate font-bold text-on-surface-variant">{String(band.label ?? '')}</span><div className="h-2 overflow-hidden rounded-full bg-surface-container-high"><div className={`h-full rounded-full ${bandColors[index % bandColors.length]}`} style={{ width: `${Math.min(100, Math.max(0, percentValue(band.final_score_rate) ?? percentValue(band.assignment_score_rate) ?? 0))}%` }} /></div><span className="text-right font-black text-primary">{formatPercent(percentValue(band.final_score_rate) ?? percentValue(band.assignment_score_rate))}</span></div>)}</div></div>}
          </section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <InsightPanel title="教学问题诊断" tone="error" items={diagnosis.length > 0 ? diagnosis : ['暂无足够数据形成教学问题诊断。']} />
            <InsightPanel title="后续课程迭代策略" tone="primary" items={strategies.length > 0 ? strategies : ['继续跟踪出勤、作业得分率和阶段成绩的联动变化。']} />
          </div>
        </div>
      )}

      <details className="bg-surface-container-low/50 px-5 py-3 md:px-6">
        <summary className="cursor-pointer list-none text-xs font-bold text-primary marker:hidden">
          <span className="inline-flex items-center gap-1.5">展开文本分析 <ChevronDown className="h-3.5 w-3.5" /></span>
        </summary>
        <div className="mt-3 max-h-72 overflow-y-auto whitespace-pre-wrap rounded-xl bg-white p-4 text-xs leading-6 text-on-surface-variant shadow-xs">
          {markdown}
        </div>
      </details>

      <div className="flex flex-col items-center justify-between gap-3 bg-surface-container-highest/20 px-5 py-4 sm:flex-row md:px-6"><div className="flex items-center gap-1.5 text-[10px] font-semibold text-on-surface-variant"><FileText className="h-4 w-4 text-primary" />数据来源：当前课程全部资料</div><div className="flex w-full items-center justify-end gap-2 sm:w-auto"><button type="button" onClick={() => onCopy(markdown)} className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-high"><Copy className="h-3.5 w-3.5" />复制报告</button><button type="button" onClick={onGenerate} className="flex items-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-on-primary hover:bg-primary-container"><Sparkles className="h-3.5 w-3.5" />生成课程迭代方案</button></div></div>
    </motion.div>
  )
}

function AnalysisMetric({ label, value, hint, valueClass }: { label: string; value: string; hint: string; valueClass: string }) {
  return <div className="rounded-2xl bg-surface-container p-3 shadow-xs"><p className="text-[10px] font-bold text-on-surface-variant">{label}</p><p className={`mt-2 text-2xl font-black ${valueClass}`}>{value}</p><p className="mt-1 truncate text-[9px] text-outline">{hint}</p></div>
}

function InsightPanel({ title, items, tone }: { title: string; items: string[]; tone: 'error' | 'primary' }) {
  return <section className="rounded-2xl bg-surface-container-low p-4 shadow-xs"><div className="mb-3 flex items-center gap-2"><span className={`h-4 w-1.5 rounded-full ${tone === 'error' ? 'bg-error' : 'bg-primary'}`} /><h3 className="text-xs font-extrabold tracking-wider text-on-surface-variant">{title}</h3></div><ul className="space-y-2.5">{items.map((item, index) => <li key={`${item}-${index}`} className="flex items-start gap-2 text-xs leading-relaxed text-on-surface-variant"><span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${tone === 'error' ? 'bg-error' : 'bg-primary'}`} />{item}</li>)}</ul></section>
}

function EmptyAnalysis({ text }: { text: string }) {
  return <div className="flex h-full min-h-24 items-center justify-center text-xs italic text-outline">{text}</div>
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function asRecordList(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object' && !Array.isArray(item))) : []
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : []
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function percentValue(value: unknown): number | null {
  const number = numberValue(value)
  if (number === null) return null
  return number <= 1 ? number * 100 : number
}

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)}%`
}
