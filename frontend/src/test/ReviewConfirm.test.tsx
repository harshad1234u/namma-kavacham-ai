import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { editedSource, ReviewConfirm, type Draft } from "../components/ReviewConfirm";
import { LanguageProvider } from "../i18n/LanguageContext";

const draft: Draft = { body: "Pay Rs 50 fee", source: "pasted_text", screenshot: null, screenshotUrl: null, senderMasked: null };

function setup(overrides: Partial<Draft> = {}) {
  const handlers = { onBack: vi.fn(), onCancel: vi.fn(), onConfirm: vi.fn() };
  render(
    <LanguageProvider>
      <ReviewConfirm draft={{ ...draft, ...overrides }} {...handlers} />
    </LanguageProvider>,
  );
  return handlers;
}

describe("ReviewConfirm", () => {
  it("blocks submission until the user explicitly consents", async () => {
    const { onConfirm } = setup();
    const confirm = screen.getByRole("button", { name: /confirm & analyze/i });
    expect(confirm).toBeDisabled();
    await userEvent.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("checkbox"));
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith("Pay Rs 50 fee", "pasted_text");
  });

  it("submits the edited text and marks the edit", async () => {
    const { onConfirm } = setup();
    const box = screen.getByRole("textbox");
    await userEvent.clear(box);
    await userEvent.type(box, "edited text");
    expect(screen.getByText(/edited during review/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /confirm & analyze/i }));
    expect(onConfirm).toHaveBeenCalledWith("edited text", "pasted_text");
  });

  it("cancel never submits", async () => {
    const { onCancel, onConfirm } = setup();
    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("does not allow empty content", async () => {
    setup({ body: "" });
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: /confirm & analyze/i })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/add some content/i);
  });

  it("labels screenshot text corrected by the user", () => {
    expect(editedSource("ocr", true)).toBe("user_corrected_ocr");
    expect(editedSource("ocr", false)).toBe("ocr");
    expect(editedSource("pasted_text", true)).toBe("pasted_text");
  });
});
