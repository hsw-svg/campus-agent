$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $root 'tts'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Add-Type -AssemblyName System.Speech
$rows = Get-Content -LiteralPath (Join-Path $root 'narration_data.tsv') -Encoding UTF8
foreach ($row in $rows) {
  if ([string]::IsNullOrWhiteSpace($row)) { continue }
  $parts = $row -split "`t", 3
  $id = $parts[0]
  $text = $parts[2]
  $wav = Join-Path $outDir ("chunk_{0}.wav" -f $id)
  $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $synth.Rate = -1
  $synth.Volume = 100
  $synth.SelectVoice('Microsoft Huihui Desktop')
  $synth.SetOutputToWaveFile($wav)
  $synth.Speak($text)
  $synth.Dispose()
}
Write-Output ("Generated {0} narration chunks" -f $rows.Count)
