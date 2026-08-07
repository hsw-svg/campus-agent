import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  GraduationCap,
  BookOpen,
  BookOpenCheck,
  History,
  FolderOpen,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  ShieldCheck,
  Search,
  Activity,
  Bell,
  UserRoundCheck,
  Send,
  Paperclip,
  Mic,
  Image as ImageIcon,
  Compass,
  FileText,
  HelpCircle,
  Sparkles,
  ClipboardList,
  CheckCircle,
  Copy,
  Newspaper,
  LibraryBig,
  CircleCheckBig,
  FileUser
} from 'lucide-react';
import { motion } from 'motion/react';
import {
  completeCourseChapter,
  downloadBlob,
  exportArtifact,
  getCourseDetail,
  initializeDefaultCourses,
  startCourse,
  startCourseChapter,
  type Artifact,
  type CourseDetail,
  type CourseSummary,
} from '../api';
import { Message } from '../types';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import ConversationHistory from './ConversationHistory';
import ResourcePicker from './ResourcePicker';
import CampusNewsPanel from './CampusNewsPanel';
import CourseCenterPanel from './CourseCenterPanel';
import CourseDetailPanel from './CourseDetailPanel';
import ResumeAssistantPanel from './ResumeAssistantPanel';
import DeepTutorBookPanel from './DeepTutorBookPanel';
import DeepTutorLearningSpacePanel from './DeepTutorLearningSpacePanel';

interface StudentWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

type StudentSection = 'learning' | 'courses' | 'course-detail' | 'campus' | 'resume' | 'learning-space' | 'deep-tutor';

