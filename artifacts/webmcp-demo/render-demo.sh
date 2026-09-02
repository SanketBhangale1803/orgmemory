#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CAPTURES="$ROOT/captures"
WORK="$ROOT/.render-v2"
FONT="/System/Library/Fonts/SFNS.ttf"
OUTPUT="$ROOT/orgmemory-webmcp-demo.mp4"
POSTER="$ROOT/orgmemory-webmcp-demo-poster.png"
SILENT="$WORK/demo-silent.mp4"
NARRATION_RAW="$WORK/narration.aiff"
NARRATION_FIT="$WORK/narration-fit.wav"
MUSIC="$WORK/ambient.wav"
MIX="$WORK/mix.m4a"

mkdir -p "$WORK"

make_clip() {
  local index="$1"
  local image="$2"
  local duration="$3"
  local title="$4"
  local subtitle="$5"
  local focus="$6"
  local pan_x
  local pan_y

  pan_x="iw/2-(iw/zoom/2)"
  pan_y="ih/2-(ih/zoom/2)"
  case "$focus" in
    right) pan_x="(iw-iw/zoom)*0.82" ;;
    left) pan_x="(iw-iw/zoom)*0.18" ;;
    top) pan_y="(ih-ih/zoom)*0.16" ;;
    bottom) pan_y="(ih-ih/zoom)*0.84" ;;
  esac

  ffmpeg -hide_banner -loglevel error -y \
    -loop 1 -framerate 30 -i "$CAPTURES/$image" -t "$duration" \
    -vf "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,zoompan=z='min(zoom+0.00010,1.035)':x='$pan_x':y='$pan_y':d=1:s=1920x1080:fps=30,unsharp=5:5:0.38:3:3:0.16,drawbox=x=52:y=902:w=1816:h=132:color=0x07100F@0.88:t=fill:enable='gte(t,0.35)',drawbox=x=52:y=902:w=6:h=132:color=0x9DF4D3@1:t=fill:enable='gte(t,0.35)',drawtext=fontfile='$FONT':text='$title':fontcolor=white:fontsize=35:x=82:y=920:enable='gte(t,0.35)',drawtext=fontfile='$FONT':text='$subtitle':fontcolor=0xC6D6D1:fontsize=21:x=82:y=971:enable='gte(t,0.35)',drawbox=x=0:y=1075:w=1920:h=5:color=0x9DF4D3@1:t=fill,format=yuv420p" \
    -an -c:v libx264 -preset slow -tune stillimage -crf 12 -r 30 "$WORK/$index.mp4"
}

make_clip 01 01-command-center.png 12.7 \
  "WebMCP surface" \
  "21 registered tools  •  14 read-only  •  6 governed" center
make_clip 02 02-workspace-tools.png 10.7 \
  "Authenticated workspace" \
  "Page-native tools use the signed-in session" center
make_clip 03 03-real-tool-discovery.png 14.7 \
  "Real browser tool discovery" \
  "list_orgmemory_spaces  →  21 authorized spaces" right
make_clip 04 03-real-tool-discovery.png 18.7 \
  "Brief before changing production" \
  "get_orgmemory_briefing  →  6 memories  →  approval required" right
make_clip 05 07-session-one-answer.png 14.7 \
  "Agent investigation" \
  "incidents  •  service context  •  dependencies  •  decisions" center
make_clip 06 08-human-approval-gate.png 12.7 \
  "Governed write" \
  "The agent proposes; a person decides" center
make_clip 07 09-fresh-agent-bridge.png 14.7 \
  "Fresh-agent handoff" \
  "No shared chat  •  approved memory is retrieved again" center
make_clip 08 12-ingest.png 12.7 \
  "Add Knowledge" \
  "documents  •  repositories  •  Slack  •  connected sources" top
make_clip 09 13-memories.png 12.7 \
  "Atomic memories" \
  "typed  •  scoped  •  confidence-ranked  •  current" top
make_clip 10 14-profiles.png 12.7 \
  "Current profiles" \
  "decisions  •  procedures  •  dependencies" center
make_clip 11 15-graph.png 12.7 \
  "Memory Graph" \
  "sources  →  memories  →  entities  →  relationships" center
make_clip 12 16-memory-work.png 12.7 \
  "Memory Work" \
  "activate context  →  prepare output  →  governed handoff" center
make_clip 13 18-outcome-loop.png 16.7 \
  "Outcome Loop" \
  "context served  →  action taken  →  outcome observed" top
make_clip 14 01-command-center.png 10 \
  "Complete application loop" \
  "ingest  →  remember  →  retrieve  →  approve  →  learn" center

