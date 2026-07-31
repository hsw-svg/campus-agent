import {
  BriefcaseBusiness,
  Dumbbell,
  Languages,
  Landmark,
  Laptop,
  Sigma,
} from 'lucide-react'

const THEMES = {
  english: { gradient: 'from-sky-500 via-blue-500 to-indigo-600', Icon: Languages, label: 'LANGUAGE' },
  policy: { gradient: 'from-rose-500 via-red-500 to-orange-500', Icon: Landmark, label: 'PERSPECTIVE' },
  mathematics: { gradient: 'from-violet-500 via-purple-500 to-fuchsia-600', Icon: Sigma, label: 'SCIENCE' },
  computer: { gradient: 'from-cyan-500 via-teal-500 to-emerald-600', Icon: Laptop, label: 'DIGITAL' },
  sports: { gradient: 'from-amber-400 via-orange-500 to-red-500', Icon: Dumbbell, label: 'WELLNESS' },
  career: { gradient: 'from-emerald-500 via-green-500 to-teal-600', Icon: BriefcaseBusiness, label: 'GROWTH' },
} as const

export default function CourseArtwork({
  thumbnailKey,
  name,
  compact = false,
}: {
  thumbnailKey: string | null
  name: string
  compact?: boolean
}) {
  const theme = THEMES[thumbnailKey as keyof typeof THEMES] ?? THEMES.english
  const Icon = theme.Icon

  return (
    <div className={`relative overflow-hidden bg-gradient-to-br ${theme.gradient} text-white ${compact ? 'min-h-44 rounded-3xl' : 'h-40'}`}>
      <div className="absolute -right-8 -top-10 h-36 w-36 rounded-full border-[18px] border-white/10" />
      <div className="absolute -bottom-14 -left-10 h-32 w-32 rounded-full bg-white/10 blur-sm" />
      <div className="relative flex h-full flex-col justify-between p-5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black tracking-[0.24em] text-white/75">{theme.label}</span>
          <span className="rounded-full border border-white/30 bg-white/15 p-2 backdrop-blur-sm">
            <Icon className="h-5 w-5" />
          </span>
        </div>
        <div>
          <p className="text-xs font-semibold text-white/75">通识核心课程</p>
          <p className={`${compact ? 'mt-1 text-3xl' : 'mt-1 text-xl'} font-black tracking-tight`}>{name}</p>
        </div>
      </div>
    </div>
  )
}
