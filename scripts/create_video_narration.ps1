param(
  [string]$ChapterFile = (Join-Path $PSScriptRoot '..\site\video_chapters.json'),
  [string]$OutputDir = (Join-Path $PSScriptRoot '..\out\pazhou_video_voice_20261107')
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$chapters = Get-Content -LiteralPath $ChapterFile -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -eq 'Microsoft Huihui Desktop' } | Select-Object -First 1
if (-not $voice) { throw 'Expected Mandarin voice Microsoft Huihui Desktop is unavailable.' }
$synth.SelectVoice('Microsoft Huihui Desktop')
$synth.Rate = -1
$synth.Volume = 92
$index = 0
foreach ($chapter in $chapters) {
  $index++
  $path = Join-Path $OutputDir ('chapter_{0:D2}.wav' -f $index)
  $synth.SetOutputToWaveFile($path)
  $synth.Speak([string]$chapter.narration)
  $synth.SetOutputToNull()
  Write-Output ('{0:D2} {1}' -f $index, $path)
}
$synth.Dispose()
