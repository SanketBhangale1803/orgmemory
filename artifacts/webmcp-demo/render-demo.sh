#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CAPTURES="$ROOT/captures"
WORK="$ROOT/.render"
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
  local fade_out
  if [[ "${REUSE_CLIPS:-0}" == "1" && -s "$WORK/$index.mp4" ]]; then
    return
  fi
  fade_out="$(awk -v d="$duration" 'BEGIN {printf "%.3f", d-0.45}')"

  ffmpeg -hide_banner -loglevel error -y \
    -loop 1 -framerate 30 -i "$CAPTURES/$image" -t "$duration" \
    -vf "scale=2048:1152:force_original_aspect_ratio=increase,crop=2048:1152,zoompan=z='min(zoom+0.00012,1.022)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,setsar=1,eq=brightness=-0.025:saturation=1.04,drawbox=x=56:y=846:w=1808:h=180:color=0x07100F@0.86:t=fill,drawbox=x=56:y=846:w=8:h=180:color=0x9DF4D3@1:t=fill,drawtext=fontfile='$FONT':text='$title':fontcolor=white:fontsize=41:x=94:y=876,drawtext=fontfile='$FONT':text='$subtitle':fontcolor=0xC6D6D1:fontsize=24:x=94:y=942,fade=t=in:st=0:d=0.45,fade=t=out:st=$fade_out:d=0.45,format=yuv420p" \
    -an -c:v libx264 -preset medium -crf 16 -r 30 "$WORK/$index.mp4"
}

make_clip 01 01-command-center.png 14 \
  "Give browser agents organizational memory" \
  "Source-backed context before action"
make_clip 02 06-with-vs-without.png 14 \
  "From interface archaeology to a direct capability" \
  "No DOM guessing  •  structured, authorized evidence"
make_clip 03 02-workspace-tools.png 10 \
  "The authenticated workspace is the tool boundary" \
  "19 tools  •  13 read-only  •  6 human-governed"
make_clip 04 03-real-tool-discovery.png 14 \
  "The browser discovers WebMCP directly from the page" \
  "Actual tool  •  arguments  •  result count  •  latency"
make_clip 05 04-incidents-and-context.png 18 \
  "Why is payments failing again?" \
  "Previous incidents and service context arrive through WebMCP"
make_clip 06 05-dependencies-and-decisions.png 16 \
  "OrgMemory connects the evidence" \
  "Shared PostgreSQL blast radius  •  prior concurrency decision"
make_clip 07 07-session-one-answer.png 18 \
  "The first agent starts from organizational precedent" \
  "Incidents  •  dependencies  •  procedure  •  decisions"
make_clip 08 08-human-approval-gate.png 14 \
  "The agent proposes. A human decides." \
  "Nothing is saved until explicit approval"
make_clip 09 09-fresh-agent-bridge.png 18 \
  "A brand-new agent starts ahead" \
  "No shared chat  •  no carried context  •  durable company memory"
make_clip 10 10-fresh-agent-answer.png 18 \
  "The memory survives the session" \
  "The next agent recovers the same verified operating context"
make_clip 11 11-governed-tools.png 14 \
  "Capability is not authorization" \
  "Read automatically  •  propose safely  •  decide explicitly"
make_clip 12 01-command-center.png 12 \
  "OrgMemory is the long-term memory layer for browser agents" \
  "Understand what happened before acting on what is happening now"

ffmpeg -hide_banner -loglevel error -y \
  -i "$WORK/01.mp4" -i "$WORK/02.mp4" -i "$WORK/03.mp4" \
  -i "$WORK/04.mp4" -i "$WORK/05.mp4" -i "$WORK/06.mp4" \
  -i "$WORK/07.mp4" -i "$WORK/08.mp4" -i "$WORK/09.mp4" \
  -i "$WORK/10.mp4" -i "$WORK/11.mp4" -i "$WORK/12.mp4" \
  -filter_complex "[0:v][1:v][2:v][3:v][4:v][5:v][6:v][7:v][8:v][9:v][10:v][11:v]concat=n=12:v=1:a=0[v]" \
  -map "[v]" -an -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p \
  -r 30 -t 180 -movflags +faststart "$SILENT"

/usr/bin/say -v Samantha -r 180 -f "$ROOT/narration.txt" -o "$NARRATION_RAW"

if [[ ! -s "$NARRATION_RAW" ]] || [[ "$(stat -f%z "$NARRATION_RAW")" -lt 100000 ]]; then
  printf 'Narration generation failed. Run this script on macOS with speech synthesis available.\n' >&2
  exit 1
fi

NARRATION_DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$NARRATION_RAW")"
TEMPO="$(awk -v d="$NARRATION_DURATION" 'BEGIN {printf "%.6f", d/170}')"

ffmpeg -hide_banner -loglevel error -y \
  -i "$NARRATION_RAW" \
  -af "atempo=$TEMPO,highpass=f=90,lowpass=f=9500,acompressor=threshold=0.12:ratio=3:attack=15:release=180,volume=1.2,apad=pad_dur=180" \
  -t 180 -c:a pcm_s16le "$NARRATION_FIT"

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -t 180 -i "sine=frequency=110:sample_rate=48000" \
  -f lavfi -t 180 -i "sine=frequency=164.81:sample_rate=48000" \
  -f lavfi -t 180 -i "anoisesrc=color=pink:sample_rate=48000" \
  -filter_complex "[0:a]volume=0.017,tremolo=f=0.10:d=0.35[a0];[1:a]volume=0.009,tremolo=f=0.10:d=0.28[a1];[2:a]lowpass=f=700,volume=0.004[a2];[a0][a1][a2]amix=inputs=3:duration=longest:normalize=0,afade=t=in:st=0:d=2,afade=t=out:st=176:d=4[m]" \
  -map "[m]" -c:a pcm_s16le "$MUSIC"

ffmpeg -hide_banner -loglevel error -y \
  -i "$NARRATION_FIT" -i "$MUSIC" \
  -filter_complex "[0:a]volume=1.0[n];[1:a]volume=0.60[m];[n][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]" \
  -map "[a]" -t 180 -c:a aac -b:a 192k "$MIX"

ffmpeg -hide_banner -loglevel error -y \
  -i "$SILENT" -i "$MIX" -i "$ROOT/captions.srt" \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=eng -metadata:s:s:0 title=English \
  -t 180 -movflags +faststart "$OUTPUT"

ffmpeg -hide_banner -loglevel error -y -ss 7 -i "$OUTPUT" -frames:v 1 "$POSTER"

DURATION="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUTPUT")"
printf 'Rendered %s (%ss)\n' "$OUTPUT" "$DURATION"
