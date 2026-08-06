#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CAPTURES="$ROOT/captures"
WORK="$ROOT/.render"
FONT="/System/Library/Fonts/SFNS.ttf"
OUTPUT="$ROOT/orgmemory-client-demo.mp4"
SILENT="$WORK/demo-silent.mp4"
NARRATION="$WORK/narration.aiff"
MUSIC="$WORK/ambient.wav"
MIX="$WORK/mix.m4a"

mkdir -p "$WORK"

make_clip() {
  local index="$1"
  local image="$2"
  local duration="$3"
  local title="$4"
  local subtitle="$5"

  ffmpeg -hide_banner -loglevel error -y \
    -loop 1 -framerate 30 -i "$CAPTURES/$image" -t "$duration" \
    -vf "scale=2048:1152:force_original_aspect_ratio=increase,crop=2048:1152,zoompan=z='min(zoom+0.00018,1.035)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,drawbox=x=58:y=850:w=1804:h=172:color=0x140B0E@0.84:t=fill,drawbox=x=58:y=850:w=9:h=172:color=0xD84B5B@1:t=fill,drawtext=fontfile='$FONT':text='$title':fontcolor=white:fontsize=42:x=94:y=878,drawtext=fontfile='$FONT':text='$subtitle':fontcolor=0xE8DDE0:fontsize=25:x=94:y=942,format=yuv420p" \
    -an -c:v libx264 -preset medium -crf 16 -r 30 "$WORK/$index.mp4"
}

make_clip 01 01-hero.png 6 \
  "The context layer for every agent" \
  "One company memory  •  source-backed  •  permission-aware"
make_clip 02 02-connect.png 6 \
  "Connect once. Every agent gets context." \
  "GitHub  •  Slack  •  files  •  MCP  •  API"
make_clip 03 03-swarm.png 6 \
  "Retrieval is a team, not a lookup." \
  "Scouts  •  graph foragers  •  truth historians  •  one compiler"
make_clip 04 14-chat-empty.png 3 \
  "Ask in plain English" \
  "The same governed brain from the web, an IDE, Slack, or any MCP client"
make_clip 05 15-query-sent.png 2 \
  "A real question enters the workspace" \
  "What changed recently?"
make_clip 06 16-query-retrieving.png 3 \
  "OrgMemory follows the evidence" \
  "Authorized sources are searched and reconciled in parallel"
make_clip 07 17-query-answer.png 8 \
  "A cited answer grounded in current sources" \
  "Recent changes are returned with exact GitHub commit evidence"
make_clip 08 06-sources.png 6 \
  "Inspect every source" \
  "No unsupported summary layer. Every answer remains traceable."
make_clip 09 18-graph-live.png 7 \
  "A living graph of company truth" \
  "Messages  •  revisions  •  memories  •  decisions  •  outcomes"
make_clip 10 10-updates.png 6 \
  "Changes become active agent context" \
  "New evidence updates what agents should believe and do"
make_clip 11 11-work.png 6 \
  "From remembered context to useful work" \
  "Describe the outcome once. OrgMemory prepares the grounded brief."
make_clip 12 12-approvals.png 5 \
  "Consequential writes wait for approval" \
  "Read and write tools stay separated by risk"
make_clip 13 13-audit.png 5 \
  "Every action stays auditable" \
  "Who  •  what  •  when  •  source  •  result"

ffmpeg -hide_banner -loglevel error -y \
  -loop 1 -framerate 30 -i "$CAPTURES/01-hero.png" -t 7 \
  -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=7,eq=brightness=-0.52:saturation=0.75,drawbox=x=0:y=0:w=1920:h=1080:color=0x140B0E@0.42:t=fill,drawtext=fontfile='$FONT':text='ORGMEMORY':fontcolor=0xE05062:fontsize=34:x=(w-text_w)/2:y=330,drawtext=fontfile='$FONT':text='One company memory. Every agent.':fontcolor=white:fontsize=68:x=(w-text_w)/2:y=430,drawtext=fontfile='$FONT':text='Cursor  •  Claude  •  ChatGPT  •  Codex  •  your agents':fontcolor=0xE8DDE0:fontsize=31:x=(w-text_w)/2:y=535,drawtext=fontfile='$FONT':text='Source-backed context. Governed actions. Durable outcomes.':fontcolor=0xE8DDE0:fontsize=27:x=(w-text_w)/2:y=600,format=yuv420p" \
  -an -c:v libx264 -preset medium -crf 16 -r 30 "$WORK/14.mp4"

