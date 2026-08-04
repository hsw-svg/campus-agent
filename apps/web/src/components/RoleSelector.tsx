import { GraduationCap, ShieldCheck, Presentation, BookOpen, ShieldAlert, EyeOff, Lock, Landmark, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { WorkspaceRole } from '../types';

interface RoleSelectorProps {
  onSelectRole: (role: WorkspaceRole) => void | Promise<void>;
  isLoading?: boolean;
  notice?: string | null;
}

export default function RoleSelector({ onSelectRole, isLoading = false, notice }: RoleSelectorProps) {
  return (
    <div className="min-h-screen flex flex-col font-sans text-on-surface antialiased bg-background">
      {/* Header / Branding */}
      <header className="w-full px-10 py-6 flex items-center justify-between z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary flex items-center justify-center rounded-lg shadow-sm">
            <GraduationCap className="w-6 h-6 text-on-primary" />
          </div>
          <span className="font-display text-2xl font-bold text-primary tracking-tight">智汇校园</span>
        </div>
        <div className="hidden md:flex gap-4 items-center">
          <span className="text-sm text-on-surface-variant font-medium">院校级智能协作平台</span>
          <div className="w-px h-4 bg-outline-variant"></div>
          <div className="flex items-center gap-1.5 text-primary font-medium text-sm">
            <ShieldCheck className="w-4.5 h-4.5" />
            <span>企业级安全标准</span>
          </div>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center px-4 md:px-10 pb-16">
        {/* Welcoming Hero Section */}
        <section className="text-center mb-10 max-w-3xl">
          <motion.h1 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display text-3xl md:text-4xl lg:text-5xl font-extrabold text-on-surface mb-4 tracking-tight leading-tight"
          >
            让每一次教学、学习与协作，都更清晰
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-base md:text-lg text-on-surface-variant max-w-xl mx-auto opacity-90"
          >
            选择一个角色即可开始，无需注册。您的数据将受到严格的学术隐私保护。
          </motion.p>
        </section>

        {/* Role Selection Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl">
          {/* Teacher Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="role-card bg-surface-container-lowest border border-outline-variant p-8 rounded-2xl flex flex-col h-full shadow-sm"
          >
            <div className="mb-6 w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
              <Presentation className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-2xl font-bold text-on-surface mb-1">教师</h3>
              <p className="text-xs text-on-surface-variant mb-6 tracking-wider font-semibold font-sans">教师智能工作空间</p>
              <div className="flex flex-wrap gap-2 mb-8">
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">学情分析</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">题目生成</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">互动设计</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('teacher')}
              disabled={isLoading}
              className="w-full py-3 bg-primary text-on-primary font-medium rounded-xl flex items-center justify-center gap-2 active:scale-[0.98] hover:bg-primary-container transition-all group"
            >
              进入工作空间
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>

          {/* Student Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.4 }}
            className="role-card bg-surface-container-lowest border border-outline-variant p-8 rounded-2xl flex flex-col h-full shadow-sm"
          >
            <div className="mb-6 w-14 h-14 rounded-xl bg-secondary-container/20 flex items-center justify-center text-secondary">
              <BookOpen className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-2xl font-bold text-on-surface mb-1">学生</h3>
              <p className="text-xs text-on-surface-variant mb-6 tracking-wider font-semibold font-sans">学生智能工作空间</p>
              <div className="flex flex-wrap gap-2 mb-8">
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">论文辅助</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">知识问答</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">课程总结</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('student')}
              disabled={isLoading}
              className="w-full py-3 border-2 border-outline text-on-surface hover:bg-surface-container-high font-medium rounded-xl flex items-center justify-center gap-2 active:scale-[0.98] transition-all group"
            >
              进入工作空间
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>

          {/* Admin Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.5 }}
            className="role-card bg-surface-container-lowest border border-outline-variant p-8 rounded-2xl flex flex-col h-full shadow-sm"
          >
            <div className="mb-6 w-14 h-14 rounded-xl bg-tertiary-container/20 flex items-center justify-center text-tertiary">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-2xl font-bold text-on-surface mb-1">教务人员</h3>
              <p className="text-xs text-on-surface-variant mb-6 tracking-wider font-semibold font-sans">教务智能工作空间</p>
              <div className="flex flex-wrap gap-2 mb-8">
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">报表自动化</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">资源排课</span>
                <span className="px-3 py-1 bg-secondary-container/50 text-on-secondary-container text-xs font-semibold rounded-full">信息分发</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('admin')}
              disabled={isLoading}
              className="w-full py-3 border-2 border-outline text-on-surface hover:bg-surface-container-high font-medium rounded-xl flex items-center justify-center gap-2 active:scale-[0.98] transition-all group"
            >
              进入工作空间
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>
        </div>
      </main>

      {isLoading && <p className="fixed bottom-24 left-1/2 -translate-x-1/2 rounded-full bg-primary px-4 py-2 text-sm text-white shadow-lg">正在准备匿名工作空间…</p>}
      {notice && <p role="alert" className="fixed bottom-24 left-1/2 -translate-x-1/2 max-w-[90vw] rounded-xl bg-error-container px-4 py-2 text-sm text-on-error-container shadow-lg">{notice}</p>}

      {/* Footer Security Promises */}
      <footer className="w-full bg-surface-container-low border-t border-outline-variant py-6 px-10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-1.5 text-on-surface-variant">
              <EyeOff className="w-4.5 h-4.5 text-primary" />
              <span className="text-sm font-medium">匿名使用</span>
            </div>
            <div className="flex items-center gap-1.5 text-on-surface-variant">
              <Landmark className="w-4.5 h-4.5 text-primary" />
              <span className="text-sm font-medium">角色隔离</span>
            </div>
            <div className="flex items-center gap-1.5 text-on-surface-variant">
              <Lock className="w-4.5 h-4.5 text-primary" />
              <span className="text-sm font-medium">资料可控</span>
            </div>
          </div>
          <div className="text-xs text-on-surface-variant flex flex-wrap items-center gap-3">
            <span>© 2024 智汇校园</span>
            <span className="hidden md:inline font-light">基于大语言模型的学术辅助系统</span>
            <a className="hover:text-primary hover:underline underline-offset-4 font-semibold" href="#">隐私协议</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