export default function StudentWorkspace({ token, onBackToRoles }: StudentWorkspaceProps) {
  const [activeSection, setActiveSection] = useState<StudentSection>('learning');
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [courseDetail, setCourseDetail] = useState<CourseDetail | null>(null);
  const [learningCourse, setLearningCourse] = useState<CourseDetail | null>(null);
  const [learningChapterId, setLearningChapterId] = useState<string | null>(null);
  const [courseLoading, setCourseLoading] = useState(false);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [deepTutorBookId, setDeepTutorBookId] = useState('');
  const [deepTutorPageId, setDeepTutorPageId] = useState('');
  const courseLoadAttemptedRef = useRef(false);
  const learningChapter = learningCourse?.chapters.find((chapter) => chapter.id === learningChapterId) ?? null;
  const courseContext = useMemo(() => learningCourse ? {
    courseId: learningCourse.id,
    courseName: learningCourse.name,
    chapterId: learningChapter?.id ?? null,
    chapterName: learningChapter?.title ?? '课程学习',
    workflowId: 'student-course-learning',
    workflowName: '课程学习',
  } : undefined, [learningChapter?.id, learningChapter?.title, learningCourse]);

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
    citations,
    selectedAttachmentIds,
    selectedArtifactIds,
    toggleAttachment,
    toggleArtifact,
    stopStreaming,
    retryLastMessage,
    runStatus,
    toolStatus,
    route,
  } = useWorkspaceChat(token, courseContext);
  const [inputVal, setInputVal] = useState('');
  const [copied, setCopied] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputVal]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAiTyping]);

  const handleSendMessage = (textToSend?: string) => {
    const finalMsg = textToSend || inputVal;
    if (!finalMsg.trim()) return;
    setInputVal('');
    void sendMessage(finalMsg);
  };

  const refreshCourses = useCallback(async () => {
    if (!token) return
    courseLoadAttemptedRef.current = true
    setCourseLoading(true)
    setCourseError(null)
    try {
      setCourses(await initializeDefaultCourses(token))
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '课程加载失败，请稍后重试。')
    } finally {
      setCourseLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (activeSection === 'courses' && courses.length === 0 && !courseLoadAttemptedRef.current) {
      void refreshCourses()
    }
  }, [activeSection, courses.length, refreshCourses])

  const showCourseCenter = () => {
    setActiveSection('courses')
    setCourseDetail(null)
  }

  const openCourseDetail = async (course: CourseSummary) => {
    if (!token) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = await getCourseDetail(token, course.id)
      setCourseDetail(detail)
      setActiveSection('course-detail')
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '课程详情加载失败。')
    } finally {
      setCourseLoading(false)
    }
  }

  const enterCourseLearning = async (course: CourseSummary | CourseDetail, chapterId?: string) => {
    if (!token) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = chapterId
        ? await startCourseChapter(token, course.id, chapterId)
        : await startCourse(token, course.id)
      const nextChapterId = chapterId ?? detail.current_chapter_id ?? detail.chapters[0]?.id ?? null
      clearChat()
      setLearningCourse(detail)
      setLearningChapterId(nextChapterId)
      setCourseDetail(detail)
      setCourses((current) => current.map((item) => item.id === detail.id ? detail : item))
      setActiveSection('learning')
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '无法开始课程学习。')
    } finally {
      setCourseLoading(false)
    }
  }

  const finishCurrentChapter = async () => {
    if (!token || !learningCourse || !learningChapterId || isAiTyping) return
    setCourseLoading(true)
    setCourseError(null)
    try {
      const detail = await completeCourseChapter(token, learningCourse.id, learningChapterId)
      clearChat()
      setLearningCourse(detail)
      setLearningChapterId(detail.current_chapter_id)
      setCourseDetail(detail)
      setCourses((current) => current.map((item) => item.id === detail.id ? detail : item))
    } catch (reason) {
      setCourseError(reason instanceof Error ? reason.message : '章节进度保存失败。')
    } finally {
      setCourseLoading(false)
    }
  }

  const copyText = (txt: string) => {
    navigator.clipboard.writeText(txt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportArtifact = async (artifact: Artifact, format: 'markdown' | 'csv') => {
    if (!token) return;
    try {
      const blob = await exportArtifact(token, artifact.id, format);
      downloadBlob(blob, `${artifact.title || artifact.id}.${format === 'csv' ? 'csv' : 'md'}`);
      setExportError(null);
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : '成果导出失败，请稍后重试。');
    }
  };

  const resourcePicker = (
    <ResourcePicker
      attachments={attachments}
      artifacts={artifacts}
      citations={citations}
      selectedAttachmentIds={selectedAttachmentIds}
      selectedArtifactIds={selectedArtifactIds}
      accentClass="text-secondary"
      onToggleAttachment={toggleAttachment}
      onToggleArtifact={toggleArtifact}
      onExport={handleExportArtifact}
    />
  );

  return (
    <div className="flex h-screen w-full font-sans antialiased bg-background text-on-surface overflow-hidden">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className={`fixed left-0 top-0 z-50 flex h-screen w-72 flex-col border-r border-outline-variant bg-surface-container-low py-4 px-3 transition-transform duration-300 ${sidebarCollapsed ? '-translate-x-full' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-white shadow-sm">
            <BookOpen className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-display text-lg font-extrabold text-secondary leading-tight">智汇校园</h1>
            <p className="text-xs text-on-surface-variant font-medium">学生工作台</p>
          </div>
          <button type="button" aria-label="折叠侧边栏" onClick={() => setSidebarCollapsed(true)} className="rounded-lg p-1.5 text-outline transition-all duration-200 hover:bg-surface-container hover:text-secondary">
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        <button 
          onClick={() => {
            setLearningCourse(null);
            setLearningChapterId(null);
            setActiveSection('learning');
            clearChat();
          }}
          className="flex items-center justify-center gap-2 w-full py-3 mb-6 bg-secondary text-on-secondary rounded-xl font-semibold text-sm hover:opacity-95 transition-all active:scale-95 shadow-sm cursor-pointer"
        >
          <Compass className="w-4.5 h-4.5" />
          新建学习任务
        </button>

        <nav className="flex-1 space-y-1 overflow-y-auto">
          <div className="px-3 py-1 mb-1 text-[11px] text-outline font-bold tracking-wider">菜单</div>
          
          <button 
            onClick={() => {
              if (learningCourse) {
                clearChat();
                setLearningCourse(null);
                setLearningChapterId(null);
              }
              setActiveSection('learning');
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'learning'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <Compass className="w-4.5 h-4.5" />
            <span>学习中心</span>
          </button>

          <button
            type="button"
            onClick={showCourseCenter}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'courses' || activeSection === 'course-detail'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <LibraryBig className="w-4.5 h-4.5" />
            <span>课程中心</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('learning-space')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'learning-space'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <Sparkles className="w-4.5 h-4.5" />
            <span>学习空间</span>
          </button>

          <button
            type="button"
            onClick={() => { setDeepTutorBookId(''); setDeepTutorPageId(''); setActiveSection('deep-tutor') }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'deep-tutor'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <BookOpenCheck className="w-4.5 h-4.5" />
            <span>交互教材</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('campus')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'campus'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <Newspaper className="w-4.5 h-4.5" />
            <span>校园中心</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('resume')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              activeSection === 'resume'
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <FileUser className="w-4.5 h-4.5" />
            <span>简历助手</span>
          </button>

          <ConversationHistory
            conversations={conversations.filter((conversation) => conversation.agent_id !== 'resume_helper' && (learningCourse
              ? conversation.course_id === learningCourse.id && conversation.chapter_id === learningChapterId
              : conversation.course_id === null))}
            activeConversationId={activeConversationId}
            onOpen={(id) => { setActiveSection('learning'); void openConversation(id); }}
            onDelete={(id) => { void removeConversation(id); }}
            accentClass="text-secondary"
          />
        </nav>

        {/* User Info */}
        <div className="mt-auto p-2 bg-surface-container/50 rounded-xl border border-outline-variant flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-sm shrink-0 border border-outline-variant">
            学生
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold truncate">学生用户</p>
            <p className="text-[10px] text-on-surface-variant truncate font-semibold tracking-wider">本科生</p>
          </div>
          <MoreVertical className="w-4 h-4 text-outline cursor-pointer hover:text-secondary" />
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className={`flex-1 flex flex-col bg-background min-h-screen pb-16 lg:pb-0 relative overflow-hidden transition-[margin-left] duration-300 ${sidebarCollapsed ? 'lg:ml-0' : 'lg:ml-72'}`}>
        {activeSection === 'learning' && (error || exportError) && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{error || exportError}</div>}
        {activeSection === 'learning' && courseError && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{courseError}</div>}
        {activeSection === 'learning' && (toolStatus || route || runStatus === 'failed' || runStatus === 'needs_input') && (
          <div className="mx-10 mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-secondary/20 bg-secondary-container/10 px-4 py-2 text-xs text-on-surface-variant">
            {toolStatus && <span className="font-semibold text-secondary">{toolStatus}</span>}
            {route?.agentName && <span>当前智能体：{route.agentName}</span>}
            {(runStatus === 'failed' || runStatus === 'needs_input') && !isAiTyping && (
              <button type="button" onClick={retryLastMessage} className="rounded-lg border border-secondary/30 px-2.5 py-1 font-bold text-secondary hover:bg-secondary-container/25">重试上一次任务</button>
            )}
          </div>
        )}
        
        {/* Top App Bar */}
        <header className="sticky top-0 z-40 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-10 shrink-0">
          <div className="flex items-center gap-3">
            {sidebarCollapsed && (
              <button
                type="button"
                onClick={() => setSidebarCollapsed(false)}
                aria-label="展开侧边栏"
                className="rounded-lg p-2 text-secondary transition-all duration-200 hover:bg-surface-container"
              >
                <PanelLeftOpen className="w-5 h-5" />
              </button>
            )}
            <div className="flex items-center gap-1 px-3 py-1 bg-surface-container-high rounded-full border border-outline-variant shadow-xs">
              <ShieldCheck className="w-4 h-4 text-secondary" />
              <span className="text-xs font-bold text-on-surface-variant">安全学生工作空间</span>
            </div>
          </div>

          <button 
            onClick={onBackToRoles}
            className="flex items-center gap-1 px-4 py-2 bg-secondary-container text-on-secondary-container rounded-full font-semibold text-xs hover:bg-opacity-95 transition-all active:scale-95 cursor-pointer"
          >
            <UserRoundCheck className="w-3.5 h-3.5" />
            切换角色
          </button>
        </header>

        {/* Chat / Workbench layout */}
        <div className="flex-1 flex overflow-hidden">
          
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            <section className={`flex-1 flex flex-col overflow-y-auto mx-auto w-full ${
              activeSection === 'resume'
                ? 'max-w-none p-3 sm:p-4 xl:overflow-hidden xl:p-0'
                : `space-y-6 p-4 sm:p-6 ${activeSection === 'campus' || activeSection === 'courses' || activeSection === 'course-detail' || activeSection === 'learning-space' || activeSection === 'deep-tutor' ? 'max-w-7xl' : 'max-w-4xl'}`
            }`}>

            {activeSection === 'resume' && <ResumeAssistantPanel token={token} />}

            {activeSection === 'campus' && (
              <div className="w-full py-4 sm:py-8">
                <CampusNewsPanel />
              </div>
            )}

            {activeSection === 'learning-space' && (
              <DeepTutorLearningSpacePanel
                token={token}
                onOpenBooks={(bookId, pageId) => {
                  setDeepTutorBookId(bookId ?? '')
                  setDeepTutorPageId(pageId ?? '')
                  setActiveSection('deep-tutor')
                }}
              />
            )}

            {activeSection === 'deep-tutor' && <DeepTutorBookPanel token={token} initialBookId={deepTutorBookId} initialPageId={deepTutorPageId} />}

            {activeSection === 'courses' && (
              <CourseCenterPanel
                courses={courses}
                loading={courseLoading}
                error={courseError}
                onRetry={() => { void refreshCourses() }}
                onOpen={(course) => { void openCourseDetail(course) }}
                onStart={(course) => { void enterCourseLearning(course) }}
              />
            )}

            {activeSection === 'course-detail' && courseDetail && (
              <CourseDetailPanel
                course={courseDetail}
                loading={courseLoading}
                onBack={showCourseCenter}
                onStart={(chapterId) => { void enterCourseLearning(courseDetail, chapterId) }}
              />
            )}

            {activeSection === 'learning' && learningCourse && learningChapter && (
              <div className="flex flex-col gap-3 rounded-2xl border border-secondary/25 bg-secondary-container/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">当前课程 · {learningCourse.progress_percent}%</p>
                  <p className="mt-1 truncate text-sm font-black text-on-surface">{learningCourse.name} · {learningChapter.title}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" onClick={() => { setCourseDetail(learningCourse); setActiveSection('course-detail') }} className="rounded-xl border border-secondary/25 px-3 py-2 text-[11px] font-black text-secondary hover:bg-secondary-container/20">
                    查看课程详情
                  </button>
                  <button type="button" disabled={courseLoading || isAiTyping} onClick={() => { void finishCurrentChapter() }} className="inline-flex items-center gap-1.5 rounded-xl bg-secondary px-3 py-2 text-[11px] font-black text-on-secondary disabled:opacity-50">
                    <CircleCheckBig className="h-4 w-4" />完成本节学习
                  </button>
                </div>
              </div>
            )}

            {activeSection === 'learning' && chatMessages.length === 0 && (
              <div className="flex-grow flex flex-col items-center text-center py-6 space-y-6 max-w-4xl mx-auto w-full">
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 bg-secondary/5 rounded-full animate-pulse"></div>
                  <div className="absolute inset-3 bg-secondary/10 rounded-full flex items-center justify-center">
                    <BookOpen className="w-8 h-8 text-secondary" />
                  </div>
                </div>
                <div className="space-y-3">
                  <h2 className="font-display text-2xl font-bold text-on-surface">{learningCourse ? `开始学习「${learningChapter?.title ?? learningCourse.name}」` : '开启你的学术与学习智能陪伴'}</h2>
                  <p className="text-sm text-on-surface-variant font-medium animate-fade-in">
                    {learningCourse ? '围绕当前章节提问、上传资料或生成练习，完成后记得记录本节进度。' : '输入你的学术难点、复习章节，或点击下方的智能引擎快捷入口，自动为你制定冲刺大纲！'}
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
                  <button 
                    onClick={() => handleSendMessage('论文辅助：生成计算机大模型相关大纲')}
                    className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-2xl flex items-center justify-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <FileText className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">论文辅助</span>
                  </button>

                  <button 
                    onClick={() => handleSendMessage('知识问答：Python 列表与元组的深度区别')}
                    className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-2xl flex items-center justify-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <HelpCircle className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">知识问答</span>
                  </button>

                  <button 
                    onClick={() => handleSendMessage('课程总结：自动生成 Python 复习备考冲刺计划')}
                    className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-2xl flex items-center justify-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <ClipboardList className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">课程总结</span>
                  </button>
                </div>
              </div>
            )}

            {activeSection === 'learning' && chatMessages.length > 0 && (
              <div className="space-y-6">
                {chatMessages.map((msg, idx) => {
                  const isUser = msg.sender === 'user';
                  return (
                    <div key={msg.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      {!isUser && (
                        <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container shrink-0 border border-outline-variant">
                          <BookOpen className="w-4 h-4" />
                        </div>
                      )}
                      
                      <div className={`max-w-[85%] rounded-2xl px-5 py-4 shadow-xs ${
                        isUser 
                          ? 'bg-secondary text-on-secondary rounded-tr-none' 
                          : 'bg-surface-container-lowest border border-outline-variant/60 text-on-surface rounded-tl-none'
                      }`}>
                        <div className="text-xs opacity-70 mb-1 flex items-center justify-between">
                          <span>{isUser ? '学生（您）' : '学生智能助手'}</span>
                          <span>{msg.timestamp}</span>
                        </div>
                        <div className="text-sm leading-relaxed whitespace-pre-line prose prose-sm max-w-none">
                          {msg.content}
                        </div>
                        
                        {!isUser && (
                          <button 
                            onClick={() => copyText(msg.content)}
                            className="mt-3 flex items-center gap-1 px-3 py-1.5 bg-surface-container hover:bg-surface-container-high rounded-lg text-xs font-semibold cursor-pointer border border-outline-variant"
                          >
                            <Copy className="w-3.5 h-3.5" />
                            {copied ? '复制成功！' : '复制资料方案'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}

                {isAiTyping && (
                  <div className="flex gap-3 justify-start items-center">
                    <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container shrink-0">
                      <BookOpen className="w-4 h-4" />
                    </div>
                    <div className="bg-surface-container-lowest border border-outline-variant/60 rounded-2xl px-5 py-4 text-xs font-semibold text-on-surface-variant flex items-center gap-2">
                      <span className="animate-pulse">学生智能助手正在提炼课程纲领与要点</span>
                      <span className="flex gap-0.5">
                        <span className="w-1 h-1 bg-secondary rounded-full animate-bounce"></span>
                        <span className="w-1 h-1 bg-secondary rounded-full animate-bounce [animation-delay:0.2s]"></span>
                        <span className="w-1 h-1 bg-secondary rounded-full animate-bounce [animation-delay:0.4s]"></span>
                      </span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </section>

          {/* Input Footer */}
          {activeSection === 'learning' && chatMessages.length > 0 && <div className="px-6 pb-3 xl:hidden">{resourcePicker}</div>}
          {activeSection === 'learning' && <div className="mt-auto px-10 pb-8 shrink-0 bg-background pt-2 border-t border-outline-variant/10 z-10">
            <div className="max-w-4xl mx-auto space-y-3">
              <div className="flex gap-2 overflow-x-auto scrollbar-hide py-1">
                <button 
                  onClick={() => handleSendMessage('论文辅助：生成计算机大模型相关大纲')}
                  className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                >
                  📝 论文大纲构思
                </button>
                <button 
                  onClick={() => handleSendMessage('知识问答：Python 列表与元组的深度区别')}
                  className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                >
                  💡 算法概念答疑
                </button>
                <button 
                  onClick={() => handleSendMessage('课程总结：自动生成 Python 复习备考冲刺计划')}
                  className="whitespace-nowrap px-3 py-1 bg-surface-container hover:bg-surface-container-high text-[11px] font-bold text-on-surface-variant border border-outline-variant rounded-full transition-colors cursor-pointer"
                >
                  📅 期末复习冲刺
                </button>
              </div>

              <div className="bg-surface-container-lowest rounded-2xl shadow-xs border-2 border-outline-variant focus-within:border-secondary transition-all p-3">
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
                  className="w-full bg-transparent border-none outline-none focus:outline-hidden text-sm p-1 resize-none font-sans leading-relaxed text-on-surface min-h-[44px] scrollbar-hide" 
                  placeholder="提问你的学术盲点或概念..." 
                  rows={2}
                />
                <div className="flex items-center justify-between pt-2 border-t border-outline-variant/35">
                  <div className="flex gap-1">
                    <button onClick={() => fileInputRef.current?.click()} className="p-1.5 text-outline hover:text-secondary transition-colors rounded-lg hover:bg-surface-container cursor-pointer">
                      <Paperclip className="w-4 h-4" />
                    </button>
                    <input ref={fileInputRef} type="file" className="hidden" accept=".txt,.md,.docx,.pdf,.xlsx,.csv" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadFile(file); event.currentTarget.value = ''; }} />
                    <button className="p-1.5 text-outline hover:text-secondary transition-colors rounded-lg hover:bg-surface-container cursor-pointer">
                      <Mic className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <button 
                    onClick={() => isAiTyping ? stopStreaming() : handleSendMessage()}
                    className="bg-secondary text-on-secondary px-5 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer hover:bg-opacity-95 shadow-sm"
                  >
                    <span>{isAiTyping ? '停止生成' : '发送指令'}</span>
                    {isAiTyping ? <span className="h-3 w-3 rounded-sm bg-on-secondary" /> : <Send className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>}
          </div>

          {/* Right sidebar */}
          {activeSection === 'learning' && <aside className="w-80 h-full border-l border-outline-variant bg-surface-container-low flex flex-col p-4 gap-6 overflow-y-auto shrink-0 hidden xl:flex">
            {resourcePicker}
            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider px-1">学习备考资料袋</h3>
              <div className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-xl space-y-2">
                <p className="text-xs font-bold text-on-surface">我的期末复习档案</p>
                <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                  <CheckCircle className="w-4 h-4 text-secondary" />
                  <span>Python 切片练习：已刷 3 次</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                  <CheckCircle className="w-4 h-4 text-secondary" />
                  <span>大一元组内存测试：完美掌握</span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-on-surface-variant tracking-wider px-1">智能学习辅导进度</h3>
              <div className="bg-surface-container-lowest border border-outline-variant/60 p-4 rounded-xl space-y-2">
                <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                  <div className="h-full bg-secondary w-2/3"></div>
                </div>
                <p className="text-[10px] text-outline">今天已学习 2/3 的难点。继续加油！</p>
              </div>
            </div>
          </aside>}

        </div>
      </main>

      <nav className="fixed inset-x-3 bottom-3 z-50 grid grid-cols-6 rounded-2xl border border-outline-variant bg-surface-container-lowest/95 p-1.5 shadow-xl backdrop-blur lg:hidden" aria-label="学生端主导航">
        <button type="button" onClick={() => { clearChat(); setLearningCourse(null); setLearningChapterId(null); setActiveSection('learning') }} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'learning' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <Compass className="h-4 w-4" />学习
        </button>
        <button type="button" onClick={showCourseCenter} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'courses' || activeSection === 'course-detail' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <LibraryBig className="h-4 w-4" />课程
        </button>
        <button type="button" onClick={() => setActiveSection('learning-space')} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'learning-space' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <Sparkles className="h-4 w-4" />空间
        </button>
        <button type="button" onClick={() => { setDeepTutorBookId(''); setDeepTutorPageId(''); setActiveSection('deep-tutor') }} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'deep-tutor' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <BookOpenCheck className="h-4 w-4" />教材
        </button>
        <button type="button" onClick={() => setActiveSection('campus')} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'campus' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <Newspaper className="h-4 w-4" />校园
        </button>
        <button type="button" onClick={() => setActiveSection('resume')} className={`flex flex-col items-center gap-1 rounded-xl py-2 text-[10px] font-black ${activeSection === 'resume' ? 'bg-secondary text-on-secondary' : 'text-on-surface-variant'}`}>
          <FileUser className="h-4 w-4" />简历
        </button>
      </nav>

    </div>
  );
}
