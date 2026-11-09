import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { MotionGlobalConfig } from "motion/react";
import { afterEach, vi } from "vitest";

// Animations finish at once in tests. Otherwise the test browser cancels them when a page closes
// and reports every cancelled animation as an error.
MotionGlobalConfig.skipAnimations = true;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
