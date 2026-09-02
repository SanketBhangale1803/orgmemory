import { readFile, writeFile } from "node:fs/promises";

const source = new URL("../../narration-final.txt", import.meta.url);
const destination = new URL("../public/captions-final.json", import.meta.url);
const narration = await readFile(source, "utf8");

const displayText = narration
  .replaceAll("get OrgMemory briefing", "get_orgmemory_briefing")
  .replaceAll("record OrgMemory outcome", "record_orgmemory_outcome")
  .replaceAll("I D", "ID")
  .replaceAll(/\s+/g, " ")
  .trim();

const tokens = displayText.split(" ");
const chunks = [];
let current = [];

for (const token of tokens) {
  current.push(token);
  const sentenceEnd = /[.!?][\"”]?$/.test(token);
  if (current.length >= 10 || (sentenceEnd && current.length >= 5)) {
    chunks.push(current);
    current = [];
  }
}
if (current.length) chunks.push(current);

const spokenWordCount = narration.trim().split(/\s+/).length;
const startMs = 600;
const endMs = 165600;
const millisecondsPerSpokenWord = (endMs - startMs) / spokenWordCount;
let spokenCursor = 0;

const captions = chunks.map((chunk) => {
  const captionText = chunk.join(" ");
  const spokenCount = captionText
    .replaceAll("get_orgmemory_briefing", "get OrgMemory briefing")
    .replaceAll("record_orgmemory_outcome", "record OrgMemory outcome")
    .replaceAll("ID", "I D")
    .split(/\s+/).length;
  const captionStart = Math.round(startMs + spokenCursor * millisecondsPerSpokenWord);
  spokenCursor += spokenCount;
  const captionEnd = Math.round(startMs + spokenCursor * millisecondsPerSpokenWord);
  return {
    text: ` ${captionText}`,
    startMs: captionStart,
    endMs: captionEnd,
    timestampMs: null,
    confidence: 1,
  };
});

await writeFile(destination, `${JSON.stringify(captions, null, 2)}\n`);
console.log(`Wrote ${captions.length} captions across ${spokenWordCount} spoken words.`);
