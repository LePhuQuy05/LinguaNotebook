import { fireEvent, render, screen } from "@testing-library/react";

import { Flashcard } from "./Flashcard";

describe("Flashcard", () => {
  it("shows the term + reading on the front and definition + example on the back", () => {
    render(
      <Flashcard
        item={{
          id: "1",
          item_type: "flashcard",
          question: "What does this term mean?",
          correct_answer: "weather",
          data: {
            term: "天気",
            reading: "てんき",
            definition: "weather",
            example: "今日はいい天気です。",
          },
        }}
        onSubmit={jest.fn()}
        onNext={jest.fn()}
      />,
    );

    expect(screen.getByText("天気")).toBeInTheDocument();
    expect(screen.getByText("てんき")).toBeInTheDocument();

    fireEvent.click(screen.getByText("天気"));
    expect(screen.getByText("weather")).toBeInTheDocument();
    expect(screen.getByText("今日はいい天気です。")).toBeInTheDocument();
  });

  it("grades by self-rating and reveals the verdict before Next", async () => {
    const onSubmit = jest.fn().mockResolvedValue({ is_correct: true, correct_answer: null });
    const onNext = jest.fn();

    render(
      <Flashcard
        item={{
          id: "1",
          item_type: "flashcard",
          question: "What does this term mean?",
          correct_answer: "weather",
          data: { term: "天気" },
        }}
        onSubmit={onSubmit}
        onNext={onNext}
      />,
    );

    fireEvent.click(screen.getByText("天気")); // flip
    fireEvent.click(screen.getByText("5")); // "Easy"

    expect(onSubmit).toHaveBeenCalledWith("", 5);
    expect(await screen.findByText("Correct! 🎉")).toBeInTheDocument();
    expect(onNext).not.toHaveBeenCalled();
  });
});