ffmpeg -hide_banner -loglevel error -y \
  -i "$WORK/01.mp4" -i "$WORK/02.mp4" -i "$WORK/03.mp4" \
  -i "$WORK/04.mp4" -i "$WORK/05.mp4" -i "$WORK/06.mp4" \
  -i "$WORK/07.mp4" -i "$WORK/08.mp4" -i "$WORK/09.mp4" \
  -i "$WORK/10.mp4" -i "$WORK/11.mp4" -i "$WORK/12.mp4" \
  -i "$WORK/13.mp4" -i "$WORK/14.mp4" \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=5.4[x1];[x1][2:v]xfade=transition=fade:duration=0.6:offset=10.8[x2];[x2][3:v]xfade=transition=fade:duration=0.6:offset=16.2[x3];[x3][4:v]xfade=transition=fade:duration=0.6:offset=18.6[x4];[x4][5:v]xfade=transition=fade:duration=0.6:offset=20.0[x5];[x5][6:v]xfade=transition=fade:duration=0.6:offset=22.4[x6];[x6][7:v]xfade=transition=fade:duration=0.6:offset=29.8[x7];[x7][8:v]xfade=transition=fade:duration=0.6:offset=35.2[x8];[x8][9:v]xfade=transition=fade:duration=0.6:offset=41.6[x9];[x9][10:v]xfade=transition=fade:duration=0.6:offset=47.0[x10];[x10][11:v]xfade=transition=fade:duration=0.6:offset=52.4[x11];[x11][12:v]xfade=transition=fade:duration=0.6:offset=56.8[x12];[x12][13:v]xfade=transition=fade:duration=0.6:offset=61.2[v]" \
  -map "[v]" -an -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p \
  -movflags +faststart "$SILENT"

/usr/bin/say -v Samantha -r 220 -f "$ROOT/narration.txt" -o "$NARRATION"

if [[ ! -s "$NARRATION" ]] || [[ "$(stat -f%z "$NARRATION")" -lt 100000 ]]; then
  printf 'Narration generation failed. Run this script with access to macOS speech synthesis.\n' >&2
  exit 1
fi

VIDEO_DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$SILENT")"

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -t "$VIDEO_DURATION" -i "sine=frequency=110:sample_rate=48000" \
  -f lavfi -t "$VIDEO_DURATION" -i "sine=frequency=164.81:sample_rate=48000" \
  -f lavfi -t "$VIDEO_DURATION" -i "sine=frequency=220:sample_rate=48000" \
  -filter_complex "[0:a]volume=0.022,tremolo=f=0.12:d=0.4[a0];[1:a]volume=0.014,tremolo=f=0.1:d=0.3[a1];[2:a]volume=0.009,tremolo=f=0.14:d=0.35[a2];[a0][a1][a2]amix=inputs=3:duration=longest:normalize=0,lowpass=f=900,afade=t=in:st=0:d=2,afade=t=out:st=$(awk -v d="$VIDEO_DURATION" 'BEGIN {printf "%.3f", d-3}'):d=3[m]" \
  -map "[m]" -c:a pcm_s16le "$MUSIC"

ffmpeg -hide_banner -loglevel error -y \
  -i "$NARRATION" -i "$MUSIC" \
  -filter_complex "[0:a]highpass=f=90,lowpass=f=9000,acompressor=threshold=0.12:ratio=3:attack=15:release=180,volume=1.25,apad[n];[1:a]volume=0.55[m];[n][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]" \
  -map "[a]" -t "$VIDEO_DURATION" -c:a aac -b:a 192k "$MIX"

ffmpeg -hide_banner -loglevel error -y \
  -i "$SILENT" -i "$MIX" -i "$ROOT/captions.srt" \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng -metadata:s:s:0 title=English \
  -t "$VIDEO_DURATION" -movflags +faststart "$OUTPUT"

ffmpeg -hide_banner -loglevel error -y -ss 61.8 -i "$OUTPUT" -frames:v 1 \
  "$ROOT/orgmemory-client-demo-poster.png"

printf 'Rendered %s\n' "$OUTPUT"
