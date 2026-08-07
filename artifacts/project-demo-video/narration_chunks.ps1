$ErrorActionPreference = 'Stop'
$outDir = Join-Path $PSScriptRoot 'tts'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Add-Type -AssemblyName System.Speech

$chunks = @(
  @{ id='01'; text='这是智汇校园，一个面向教师、学生和行政岗位的校园人工智能工作台。它用角色入口组织功能，让校园教、学、管场景可以在同一个本地系统中直接使用。'; duration=8 },
  @{ id='02'; text='进入教师工作台后，我们先演示教师最核心的学情分析任务。系统不依赖复杂账号和班级关系，教师可以直接创建任务。'; duration=8 },
  @{ id='03'; text='这里上传的是匿名成绩或作业资料。系统把用户明确选择的文件交给解析和统计 Skill，既减少重复整理，也避免把真实身份带入分析。'; duration=14 },
  @{ id='04'; text='点击开始分析后，程序先完成字段解析和班级整体统计，再交给智能体生成解释。结果页用图表呈现完成率、得分和薄弱点，让教师快速判断教学节奏。'; duration=12 },
  @{ id='05'; text='文本分析进一步把数据转成可执行建议。学情结果面向班级整体，不输出个体画像，体现了赛题要求的数据安全和可解释性。'; duration=10 },
  @{ id='06'; text='接着进入课堂互动。教师可以基于教学目标新建活动任务，让人工智能生成讨论、练习和追问提示，为课堂互动提供即时辅助。'; duration=9 },
  @{ id='07'; text='历史记录保留了高数函数等课堂任务，教师可以复用已有成果，形成从学情研判到课堂行动的连续闭环。'; duration=8 },
  @{ id='08'; text='课程迭代把旧课程资料和教学成果连接起来。这里可以查看 Python 课程内容和演示文稿，帮助教师快速更新课程与练习。'; duration=24 },
  @{ id='09'; text='课程菜单集中管理课程资料、课程任务和智能体历史。系统通过轻量 Skill 负责解析、统计和导出，智能体负责解释和生成，成果来源保持可追踪。'; duration=30 },
  @{ id='10'; text='切换到学生端后，学生拥有独立的学习空间。课程中心、学习记录和资料入口彼此清晰，学生可以从自己的课程内容开始学习。'; duration=42 },
  @{ id='11'; text='交互教材支持围绕当前资料提问，校园中心提供学习辅助入口，简历助手则把修改建议和模拟准备组织成可操作的任务。学生端不读取教师学情明细，角色空间保持隔离。'; duration=56 },
  @{ id='12'; text='行政端面向通知、会议记录、材料摘要和待办整理等流程化事务。进入行政助手后，用户可以直接提交材料并获得结构化结果。'; duration=29 },
  @{ id='13'; text='从教师教学到学生学习，再到行政办公，智汇校园用本地部署的轻量智能辅助能力，回应赛题提出的提质增效、个性化学习和办公协同需求。所有结果都可以继续查看、复制或导出，便于真实校园流程落地。'; duration=28 }
)

foreach ($chunk in $chunks) {
  $wav = Join-Path $outDir ("chunk_" + $chunk.id + '.wav')
  $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $synth.Rate = -1
  $synth.Volume = 100
  $synth.SelectVoice('Microsoft Huihui Desktop')
  $synth.SetOutputToWaveFile($wav)
  $synth.Speak($chunk.text)
  $synth.Dispose()
}

Write-Output ("Generated {0} chunks in {1}" -f $chunks.Count, $outDir)
