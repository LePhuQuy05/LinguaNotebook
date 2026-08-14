import { fireEvent, render, screen } from "@testing-library/react";

import { ChoiceExercise } from "./ChoiceExercise";

describe("ChoiceExercise", () => {
  it("submits the option index and shows the correct answer after a wrong pick", async () => {
    const onSubmit = jest
      .fn()
      .mockResolvedValue({ is_correct: false, correct_answer: "goes to school" });
    const onNext = jest.fn();

    render(
      <ChoiceExercise
        options={["goes to school", "stays home", "sleeps", "eats"]}
        correctIndex={0}
        onSubmit={onSubmit}
        onNext={onNext}
      >
        <p>What is the main idea?</p>
      </ChoiceExercise>,
    );

    fireEvent.click(screen.getByText("sleeps"));
    expect(onSubmit).toHaveBeenCalledWith("2");
    expect(await screen.findByText("Not quite")).toBeInTheDocument();
    expect(screen.getByText("Correct answer:")).toBeInTheDocument();
    // The correct answer shows twice: the highlighted option + the feedback line.
    expect(screen.getAllByText("goes to school").length).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByText("Next →"));
    expect(onNext).toHaveBeenCalled();
  });

  it("submits typed text for legacy items that carry no structured options", async () => {
    const onSubmit = jest.fn().mockResolvedValue({ is_correct: true, correct_answer: null });
    const onNext = jest.fn();

    render(
      <ChoiceExercise
        onSubmit={onSubmit}
        onNext={onNext}
        textInput={{ placeholder: "Type your answer...", submitLabel: "Submit Answer" }}
      >
        <p>What does this term mean?</p>
      </ChoiceExercise>,
    );

    fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
      target: { value: "weather" },
    });
    fireEvent.click(screen.getByText("Submit Answer"));

    expect(onSubmit).toHaveBeenCalledWith("weather");
    expect(await screen.findByText("Correct! 🎉")).toBeInTheDocument();
    expect(onNext).not.toHaveBeenCalled(); // user advances via the Next button
  });
});
