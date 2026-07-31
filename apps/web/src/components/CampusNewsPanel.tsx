import { useEffect, useMemo, useState } from 'react'
import { CalendarDays, ExternalLink, Newspaper, ScrollText } from 'lucide-react'
import {
  listCampusNews,
  type CampusNewsCategory,
  type CampusNewsItem,
  type CampusNewsResponse,
} from '../api'

const categories: Array<{ id: CampusNewsCategory; label: string; icon: typeof Newspaper }> = [
  { id: 'news', label: '学校新闻', icon: Newspaper },
  { id: 'activity', label: '校园活动', icon: CalendarDays },
  { id: 'notice', label: '公文通知', icon: ScrollText },
]

export default function CampusNewsPanel() {
  const [activeCategory, setActiveCategory] = useState<CampusNewsCategory>('news')
  const [data, setData] = useState<CampusNewsResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void listCampusNews()
      .then((response) => {
        if (active) setData(response)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => { active = false }
  }, [])

  const grouped = useMemo(() => Object.fromEntries(
    categories.map(({ id }) => [id, data?.items.filter((item) => item.category === id).slice(0, 3) ?? []]),
  ) as Record<CampusNewsCategory, CampusNewsItem[]>, [data])

  const freshnessMessage = failed
    ? '校园资讯暂时无法加载，不影响其他学习功能。'
    : data?.mode === 'live' && data.status === 'degraded'
      ? '部分校园资讯暂未更新，当前展示最近可用内容。'
      : data?.status === 'stale' || data?.refreshing
        ? '校园资讯正在更新，当前展示最近内容。'
        : null

  return (
    <section aria-labelledby="campus-news-heading" className="w-full text-left space-y-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-secondary">Campus Bulletin</p>
          <h3 id="campus-news-heading" className="font-display text-lg font-extrabold text-on-surface">校园资讯</h3>
        </div>
        {freshnessMessage && <p role="status" className="max-w-sm text-right text-[11px] text-on-surface-variant">{freshnessMessage}</p>}
      </div>

      {!data && !failed && (
        <div className="h-36 animate-pulse rounded-2xl border border-outline-variant/50 bg-surface-container-low" aria-label="正在加载校园资讯" />
      )}

      {(data || failed) && (
        <>
          <div className="grid grid-cols-3 gap-2 sm:hidden" role="tablist" aria-label="校园资讯分类">
            {categories.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={activeCategory === id}
                onClick={() => setActiveCategory(id)}
                className={`rounded-xl px-2 py-2 text-xs font-bold transition-colors ${activeCategory === id ? 'bg-secondary text-on-secondary' : 'bg-surface-container text-on-surface-variant'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="sm:hidden">
            <NewsColumn category={categories.find(({ id }) => id === activeCategory)!} items={grouped[activeCategory]} compact />
          </div>
          <div className="hidden grid-cols-3 gap-3 sm:grid">
            {categories.map((category) => <NewsColumn key={category.id} category={category} items={grouped[category.id]} />)}
          </div>
        </>
      )}
    </section>
  )
}

function NewsColumn({
  category,
  items,
  compact = false,
}: {
  category: (typeof categories)[number]
  items: CampusNewsItem[]
  compact?: boolean
}) {
  const Icon = category.icon
  return (
    <div className={`rounded-2xl border border-outline-variant/60 bg-surface-container-lowest ${compact ? 'p-3' : 'p-4'}`}>
      <div className="mb-3 flex items-center gap-2 text-secondary">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-secondary-container/40"><Icon className="h-4 w-4" /></span>
        <h4 className="text-sm font-extrabold text-on-surface">{category.label}</h4>
      </div>
      {items.length === 0 ? (
        <p className="py-5 text-center text-xs text-outline">暂无可展示的最新内容</p>
      ) : (
        <ul className="divide-y divide-outline-variant/40">
          {items.map((item) => <NewsEntry key={item.id} item={item} />)}
        </ul>
      )}
    </div>
  )
}

function NewsEntry({ item }: { item: CampusNewsItem }) {
  const content = (
    <>
      <span className="flex items-start gap-1.5">
        <span className="line-clamp-2 flex-1 text-xs font-bold leading-5 text-on-surface">{item.title}</span>
        {item.url && <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-secondary" aria-hidden="true" />}
      </span>
      {item.summary && <span className="mt-1 line-clamp-2 block text-[11px] leading-4 text-on-surface-variant">{item.summary}</span>}
      <span className="mt-1.5 flex items-center justify-between gap-2 text-[10px] text-outline">
        <span className="truncate">{item.source}</span>
        <time dateTime={item.published_at}>{formatDate(item.published_at)}</time>
      </span>
    </>
  )
  return (
    <li className="py-2.5 first:pt-0 last:pb-0">
      {item.url ? (
        <a href={item.url} target="_blank" rel="noreferrer" aria-label={`${item.title}（在学校官网打开）`} className="block rounded-lg outline-none transition-colors hover:text-secondary focus-visible:ring-2 focus-visible:ring-secondary/50">
          {content}
        </a>
      ) : <div>{content}</div>}
    </li>
  )
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}
