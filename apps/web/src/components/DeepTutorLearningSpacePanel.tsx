import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Database,
  History,
  Layers3,
  LoaderCircle,
  NotebookPen,
  Sparkles,
  Target,
} from 'lucide-react'
import {
  deepTutorBooksFromResponse,
  deepTutorKnowledgeBasesFromResponse,
  listDeepTutorBooks,
  listDeepTutorKnowledgeBases,
  type DeepTutorBook,
  type DeepTutorKnowledgeBase,
} from '../api'
import useDeepTutorStudyState from '../hooks/useDeepTutorStudyState'

interface DeepTutorLearningSpacePanelProps {
  token: string | null
  onOpenBooks: (bookId?: string) => void
}

function progressFor(book: DeepTutorBook, completedCount: number): number {
  if (!book.pageCount || book.pageCount <= 0) return completedCount > 0 ? 100 : 0
  return Math.min(100, Math.round((completedCount / book.pageCount) * 100))
}

export default function DeepTutorLearningSpacePanel({ token, onOpenBooks }: DeepTutorLearningSpacePanelProps) {
  const [books, setBooks] = useState<DeepTutorBook[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<DeepTutorKnowledgeBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { state, completedForBook, notesCount } = useDeepTutorStudyState(token)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      setError('当前学生工作空间尚未建立，学习空间会在进入学生端后开放。')
      return
    }
    let active = true
    setLoading(true)
    setError(null)
    void Promise.allSettled([listDeepTutorBooks(token), listDeepTutorKnowledgeBases(token)]).then((results) => {
      if (!active) return
      const [booksResult, knowledgeResult] = results
      if (booksResult.status === 'fulfilled') {
        setBooks(deepTutorBooksFromResponse(booksResult.value))
      } else {
        setError(booksResult.reason instanceof Error ? booksResult.reason.message : '学习空间加载失败。')
      }
      if (knowledgeResult.status === 'fulfilled') setKnowledgeBases(deepTutorKnowledgeBasesFromResponse(knowledgeResult.value))
      setLoading(false)
    })
    return () => { active = false }
  }, [token])

  const completedPagesCount = useMemo(
    () => Object.values(state.completedPages).reduce((total, pages) => total + pages.length, 0),
    [state.completedPages],
  )
  const lastBook = useMemo(
    () => books.find((book) => book.id === state.lastOpened?.bookId) ?? null,
    [books, state.lastOpened?.bookId],
  )
  const recentBooks = useMemo(() => books.slice(0, 4), [books])

  return (
    <div className="w-full space-y-6 py-4 sm:py-8">
      <section className="overflow-hidden rounded-3xl border border-secondary/20 bg-secondary-container/10 p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-3 flex items-center gap-2 text-secondary">
              <Sparkles className="h-5 w-5" />
              <span className="text-[11px] font-black uppercase tracking-[0.2em]">Student Learning Space</span>
            </div>
            <h2 className="text-3xl font-black tracking-tight text-on-surface sm:text-4xl">把每一次提问，变成下一步学习。</h2>
            <p className="mt-3 text-sm font-medium leading-6 text-on-surface-variant">
              从交互式书本开始，按章节阅读、即时追问，并把完成页面、学习笔记和待复习问题留在自己的学习空间。
            </p>
          </div>
          <button
            type="button"
            onClick={() => onOpenBooks()}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-secondary px-4 py-3 text-sm font-black text-on-secondary shadow-sm transition hover:opacity-95 active:scale-[0.98]"
          >
            <BookOpenCheck className="h-4 w-4" />
            打开交互教材
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>

      {error && <div role="alert" className="rounded-2xl border border-error/30 bg-error-container px-4 py-3 text-sm font-semibold text-on-error-container">{error}</div>}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: '我的书本', value: books.length, icon: BookOpenCheck, tone: 'text-secondary bg-secondary-container/40' },
          { label: '已完成页面', value: completedPagesCount, icon: CheckCircle2, tone: 'text-tertiary bg-tertiary-container/40' },
          { label: '学习笔记', value: notesCount, icon: NotebookPen, tone: 'text-primary bg-primary-container/30' },
          { label: '待复习问题', value: state.savedQuestions.length, icon: Target, tone: 'text-error bg-error-container/50' },
        ].map((item) => {
          const Icon = item.icon
          return (
            <div key={item.label} className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-4">
              <div className="flex items-center justify-between">
                <span className={`flex h-9 w-9 items-center justify-center rounded-xl ${item.tone}`}><Icon className="h-4 w-4" /></span>
                {loading && <LoaderCircle className="h-4 w-4 animate-spin text-outline" />}
              </div>
              <p className="mt-4 text-2xl font-black text-on-surface">{item.value}</p>
              <p className="mt-1 text-xs font-bold text-on-surface-variant">{item.label}</p>
            </div>
          )
        })}
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(18rem,0.8fr)]">
        <div className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">Continue learning</p>
              <h3 className="mt-1 text-xl font-black text-on-surface">继续上次的学习</h3>
            </div>
            <History className="h-5 w-5 text-secondary" />
          </div>
          {lastBook && state.lastOpened ? (
            <button
              type="button"
              onClick={() => onOpenBooks(lastBook.id)}
              className="group w-full rounded-2xl border border-secondary/30 bg-secondary-container/10 p-4 text-left transition hover:border-secondary/60 hover:bg-secondary-container/20"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-base font-black text-on-surface">{lastBook.title}</p>
                  <p className="mt-1 text-xs font-semibold text-on-surface-variant">从上次打开的页面继续，问答会自动带入页面上下文。</p>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-secondary transition group-hover:translate-x-1" />
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-container-high">
                <div className="h-full rounded-full bg-secondary" style={{ width: `${progressFor(lastBook, completedForBook(lastBook.id).length)}%` }} />
              </div>
              <p className="mt-2 text-[11px] font-bold text-secondary">已完成 {completedForBook(lastBook.id).length} 个页面</p>
            </button>
          ) : (
            <div className="rounded-2xl border border-dashed border-outline-variant bg-surface-container px-5 py-8 text-center">
              <BookOpenCheck className="mx-auto h-8 w-8 text-secondary/70" />
              <p className="mt-3 text-sm font-black text-on-surface">还没有学习记录</p>
              <p className="mt-1 text-xs leading-5 text-on-surface-variant">打开一本交互教材，完成第一个页面后，这里会出现继续学习入口。</p>
              <button type="button" onClick={() => onOpenBooks()} className="mt-4 rounded-lg border border-secondary/40 px-3 py-2 text-xs font-black text-secondary hover:bg-secondary-container/20">去书架看看</button>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-2">
            <Database className="h-5 w-5 text-secondary" />
            <div>
              <h3 className="text-base font-black text-on-surface">知识库</h3>
              <p className="text-xs font-semibold text-on-surface-variant">可用于书本生成与页面问答</p>
            </div>
          </div>
          {knowledgeBases.length > 0 ? (
            <div className="space-y-2">
              {knowledgeBases.slice(0, 3).map((knowledgeBase) => (
                <div key={knowledgeBase.name} className="rounded-xl bg-surface-container px-3 py-3">
                  <p className="truncate text-xs font-black text-on-surface">{knowledgeBase.name}</p>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-on-surface-variant">{knowledgeBase.description}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl bg-surface-container px-3 py-4 text-xs leading-5 text-on-surface-variant">当前没有可用知识库。仍可以直接阅读已生成的交互教材。</div>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5 sm:p-6">
        <div className="mb-5 flex items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-secondary">My library</p>
            <h3 className="mt-1 text-xl font-black text-on-surface">我的交互书本</h3>
          </div>
          <button type="button" onClick={() => onOpenBooks()} className="inline-flex items-center gap-1 text-xs font-black text-secondary hover:underline">查看全部 <ArrowRight className="h-3.5 w-3.5" /></button>
        </div>
        {recentBooks.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {recentBooks.map((book) => {
              const completed = completedForBook(book.id).length
              return (
                <button key={book.id} type="button" onClick={() => onOpenBooks(book.id)} className="group rounded-2xl border border-outline-variant/60 bg-surface p-4 text-left transition hover:-translate-y-0.5 hover:border-secondary/50 hover:shadow-sm">
                  <div className="flex h-20 items-end justify-between overflow-hidden rounded-xl bg-gradient-to-br from-secondary-container/60 via-surface-container to-tertiary-container/40 p-3">
                    <Layers3 className="h-6 w-6 text-secondary" />
                    <span className="rounded-full bg-surface/80 px-2 py-1 text-[10px] font-black text-secondary">{progressFor(book, completed)}%</span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm font-black text-on-surface">{book.title}</p>
                  <p className="mt-1 line-clamp-2 min-h-10 text-[11px] leading-5 text-on-surface-variant">{book.description}</p>
                  <div className="mt-3 flex items-center justify-between text-[10px] font-bold text-outline">
                    <span>{book.pageCount ?? '—'} 页面</span>
                    <span className="text-secondary group-hover:underline">开始阅读</span>
                  </div>
                </button>
              )
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-outline-variant bg-surface-container px-5 py-8 text-center text-sm font-semibold text-on-surface-variant">
            {loading ? '正在同步 DeepTutor 书架…' : '还没有交互书本，去交互教材页面创建一本主题教材吧。'}
          </div>
        )}
      </section>

      <section className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5">
          <div className="flex items-center gap-2 text-secondary"><NotebookPen className="h-4 w-4" /><h3 className="text-sm font-black text-on-surface">学习笔记</h3></div>
          <p className="mt-2 text-xs leading-5 text-on-surface-variant">在阅读页记录自己的理解，笔记只保存在当前浏览器，适合现场演示和快速复盘。</p>
          <p className="mt-4 text-2xl font-black text-on-surface">{notesCount}<span className="ml-1 text-xs font-bold text-on-surface-variant">条</span></p>
        </div>
        <div className="rounded-2xl border border-outline-variant/60 bg-surface-container-lowest p-5">
          <div className="flex items-center gap-2 text-secondary"><Target className="h-4 w-4" /><h3 className="text-sm font-black text-on-surface">待复习问题</h3></div>
          <p className="mt-2 text-xs leading-5 text-on-surface-variant">把页面问答中的好问题收藏下来，回到阅读页继续追问。</p>
          <p className="mt-4 text-2xl font-black text-on-surface">{state.savedQuestions.length}<span className="ml-1 text-xs font-bold text-on-surface-variant">个</span></p>
        </div>
      </section>
    </div>
  )
}
