import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  localStorage.clear();
});

// Vitest's built-in shim cannot read jsdom File objects.
URL.createObjectURL = () => "blob:mock";
URL.revokeObjectURL = () => {};
window.scrollTo = () => {};
