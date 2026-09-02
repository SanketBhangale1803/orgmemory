import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

await loadFont({
  family: "OrgMemory Sans",
  url: staticFile("SFNS.ttf"),
  format: "truetype",
  display: "block",
});
