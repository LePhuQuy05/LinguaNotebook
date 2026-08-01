import { render, screen } from "@testing-library/react";

import { MarkdownContent } from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders a GFM table as a real <table>, not literal pipes", () => {
    const markdown = "| 単語 | 意味 |\n| --- | --- |\n| 行く | to go |";

    const { container } = render(<MarkdownContent content={markdown} />);

    expect(container.querySelector("table")).toBeInTheDocument();
    expect(screen.queryByText(/\|/)).not.toBeInTheDocument();
    expect(screen.getByText("行く")).toBeInTheDocument();
  });

  it("renders headings as heading elements", () => {
    render(<MarkdownContent content="# はじめに" />);

    expect(
      screen.getByRole("heading", { name: "はじめに" }),
    ).toBeInTheDocument();
  });

  it("renders plain paragraph text", () => {
    render(<MarkdownContent content="本文です。" />);

    expect(screen.getByText("本文です。")).toBeInTheDocument();
  });
});
