import { GraduationCap, Presentation, BookOpen, ShieldAlert, ArrowRight } from 'lucide-react';
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
      <header className="w-full px-4 py-5 sm:px-6 sm:py-6 lg:px-10 flex items-center justify-between z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-11 sm:h-11 bg-primary flex items-center justify-center rounded-xl shadow-[0_8px_20px_rgba(79,70,229,0.2)]">
            <GraduationCap className="w-6 h-6 text-on-primary" />
          </div>
          <span className="font-display text-xl sm:text-2xl font-bold text-primary tracking-tight">智汇校园</span>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center px-4 pt-6 pb-16 sm:px-6 sm:pt-10 md:px-10 lg:pt-14 lg:pb-20">
        {/* Welcoming Hero Section */}
        <section className="text-center mb-12 md:mb-14 max-w-4xl">
          <motion.h1 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-display px-2 text-3xl sm:text-4xl lg:text-5xl xl:text-[3.5rem] font-extrabold text-on-surface mb-5 tracking-[-0.035em] leading-[1.12]"
          >
            智汇校园-多智能体校园互动平台
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-base md:text-lg leading-7 md:leading-8 text-on-surface-variant max-w-2xl mx-auto opacity-90"
          >
            汇聚教学、学习与教务场景的多智能体能力，支持学情分析、课程互动、学习答疑与校园事务协同。
          </motion.p>
        </section>

        {/* Role Selection Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6 w-full max-w-6xl">
          {/* Teacher Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="role-card relative overflow-hidden bg-surface-container-lowest border border-outline-variant p-6 sm:p-7 lg:p-8 rounded-[20px] flex flex-col h-full min-h-[280px] shadow-sm hover:border-primary/30 hover:shadow-[0_16px_40px_rgba(15,23,42,0.1)]"
          >
            <div className="absolute inset-x-0 top-0 h-1 bg-primary" aria-hidden="true" />
            <div className="mb-7 w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
              <Presentation className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-xl sm:text-2xl font-bold text-on-surface mb-2">教师</h3>
              <div className="flex flex-wrap gap-2 mb-10">
                <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full">学情分析</span>
                <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full">题目生成</span>
                <span className="px-3 py-1 bg-primary/10 text-primary text-xs font-semibold rounded-full">互动设计</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('teacher')}
              disabled={isLoading}
              className="w-full min-h-11 py-2.5 bg-primary text-on-primary font-medium rounded-lg flex items-center justify-center gap-2 active:scale-[0.98] hover:bg-primary/90 transition-all group disabled:cursor-not-allowed disabled:opacity-60"
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
            className="role-card relative overflow-hidden bg-surface-container-lowest border border-outline-variant p-6 sm:p-7 lg:p-8 rounded-[20px] flex flex-col h-full min-h-[280px] shadow-sm hover:border-secondary/40 hover:shadow-[0_16px_40px_rgba(15,23,42,0.1)]"
          >
            <div className="absolute inset-x-0 top-0 h-1 bg-secondary" aria-hidden="true" />
            <div className="mb-7 w-14 h-14 rounded-2xl bg-secondary-container/20 flex items-center justify-center text-secondary">
              <BookOpen className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-xl sm:text-2xl font-bold text-on-surface mb-2">学生</h3>
              <div className="flex flex-wrap gap-2 mb-10">
                <span className="px-3 py-1 bg-secondary-container/60 text-on-secondary-container text-xs font-semibold rounded-full">论文辅助</span>
                <span className="px-3 py-1 bg-secondary-container/60 text-on-secondary-container text-xs font-semibold rounded-full">知识问答</span>
                <span className="px-3 py-1 bg-secondary-container/60 text-on-secondary-container text-xs font-semibold rounded-full">课程总结</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('student')}
              disabled={isLoading}
              className="w-full min-h-11 py-2.5 border border-outline-variant text-on-surface hover:border-secondary/60 hover:bg-secondary-container/30 font-medium rounded-lg flex items-center justify-center gap-2 active:scale-[0.98] transition-all group disabled:cursor-not-allowed disabled:opacity-60"
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
            className="role-card relative overflow-hidden bg-surface-container-lowest border border-outline-variant p-6 sm:p-7 lg:p-8 rounded-[20px] flex flex-col h-full min-h-[280px] shadow-sm hover:border-tertiary/40 hover:shadow-[0_16px_40px_rgba(15,23,42,0.1)]"
          >
            <div className="absolute inset-x-0 top-0 h-1 bg-tertiary" aria-hidden="true" />
            <div className="mb-7 w-14 h-14 rounded-2xl bg-tertiary-container/20 flex items-center justify-center text-tertiary">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <div className="flex-grow">
              <h3 className="font-display text-xl sm:text-2xl font-bold text-on-surface mb-2">教务人员</h3>
              <div className="flex flex-wrap gap-2 mb-10">
                <span className="px-3 py-1 bg-tertiary-container/50 text-on-tertiary-container text-xs font-semibold rounded-full">报表自动化</span>
                <span className="px-3 py-1 bg-tertiary-container/50 text-on-tertiary-container text-xs font-semibold rounded-full">资源排课</span>
                <span className="px-3 py-1 bg-tertiary-container/50 text-on-tertiary-container text-xs font-semibold rounded-full">信息分发</span>
              </div>
            </div>
            <button 
              onClick={() => onSelectRole('admin')}
              disabled={isLoading}
              className="w-full min-h-11 py-2.5 border border-outline-variant text-on-surface hover:border-tertiary/60 hover:bg-tertiary-container/30 font-medium rounded-lg flex items-center justify-center gap-2 active:scale-[0.98] transition-all group disabled:cursor-not-allowed disabled:opacity-60"
            >
              进入工作空间
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>
        </div>
      </main>

      {isLoading && <p className="fixed bottom-24 left-1/2 -translate-x-1/2 rounded-full bg-primary px-4 py-2 text-sm text-white shadow-lg">正在准备匿名工作空间…</p>}
      {notice && <p role="alert" className="fixed bottom-24 left-1/2 -translate-x-1/2 max-w-[90vw] rounded-xl bg-error-container px-4 py-2 text-sm text-on-error-container shadow-lg">{notice}</p>}

    </div>
  );
}
