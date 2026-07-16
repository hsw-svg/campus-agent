import { MessageSquare, Trash2 } from 'lucide-react'
import type { Conversation } from '../api'

interface ConversationHistoryProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onOpen: (conversationId: string) => void
  onDelete: (conversationId: string) => void
  accentClass: string
}

export default function ConversationHistory({
  conversations,
  activeConversationId,
  onOpen,
  onDelete,
  accentClass,
}: ConversationHistoryProps) {
  return (
    <div className="mt-6 border-t border-outline-variant pt-5">
      <div className="px-3 py-1 mb-1 text-[11px] text-outline font-bold tracking-wider">最近对话</div>
      {conversations.length === 0 ? (
        <div className="px-3 py-2 text-xs italic text-on-surface-variant opacity-60">暂无历史对话</div>
      ) : (
        <div className="max-h-44 space-y-1 overflow-y-auto">
          {conversations.map((conversation) => (
            <div key={conversation.id} className={`group flex items-center rounded-lg ${activeConversationId === conversation.id ? 'bg-surface-container-high' : 'hover:bg-surface-container-high/60'}`}>
              <button onClick={() => onOpen(conversation.id)} className={`flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left text-xs font-semibold ${activeConversationId === conversation.id ? accentClass : 'text-on-surface-variant'}`}>
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{conversation.title || '未命名对话'}</span>
              </button>
              <button onClick={() => onDelete(conversation.id)} aria-label="删除对话" className="mr-2 rounded p-1 text-outline opacity-0 transition-opacity hover:text-error group-hover:opacity-100">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
