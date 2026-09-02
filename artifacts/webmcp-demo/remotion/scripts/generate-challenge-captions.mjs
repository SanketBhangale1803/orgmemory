import { readFile, writeFile } from "node:fs/promises";

const source = new URL("../../narration-challenge-slow.txt", import.meta.url);
const destination = new URL("../public/captions-challenge-slow.json", import.meta.url);
const input = await readFile(source, "utf8");

const spokenWords = input.trim().split(/\s+/);
const totalWords = spokenWords.length;
const startMs = 1000;
const endMs = 181150;
const msPerWord = (endMs - startMs) / totalWords;

const displayText = input
  .replaceAll("Web M C P", "WebMCP")
  .replaceAll("get OrgMemory briefing", "get_orgmemory_briefing")
  .replaceAll("record OrgMemory outcome", "record_orgmemory_outcome")
  .replaceAll("I D", "ID");

const tokens = displayText.trim().split(/\s+/);
const chunks = [];
let current = [];

for (const token of tokens) {
  current.push(token);
  const sentenceEnd = /[.!?][\"”]?$/.test(token);
  if (current.length >= 9 || (sentenceEnd && current.length >= 4)) {
    chunks.push(current);
    current = [];
  }
}
if (current.length) chunks.push(current);

let cursorWords = 0;
const captions = chunks.map((chunk) => {
  const spokenCount = chunk
    .join(" ")
    .replaceAll("WebMCP", "Web M C P")
    .replaceAll("get_orgmemory_briefing", "get OrgMemory briefing")
    .replaceAll("record_orgmemory_outcome", "record OrgMemory outcome")
    .replaceAll("ID", "I D")
    .split(/\s+/).length;
  const captionStart = Math.round(startMs + cursorWords * msPerWord);
  cursorWords += spokenCount;
  const captionEnd = Math.round(startMs + cursorWords * msPerWord);
  return {
    text: ` ${chunk.join(" ")}`,
    startMs: captionStart,
    endMs: captionEnd,
    timestampMs: null,
    confidence: 1,
  };
});

await writeFile(destination, `${JSON.stringify(captions, null, 2)}\n`);
console.log(`Wrote ${captions.length} captions for ${totalWords} spoken words.`);
