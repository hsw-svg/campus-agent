import { FileText, FolderOpen, Paperclip } from 'lucide-react'
import type { Artifact, Attachment, SourceCitation } from '../api'
import ArtifactCard from './ArtifactCard'

interface ResourcePickerProps {
  attachments: Attachment[]
  artifacts: Artifact[]
  selectedAttachmentIds: string[]
  selectedArtifactIds: string[]
  citations?: SourceCitation[]
  accentClass: string
  onToggleAttachment: (attachmentId: string) => void
  onToggleArtifact: (artifactId: string) => void
  onExport: (artifact: Artifact, format: 'markdown' | 'csv') => Promise<void>
}

const attachmentStatus: Record<Attachment['status'], string> = {
  uploaded: '待解析',
  parsing: '解析中',
  indexed: '可用',
  degraded: '降级检索',
  failed: '解析失败',
}

export default function ResourcePicker({
  attachments,
  artifacts,
  selectedAttachmentIds,
  selectedArtifactIds,
  citations = [],
  accentClass,
  onToggleAttachment,
  onToggleArtifact,
  onExport,
}: ResourcePickerProps) {
  const currentAttachments = attachments.filter((attachment) => attachment.scope === 'conversation')
  const workspaceAttachments = attachments.filter((attachment) => attachment.scope === 'workspace')
  const selectedAttachments = attachments.filter((attachment) => selectedAttachmentIds.includes(attachment.id))
  const selectableArtifacts = artifacts.filter((artifact) => artifact.type !== 'sources')
  const latestArtifactId = selectableArtifacts.at(-1)?.id

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-outline-variant bg-[#FBFDFB] p-3 shadow-xs">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div>
            <h3 className="text-[11px] font-extrabold uppercase tracking-wider text-on-surface-variant">本次任务资料</h3>
            <p className="mt-0.5 text-[10px] text-outline">上传不等于使用，只有勾选项会发送。</p>
          </div>
          <Paperclip className={`h-4 w-4 ${accentClass}`} />
        </div>
        <AttachmentGroup
          title="当前对话附件"
          items={currentAttachments}
          selectedIds={selectedAttachmentIds}
          onToggle={onToggleAttachment}
        />
        <AttachmentGroup
          title="工作区资料库"
          items={workspaceAttachments}
          selectedIds={selectedAttachmentIds}
          onToggle={onToggleAttachment}
        />
        {selectedAttachments.length > 0 && (
          <div className="mt-2 rounded-lg bg-secondary-container/15 px-2.5 py-2 text-[10px] leading-relaxed text-on-surface-variant">
            <p className={`font-extrabold ${accentClass}`}>已选 {selectedAttachments.length} 项</p>
            <p className="mt-0.5 truncate">{selectedAttachments.map((attachment) => attachment.filename).join('、')}</p>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-outline-variant bg-[#FBFDFB] p-3 shadow-xs">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div>
            <h3 className="text-[11px] font-extrabold uppercase tracking-wider text-on-surface-variant">本次任务成果</h3>
            <p className="mt-0.5 text-[10px] text-outline">可将已有成果作为输入。</p>
          </div>
          <FolderOpen className={`h-4 w-4 ${accentClass}`} />
        </div>
        {selectableArtifacts.length === 0 ? (
          <div className="rounded-xl border border-dashed border-outline-variant px-3 py-4 text-center text-[10px] text-outline">
            <FileText className="mx-auto mb-1 h-5 w-5" />暂无可选成果
          </div>
        ) : (
          <div className="space-y-3">
            {selectableArtifacts.map((artifact) => (
              <ArtifactCard
                key={artifact.id}
                artifact={artifact}
                selectable
                selected={selectedArtifactIds.includes(artifact.id)}
                onToggle={() => onToggleArtifact(artifact.id)}
                onExport={onExport}
                citations={artifact.id === latestArtifactId ? citations : []}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function AttachmentGroup({
  title,
  items,
  selectedIds,
  onToggle,
}: {
  title: string
  items: Attachment[]
  selectedIds: string[]
  onToggle: (attachmentId: string) => void
}) {
  return (
    <div className="mt-3">
      <p className="mb-1.5 px-1 text-[10px] font-extrabold text-on-surface-variant">{title}</p>
      {items.length === 0 ? (
        <p className="rounded-lg bg-surface-container px-2.5 py-2 text-[10px] text-outline">
          {title === '当前对话附件' ? '当前对话暂无附件，可从工作区资料库中勾选。' : '工作区资料库暂无资料。'}
        </p>
      ) : (
        <div className="space-y-1.5">
          {items.map((attachment) => (
            <label key={attachment.id} className="flex cursor-pointer items-center gap-2 rounded-xl border border-outline-variant/60 bg-white px-2.5 py-2 hover:border-primary/50">
              <input
                type="checkbox"
                checked={selectedIds.includes(attachment.id)}
                onChange={() => onToggle(attachment.id)}
                disabled={attachment.status === 'failed'}
                className="h-3.5 w-3.5 accent-primary"
              />
              <span className="min-w-0 flex-1 truncate text-[10px] font-bold text-on-surface">{attachment.filename}</span>
              <span className={`text-[9px] ${attachment.status === 'failed' ? 'text-error' : attachment.status === 'indexed' ? 'text-primary' : 'text-outline'}`}>
                {attachmentStatus[attachment.status]}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
