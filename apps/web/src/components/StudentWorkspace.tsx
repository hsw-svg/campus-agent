import { useState, useRef, useEffect } from 'react';
import { 
  GraduationCap, 
  BookOpen, 
  History, 
  FolderOpen, 
  Settings, 
  MoreVertical, 
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
  Award, 
  HelpCircle, 
  Bookmark, 
  Sparkles,
  ClipboardList,
  CheckCircle,
  Copy
} from 'lucide-react';
import { motion } from 'motion/react';
import { Message } from '../types';
import { useWorkspaceChat } from '../hooks/useWorkspaceChat';
import ConversationHistory from './ConversationHistory';

interface StudentWorkspaceProps {
  token: string | null;
  onBackToRoles: () => void;
}

export default function StudentWorkspace({ token, onBackToRoles }: StudentWorkspaceProps) {
  const { chatMessages, isAiTyping, sendMessage, clearChat, uploadFile, error, conversations, activeConversationId, openConversation, removeConversation } = useWorkspaceChat(token);
  const [inputVal, setInputVal] = useState('');
  const [copied, setCopied] = useState(false);
  
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

  const copyText = (txt: string) => {
    navigator.clipboard.writeText(txt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex h-screen w-full font-sans antialiased bg-[#EEF3F0] text-on-surface overflow-hidden">
      
      {/* SIDEBAR NAVIGATION */}
      <aside className="h-screen w-72 flex flex-col fixed left-0 top-0 bg-surface-container-low border-r border-outline-variant py-4 px-3 z-50">
        <div className="flex items-center gap-3 px-2 mb-6">
          <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center text-white shadow-sm">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-display text-lg font-extrabold text-secondary leading-tight">校园智能助手</h1>
            <p className="text-xs text-on-surface-variant font-medium">学生工作台</p>
          </div>
        </div>

        <button 
          onClick={() => {
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
            onClick={clearChat}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left font-semibold text-sm transition-all duration-200 cursor-pointer ${
              chatMessages.length === 0 
                ? 'text-secondary bg-secondary-container/10 border-r-4 border-secondary' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <Compass className="w-4.5 h-4.5" />
            <span>学习中心</span>
          </button>

          <a className="flex items-center gap-3 px-3 py-2.5 text-on-surface-variant font-semibold text-sm rounded-lg hover:bg-surface-container-high transition-colors" href="#">
            <Award className="w-4.5 h-4.5" />
            <span>成绩与分析</span>
          </a>

          <a className="flex items-center gap-3 px-3 py-2.5 text-on-surface-variant font-semibold text-sm rounded-lg hover:bg-surface-container-high transition-colors" href="#">
            <Bookmark className="w-4.5 h-4.5" />
            <span>收藏笔记</span>
          </a>

          <a className="flex items-center gap-3 px-3 py-2.5 text-on-surface-variant font-semibold text-sm rounded-lg hover:bg-surface-container-high transition-colors" href="#">
            <Settings className="w-4.5 h-4.5" />
            <span>设置</span>
          </a>

          <ConversationHistory conversations={conversations} activeConversationId={activeConversationId} onOpen={(id) => { void openConversation(id); }} onDelete={(id) => { void removeConversation(id); }} accentClass="text-secondary" />
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
      <main className="ml-72 flex-1 flex flex-col bg-background min-h-screen relative overflow-hidden">
        {error && <div role="alert" className="mx-10 mt-3 rounded-xl border border-error/30 bg-error-container px-4 py-2 text-xs text-on-error-container">{error}</div>}
        
        {/* Top App Bar */}
        <header className="sticky top-0 z-40 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-10 shrink-0">
          <div className="flex items-center gap-3">
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
            <section className="flex-1 flex flex-col p-6 overflow-y-auto max-w-4xl mx-auto w-full space-y-6">
            
            {chatMessages.length === 0 && (
              <div className="flex-grow flex flex-col items-center justify-center text-center py-10 space-y-8 max-w-2xl mx-auto">
                <div className="relative w-32 h-32">
                  <div className="absolute inset-0 bg-secondary/5 rounded-full animate-pulse"></div>
                  <div className="absolute inset-4 bg-secondary/10 rounded-full flex items-center justify-center">
                    <BookOpen className="w-12 h-12 text-secondary" />
                  </div>
                </div>
                <div className="space-y-3">
                  <h2 className="font-display text-2xl font-bold text-on-surface">开启你的学术与学习智能陪伴</h2>
                  <p className="text-sm text-on-surface-variant font-medium animate-fade-in">
                    输入你的学术难点、复习章节，或点击下方的智能引擎快捷入口，自动为你制定冲刺大纲！
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full pt-4">
                  <button 
                    onClick={() => handleSendMessage('论文辅助：生成计算机大模型相关大纲')}
                    className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <FileText className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">论文辅助</span>
                  </button>

                  <button 
                    onClick={() => handleSendMessage('知识问答：Python 列表与元组的深度区别')}
                    className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <HelpCircle className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">知识问答</span>
                  </button>

                  <button 
                    onClick={() => handleSendMessage('课程总结：自动生成 Python 复习备考冲刺计划')}
                    className="bg-[#FBFDFB] border border-[#D9E4DF] p-6 rounded-2xl flex flex-col items-center gap-3 hover:border-secondary hover:shadow-md transition-all group cursor-pointer text-center"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-container/30 text-secondary flex items-center justify-center group-hover:scale-105 transition-transform">
                      <ClipboardList className="w-6 h-6" />
                    </div>
                    <span className="font-bold text-sm text-on-surface">课程总结</span>
                  </button>
                </div>
              </div>
            )}

            {chatMessages.length > 0 && (
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
                          : 'bg-[#FBFDFB] border border-[#D9E4DF] text-on-surface rounded-tl-none'
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
                    <div className="bg-[#FBFDFB] border border-[#D9E4DF] rounded-2xl px-5 py-4 text-xs font-semibold text-on-surface-variant flex items-center gap-2">
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
          <div className="mt-auto px-10 pb-8 shrink-0 bg-background pt-2 border-t border-outline-variant/10 z-10">
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

              <div className="bg-[#FBFDFB] rounded-2xl shadow-xs border-2 border-outline-variant focus-within:border-secondary transition-all p-3">
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
                    <input ref={fileInputRef} type="file" className="hidden" accept=".csv,.xlsx,.xls,.pdf,.doc,.docx,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadFile(file); event.currentTarget.value = ''; }} />
                    <button className="p-1.5 text-outline hover:text-secondary transition-colors rounded-lg hover:bg-surface-container cursor-pointer">
                      <Mic className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <button 
                    onClick={() => handleSendMessage()}
                    className="bg-secondary text-on-secondary px-5 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer hover:bg-opacity-95 shadow-sm"
                  >
                    <span>发送指令</span>
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
          </div>

          {/* Right sidebar */}
          <aside className="w-80 h-full border-l border-outline-variant bg-surface-container-low flex flex-col p-4 gap-6 overflow-y-auto shrink-0 hidden xl:flex">
            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider px-1">学习备考资料袋</h3>
              <div className="bg-[#FBFDFB] border border-[#D9E4DF] p-4 rounded-xl space-y-2">
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
              <div className="bg-[#FBFDFB] border border-[#D9E4DF] p-4 rounded-xl space-y-2">
                <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                  <div className="h-full bg-secondary w-2/3"></div>
                </div>
                <p className="text-[10px] text-outline">今天已学习 2/3 的难点。继续加油！</p>
              </div>
            </div>
          </aside>

        </div>
      </main>

    </div>
  );
}
