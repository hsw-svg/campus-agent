$ErrorActionPreference = 'Stop'
$ffmpeg = 'C:\Users\hsw\AppData\Local\JianyingPro\Apps\5.5.0.11332\ffmpeg.exe'
$input = 'C:\Users\hsw\Desktop\meeting_01.mp4'
$output = Join-Path $PSScriptRoot 'project-demo-cut.mp4'
$filter = @'
[0:v]trim=start=3:end=19,setpts=PTS-STARTPTS[v0];[0:a]atrim=start=3:end=19,asetpts=PTS-STARTPTS[a0];
[0:v]trim=start=19:end=50,setpts=PTS-STARTPTS[v1];[0:a]atrim=start=19:end=50,asetpts=PTS-STARTPTS[a1];
[0:v]trim=start=53:end=58,setpts=PTS-STARTPTS[v2];[0:a]atrim=start=53:end=58,asetpts=PTS-STARTPTS[a2];
[0:v]trim=start=58:end=69,setpts=PTS-STARTPTS[v3];[0:a]atrim=start=58:end=69,asetpts=PTS-STARTPTS[a3];
[0:v]trim=start=77:end=83,setpts=PTS-STARTPTS[v4];[0:a]atrim=start=77:end=83,asetpts=PTS-STARTPTS[a4];
[0:v]trim=start=83:end=113,setpts=PTS-STARTPTS[v5];[0:a]atrim=start=83:end=113,asetpts=PTS-STARTPTS[a5];
[0:v]trim=start=136:end=160,setpts=PTS-STARTPTS[v6];[0:a]atrim=start=136:end=160,asetpts=PTS-STARTPTS[a6];
[0:v]trim=start=212:end=282,setpts=PTS-STARTPTS[v7];[0:a]atrim=start=212:end=282,asetpts=PTS-STARTPTS[a7];
[0:v]trim=start=287:end=315,setpts=PTS-STARTPTS[v8];[0:a]atrim=start=287:end=315,asetpts=PTS-STARTPTS[a8];
[0:v]trim=start=330:end=387,setpts=PTS-STARTPTS[v9];[0:a]atrim=start=330:end=387,asetpts=PTS-STARTPTS[a9];
[v0][a0][v1][a1][v2][a2][v3][a3][v4][a4][v5][a5][v6][a6][v7][a7][v8][a8][v9][a9]concat=n=10:v=1:a=1[v][a]
'@
& $ffmpeg -y -hide_banner -i $input -filter_complex $filter -map '[v]' -map '[a]' -c:v mpeg4 -q:v 3 -c:a aac -b:a 128k -movflags +faststart $output
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed with exit code $LASTEXITCODE" }
Write-Output $output
