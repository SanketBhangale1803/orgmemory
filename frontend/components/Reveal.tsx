"use client";

import { useEffect } from "react";

/* Adds `.shown` to every `.reveal` as it enters the viewport. One observer for
   the whole page; elements are unobserved once revealed so scrolling back up
   never replays the animation. */
export default function Reveal() {
  useEffect(() => {
    const targets = Array.from(document.querySelectorAll<HTMLElement>(".reveal"));
    if (!targets.length) return;

    if (!("IntersectionObserver" in window)) {
      targets.forEach((node) => node.classList.add("shown"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("shown");
          observer.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
    );
    targets.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  return null;
}