ffmpeg -hide_banner -loglevel error -y \
  -i "$WORK/01.mp4" -i "$WORK/02.mp4" -i "$WORK/03.mp4" \
  -i "$WORK/04.mp4" -i "$WORK/05.mp4" -i "$WORK/06.mp4" \
  -i "$WORK/07.mp4" -i "$WORK/08.mp4" -i "$WORK/09.mp4" \
  -i "$WORK/10.mp4" -i "$WORK/11.mp4" -i "$WORK/12.mp4" \
  -i "$WORK/13.mp4" -i "$WORK/14.mp4" \
  -filter_complex "\
    [0:v][1:v]xfade=transition=fade:duration=0.7:offset=12[x1];\
    [x1][2:v]xfade=transition=slideleft:duration=0.7:offset=22[x2];\
    [x2][3:v]xfade=transition=dissolve:duration=0.7:offset=36[x3];\
    [x3][4:v]xfade=transition=fade:duration=0.7:offset=54[x4];\
    [x4][5:v]xfade=transition=slideleft:duration=0.7:offset=68[x5];\
    [x5][6:v]xfade=transition=dissolve:duration=0.7:offset=80[x6];\
    [x6][7:v]xfade=transition=fade:duration=0.7:offset=94[x7];\
    [x7][8:v]xfade=transition=slideleft:duration=0.7:offset=106[x8];\
    [x8][9:v]xfade=transition=dissolve:duration=0.7:offset=118[x9];\
    [x9][10:v]xfade=transition=fade:duration=0.7:offset=130[x10];\
    [x10][11:v]xfade=transition=slideleft:duration=0.7:offset=142[x11];\
    [x11][12:v]xfade=transition=dissolve:duration=0.7:offset=154[x12];\
    [x12][13:v]xfade=transition=fade:duration=0.7:offset=170,fade=t=in:st=0:d=0.5,fade=t=out:st=179.3:d=0.7[v]" \
  -map "[v]" -an -c:v libx264 -preset slow -tune stillimage -crf 14 \
  -profile:v high -pix_fmt yuv420p -r 30 -t 180 -movflags +faststart "$SILENT"

/usr/bin/say -v Samantha -r 180 -f "$ROOT/narration.txt" -o "$NARRATION_RAW"

if [[ ! -s "$NARRATION_RAW" ]] || [[ "$(stat -f%z "$NARRATION_RAW")" -lt 100000 ]]; then
  printf 'Narration generation failed. Run this script on macOS with speech synthesis available.\n' >&2
  exit 1
fi

NARRATION_DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$NARRATION_RAW")"
TEMPO="$(awk -v d="$NARRATION_DURATION" 'BEGIN {printf "%.6f", d/168}')"

ffmpeg -hide_banner -loglevel error -y \
  -i "$NARRATION_RAW" \
  -af "atempo=$TEMPO,highpass=f=90,lowpass=f=9500,acompressor=threshold=0.12:ratio=3:attack=15:release=180,volume=1.18,apad=pad_dur=180" \
  -t 180 -c:a pcm_s16le "$NARRATION_FIT"

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -t 180 -i "sine=frequency=110:sample_rate=48000" \
  -f lavfi -t 180 -i "sine=frequency=164.81:sample_rate=48000" \
  -f lavfi -t 180 -i "anoisesrc=color=pink:sample_rate=48000" \
  -filter_complex "[0:a]volume=0.009,tremolo=f=0.10:d=0.30[a0];[1:a]volume=0.004,tremolo=f=0.10:d=0.24[a1];[2:a]lowpass=f=650,volume=0.002[a2];[a0][a1][a2]amix=inputs=3:duration=longest:normalize=0,afade=t=in:st=0:d=2,afade=t=out:st=176:d=4[m]" \
  -map "[m]" -c:a pcm_s16le "$MUSIC"

ffmpeg -hide_banner -loglevel error -y \
  -i "$NARRATION_FIT" -i "$MUSIC" \
  -filter_complex "[0:a]volume=1.0[n];[1:a]volume=0.30[m];[n][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]" \
  -map "[a]" -t 180 -c:a aac -b:a 192k "$MIX"

ffmpeg -hide_banner -loglevel error -y \
  -i "$SILENT" -i "$MIX" -i "$ROOT/captions.srt" \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng -metadata:s:s:0 title=English \
  -t 180 -movflags +faststart "$OUTPUT"

ffmpeg -hide_banner -loglevel error -y -ss 6 -i "$OUTPUT" -frames:v 1 "$POSTER"

DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUTPUT")"
printf 'Rendered %s (%ss)\n' "$OUTPUT" "$DURATION"
