import { useState, useEffect, useRef } from 'react';
import { 
  GraduationCap, 
  MessageSquarePlus, 
  History, 
  FolderOpen, 
  Settings, 
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
  ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { exportArtifact, type Artifact, type Attachment, type CourseContext } from '../api';
import { Role, Message } from '../types';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import ClassroomInteractionPanel from './ClassroomInteractionPanel';
import ConversationHistory from './ConversationHistory';

interface TeacherWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

const TEACHER_COURSE_CONTEXT: CourseContext = {
  courseId: 'python-programming',
  courseName: 'Python 程序设计',
  workflowId: 'learning-analysis-to-activity',
  workflowName: '学情分析 → 课堂活动包',
};

function isLearningTable(attachment: Attachment): boolean {
  return /\.(csv|xlsx?|xls)$/i.test(attachment.filename)
    || /csv|spreadsheet|excel/i.test(attachment.content_type);
}

export default function TeacherWorkspace({ token, onBackToRoles }: TeacherWorkspaceProps) {
  // States: 'welcome' | 'analyzing' | 'report'
  const [stage, setStage] = useState<'welcome' | 'analyzing' | 'report'>('welcome');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'workbench' | 'resources' | 'analytics'>('workbench');
  const [showInteractionPanel, setShowInteractionPanel] = useState(false);

  // Interactive Quiz State
  const [quizAnswers, setQuizAnswers] = useState<Record<string, number>>({});
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Chat/Input states
  const [inputVal, setInputVal] = useState('');
  const [exportError, setExportError] = useState<string | null>(null);
  const [analysisActionNotice, setAnalysisActionNotice] = useState<string | null>(null);
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
    selectedAttachmentIds,
    selectedArtifactIds,
    toggleAttachment,
    toggleArtifact,
    stopStreaming,
    retryLastMessage,
    runStatus,
    route,
    toolStatus,
  } = useWorkspaceChat(token, TEACHER_COURSE_CONTEXT);
  const [progressBarWidth, setProgressBarWidth] = useState('w-0');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatScrollRef = useRef<HTMLElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const startAnalysis = (_fileName?: string) => {
    setActiveTab('workbench');
    const selected = attachments.filter((attachment) => selectedAttachmentIds.includes(attachment.id));
    const selectedTable = selected.length === 1 && isLearningTable(selected[0]);
    if (!selectedTable) {
      setAnalysisActionNotice('请先在右侧资料选择中勾选一份可用的匿名学情表。');
      return;
    }
    if (!['indexed', 'degraded'].includes(selected[0].status)) {
      setAnalysisActionNotice('该资料仍在解析中，请等待状态变为“可用”后再分析。');
      return;
    }
    setAnalysisActionNotice(null);
    void sendMessage('分析学情');
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

  const handleSendMessage = (textToSend?: string) => {
    const finalMsg = textToSend || inputVal;
    if (!finalMsg.trim()) return;
    setAnalysisActionNotice(null);
    setInputVal('');
    void sendMessage(finalMsg);
  };

  const handleExportArtifact = async (artifact: Artifact, format: 'markdown' | 'csv') => {
    if (!token) return;
    try {
      const blob = await exportArtifact(token, artifact.id, format);
      setExportError(null);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${artifact.title || artifact.id}.${format === 'csv' ? 'csv' : 'md'}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setExportError(reason instanceof Error ? `导出失败：${reason.message}` : '导出失败，请重试。');
    }
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

  const renderInteractionPanel = () => (
    <ClassroomInteractionPanel
      attachments={attachments}
      artifacts={artifacts}
      selectedAttachmentIds={selectedAttachmentIds}
      selectedArtifactIds={selectedArtifactIds}
      onToggleAttachment={toggleAttachment}
      onToggleArtifact={toggleArtifact}
      onPrompt={handleSendMessage}
      onUpload={(file) => uploadFile(file, 'workspace')}
      onExport={handleExportArtifact}
      onStop={stopStreaming}
      onRetry={retryLastMessage}
      isBusy={isAiTyping}
      runStatus={runStatus}
      toolStatus={toolStatus}
      error={exportError}
      route={route}
    />
  );

  return (
    <div className="flex h-screen w-full font-sans antialiased bg-[#EEF3F0] text-on-surface overflow-hidden">
      
      {/* 1. SIDEBAR NAVIGATION */}
      <aside className="fixed left-0 top-0 z-50 hidden h-screen w-72 flex-col border-r border-outline-variant bg-surface-container-low px-3 py-4 lg:flex">
        
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
            setUploadedFile(null);
          }}
          className="flex items-center justify-center gap-2 w-full py-3 mb-6 bg-primary text-on-primary rounded-xl font-semibold text-sm hover:opacity-95 transition-all active:scale-95 shadow-sm cursor-pointer"
        >
          <MessageSquarePlus className="w-4.5 h-4.5" />
          新建对话
        </button>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1 overflow-y-auto">
          <div className="px-3 py-1 mb-1 text-[11px] text-outline font-bold tracking-wider">导航</div>
          
          <button 
            onClick={() => {
              setStage('welcome');
              clearChat();
              setUploadedFile(null);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              stage === 'welcome' 
                ? 'text-primary bg-primary-container/10 border-r-4 border-primary' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <MessageSquarePlus className="w-4.5 h-4.5" />
            <span>新建对话</span>
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

          <a className="flex items-center gap-3 px-3 py-2.5 text-on-surface-variant font-semibold text-sm rounded-lg hover:bg-surface-container-high transition-colors" href="#">
            <FolderOpen className="w-4.5 h-4.5" />
            <span>工作空间资料库</span>
          </a>

          <a className="flex items-center gap-3 px-3 py-2.5 text-on-surface-variant font-semibold text-sm rounded-lg hover:bg-surface-container-high transition-colors" href="#">
            <Settings className="w-4.5 h-4.5" />
            <span>设置</span>
          </a>

          <ConversationHistory conversations={conversations} activeConversationId={activeConversationId} onOpen={(id) => { void openConversation(id); setStage('welcome'); }} onDelete={(id) => { void removeConversation(id); }} accentClass="text-primary" />
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
        <header className="sticky top-0 z-40 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-10 shrink-0">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1 px-3 py-1 bg-surface-container-high rounded-full border border-outline-variant shadow-xs">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <span className="text-xs font-bold text-on-surface-variant font-sans">匿名教师工作空间</span>
            </div>
            <div className="hidden sm:flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[10px] font-bold text-primary">
              <BookOpen className="h-3.5 w-3.5" />
              <span>{TEACHER_COURSE_CONTEXT.courseName}</span>
              <span className="text-primary/60">·</span>
              <span>{TEACHER_COURSE_CONTEXT.workflowName}</span>
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
                onClick={() => setActiveTab('analytics')}
                className={`text-sm font-bold pb-1 cursor-pointer transition-colors ${
                  activeTab === 'analytics' ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                数据分析
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative hidden lg:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline" />
              <input 
                className="bg-surface-container-low border border-outline-variant rounded-full py-1.5 pl-10 pr-4 text-xs w-64 focus:outline-hidden focus:ring-2 focus:ring-primary/20" 
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
                aria-label="打开课堂互动面板"
                className="inline-flex items-center gap-1 rounded-full border border-outline-variant px-3 py-2 text-xs font-bold text-primary hover:bg-surface-container xl:hidden"
              >
                <FolderClosed className="w-3.5 h-3.5" />课堂互动
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
                          setUploadedFile('课堂互动备课案.xlsx');
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
                          setUploadedFile('破冰互动表.xlsx');
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

                {/* 2C. DYNAMIC BENTO-GRID ANALYSIS REPORT (Screen 3) */}
                {stage === 'report' && (
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
                      return (
                        <div key={msg.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                          
                          {/* Assistant Profile picture */}
                          {!isUser && (
                            <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-container shrink-0 shadow-sm">
                              <Brain className="w-4 h-4" />
                            </div>
                          )}

                          {/* Message Content Bubble */}
                          <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-xs ${
                            isUser 
                              ? 'bg-primary text-on-primary rounded-tr-none' 
                              : 'bg-[#FBFDFB] border border-[#D9E4DF] text-on-surface rounded-tl-none'
                          }`}>
                            <div className="text-xs opacity-70 mb-1 flex items-center justify-between">
                              <span>{isUser ? '用户（您）' : '校园智能助手'}</span>
                              <span>{msg.timestamp}</span>
                            </div>

                            <div className="text-sm leading-relaxed prose prose-sm max-w-none">
                              {/* Standard text renderer */}
                              {msg.type !== 'quiz' && msg.type !== 'plan' ? (
                                <div className="whitespace-pre-line">{msg.content}</div>
                              ) : null}

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
                        onClick={() => handleSendMessage('生成针对性小测')}
                        className="p-4 bg-white border border-outline-variant rounded-xl text-left hover:border-primary hover:shadow-xs transition-all group cursor-pointer"
                      >
                        <HelpCircle className="w-6 h-6 text-primary mb-2" />
                        <h4 className="font-bold text-xs text-on-surface mb-1">生成针对性小测</h4>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">针对 Python 切片知识点生成 5 道选择题</p>
                      </button>

                      <button 
                        onClick={() => handleSendMessage('更新教学课件')}
                        className="p-4 bg-white border border-outline-variant rounded-xl text-left hover:border-primary hover:shadow-xs transition-all group cursor-pointer"
                      >
                        <BookOpen className="w-6 h-6 text-primary mb-2" />
                        <h4 className="font-bold text-xs text-on-surface mb-1">更新教学课件</h4>
                        <p className="text-[11px] text-on-surface-variant leading-relaxed">自动在索引章节加入可视化图表建议</p>
                      </button>

                      <button 
                        onClick={() => handleSendMessage('撰写学情概况邮件')}
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
                        <input ref={fileInputRef} type="file" className="hidden" accept=".csv,.xlsx,.xls,.pdf,.doc,.docx,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) { setUploadedFile(file.name); void uploadFile(file); } event.currentTarget.value = ''; }} />
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
            <div className="flex-1 p-10 overflow-y-auto max-w-5xl mx-auto space-y-6">
              <h2 className="text-xl font-black font-display text-primary">备课资料库</h2>
              <p className="text-xs text-on-surface-variant font-medium">在这里，你可以存储和调取你的教案、讲义、大纲与班级学生名册。</p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-5 bg-white border border-outline-variant rounded-2xl shadow-xs space-y-3">
                  <div className="w-10 h-10 bg-primary/10 text-primary flex items-center justify-center rounded-xl">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-xs">匿名学情表.xlsx</h4>
                  <p className="text-[11px] text-on-surface-variant">包含平时考核出勤率与知识点得分。</p>
                  <button onClick={() => { setActiveTab('workbench'); startAnalysis('匿名学情表.xlsx'); }} className="text-xs text-primary font-bold hover:underline">立即调阅分析 →</button>
                </div>

                <div className="p-5 bg-white border border-outline-variant rounded-2xl shadow-xs space-y-3">
                  <div className="w-10 h-10 bg-secondary/10 text-secondary flex items-center justify-center rounded-xl">
                    <FileText className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-xs">Python高级函数教案.docx</h4>
                          <p className="text-[11px] text-on-surface-variant">包含切片、高阶函数（映射、筛选、归约）等案例。</p>
                  <button className="text-xs text-primary font-bold hover:underline">编辑教案 →</button>
                </div>

                <div className="p-5 bg-white border border-outline-variant rounded-2xl shadow-xs space-y-3">
                  <div className="w-10 h-10 bg-tertiary-container/20 text-tertiary flex items-center justify-center rounded-xl">
                    <GraduationCap className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-xs">大一班课程教学大纲.pdf</h4>
                  <p className="text-[11px] text-on-surface-variant">2026年春季最新修订版。</p>
                  <button className="text-xs text-primary font-bold hover:underline">查看大纲 →</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="flex-1 p-10 overflow-y-auto max-w-5xl mx-auto space-y-6">
              <h2 className="text-xl font-black font-display text-primary">班级学术仪表盘</h2>
              <p className="text-xs text-on-surface-variant font-medium">自动跟踪本学期教学大纲各章节的及格率、学生参与度以及高频薄弱知识点。</p>
              
              <div className="bg-white border border-outline-variant rounded-2xl p-6 shadow-xs space-y-4">
                <h3 className="font-bold text-sm">学期学情总体曲线</h3>
                <div className="h-48 bg-surface-container/30 border border-dashed border-outline-variant rounded-xl flex items-center justify-center">
                  <span className="text-xs text-outline italic">加载历史均分走势图...</span>
                </div>
              </div>
            </div>
          )}

          {/* 3. RIGHT PANEL (RESOURCE SLOTS / PERSISTENT FILE STATUS) */}
          <aside className="w-96 h-full border-l border-outline-variant bg-surface-container-low flex flex-col overflow-y-auto shrink-0 hidden xl:flex">
            {renderInteractionPanel()}

            <div className="hidden">
            
            {/* Library Container */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">工作区资料库</h3>
                <button 
                  onClick={() => startAnalysis('自定义课堂数据表_A.xlsx')}
                  className="w-6 h-6 rounded-md hover:bg-surface-container-high flex items-center justify-center text-outline cursor-pointer"
                  title="添加备课资料"
                >
                  +
                </button>
              </div>

              {/* Upload Drop Container */}
              <div 
                onClick={() => startAnalysis('匿名学情档案_期中考.xlsx')}
                className="bg-[#FBFDFB] border-2 border-dashed border-outline rounded-2xl p-6 flex flex-col items-center justify-center text-center space-y-3 opacity-80 cursor-pointer hover:border-primary hover:opacity-100 transition-all shadow-xs"
              >
                <FolderClosed className="w-8 h-8 text-outline" />
                <p className="text-[11px] text-on-surface-variant leading-relaxed">
                  <strong>暂无本地资料</strong><br/>
                  点击上传或拖拽文件到此处
                </p>
              </div>
            </div>

            {/* Current Attachments */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">当前对话附件</h3>
              </div>
              <div className="space-y-2">
                {uploadedFile ? (
                  <div className="p-3 bg-white border border-outline-variant rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileSpreadsheet className="w-4 h-4 text-primary shrink-0" />
                      <div className="min-w-0">
                        <p className="text-xs font-bold truncate text-on-surface">{uploadedFile}</p>
                        <p className="text-[9px] text-outline">18.4 KB • 电子表格文件</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => setUploadedFile(null)} 
                      className="text-xs text-outline hover:text-error hover:font-black px-1.5 py-0.5 rounded-sm hover:bg-surface-container-high font-bold cursor-pointer"
                    >
                      移除
                    </button>
                  </div>
                ) : (
                  <div className="px-4 py-6 rounded-xl bg-surface-container-high/40 flex flex-col items-center justify-center border border-outline-variant/30">
                    <p className="text-xs text-outline italic">无附件</p>
                  </div>
                )}
              </div>
            </div>

            {/* Task Selections */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">本次任务已选资料</h3>
              </div>
              <div className="p-3 bg-secondary-container/10 border border-secondary/20 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-secondary/10 flex items-center justify-center">
                    <GraduationCap className="w-5 h-5 text-secondary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-extrabold text-secondary truncate">智能教学助手</p>
                    <p className="text-[10px] text-on-surface-variant">已准备好根据资料生成内容</p>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Process Status Card */}
            <div className="mt-auto">
              <div className="bg-[#FBFDFB] border border-[#D9E4DF] p-4 rounded-xl space-y-2 shadow-xs">
                <p className="text-[11px] font-bold text-on-surface-variant">智能处理进度</p>
                <div className="h-1 w-full bg-surface-container-high rounded-full overflow-hidden">
                  <div className={`h-full bg-primary transition-all duration-700 ${
                    stage === 'analyzing' ? 'w-2/3' : stage === 'report' ? 'w-full' : 'w-0'
                  }`}></div>
                </div>
                <p className="text-[10px] text-outline">
                  {stage === 'analyzing' 
                    ? '处理中 - 正在统计得分走势' 
                    : stage === 'report' 
                    ? '已就绪 - 等待追问指令' 
                    : '空闲中 - 等待输入指令'
                  }
                </p>
              </div>
            </div>
            </div>
          </aside>

          {showInteractionPanel && (
            <div className="fixed inset-0 z-[60] bg-on-surface/25 xl:hidden" role="dialog" aria-modal="true" aria-label="课堂互动面板" onClick={() => setShowInteractionPanel(false)}>
              <div className="absolute right-0 top-0 h-full w-full max-w-md bg-surface shadow-2xl" onClick={(event) => event.stopPropagation()}>
                <div className="flex h-12 items-center justify-between border-b border-outline-variant px-4">
                  <p className="text-sm font-extrabold text-on-surface">课堂互动面板</p>
                  <button type="button" onClick={() => setShowInteractionPanel(false)} aria-label="关闭课堂互动面板" className="rounded-lg px-2 py-1 text-xs font-bold text-outline hover:bg-surface-container">关闭</button>
                </div>
                <div className="h-[calc(100%-3rem)] overflow-y-auto">{renderInteractionPanel()}</div>
              </div>
            </div>
          )}

        </div>
      </main>

    </div>
  );
}
