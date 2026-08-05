import { MessageSquare, Trash2 } from 'lucide-react'
import type { Conversation } from '../api'

interface ConversationHistoryProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onOpen: (conversationId: string) => void
  onDelete: (conversationId: string) => void
  accentClass: string
  heading?: string
  compact?: boolean
}

export default function ConversationHistory({
  conversations,
  activeConversationId,
  onOpen,
  onDelete,
  accentClass,
  heading = '最近对话',
  compact = false,
}: ConversationHistoryProps) {
  return (
    <div className={compact ? 'pb-1 pl-7 pr-1 pt-0.5' : 'mt-6 border-t border-outline-variant pt-5'}>
      {!compact && <div className="px-3 py-1 mb-1 text-[11px] text-outline font-bold tracking-wider">{heading}</div>}
      {conversations.length === 0 ? (
        <div className={`${compact ? 'px-2 py-2' : 'px-3 py-2'} text-xs italic text-on-surface-variant opacity-60`}>{heading === '任务' ? '暂无任务' : '暂无历史对话'}</div>
      ) : (
        <div className={`${compact ? 'max-h-40 space-y-0.5' : 'max-h-44 space-y-1'} overflow-y-auto`}>
          {conversations.map((conversation) => (
            <div key={conversation.id} className={`group flex items-center rounded-lg transition-colors ${activeConversationId === conversation.id ? 'bg-primary/10' : 'hover:bg-surface-container-high/70'}`}>
              <button onClick={() => onOpen(conversation.id)} className={`flex min-w-0 flex-1 items-center gap-2 text-left text-xs font-semibold outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/25 ${compact ? 'px-2 py-1.5' : 'px-3 py-2'} ${activeConversationId === conversation.id ? accentClass : 'text-on-surface-variant'}`}>
                <MessageSquare className={`${compact ? 'h-3 w-3' : 'h-3.5 w-3.5'} shrink-0`} />
                <span className="truncate">{conversation.title || '未命名对话'}</span>
              </button>
              <button onClick={() => onDelete(conversation.id)} aria-label="删除对话" className={`${compact ? 'mr-1' : 'mr-2'} rounded-md p-1 text-outline opacity-0 transition-[color,opacity,background-color] hover:bg-error-container/40 hover:text-error focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error/20 group-hover:opacity-100`}>
                <Trash2 className={`${compact ? 'h-3 w-3' : 'h-3.5 w-3.5'}`} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
