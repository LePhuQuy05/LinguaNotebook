"use client";

interface OptionPickerProps {
  options: string[];
  correctIndex: number;
  /** The user's submitted option index; null before submission. */
  selected: number | null;
  disabled: boolean;
  onSelect: (index: number) => void;
}

/**
 * The four clickable answer choices. Before submission each is a plain
 * option; once `selected` is set the correct one turns green, a wrong pick
 * red, and the rest go muted — the user sees why they were wrong.
 */
export function OptionPicker({
  options,
  correctIndex,
  selected,
  disabled,
  onSelect,
}: OptionPickerProps) {
  return (
    <div className="space-y-2">
      {options.map((option, index) => {
        let className =
          "w-full rounded-lg border border-border bg-surface p-4 text-left transition-colors";
        if (disabled) {
          if (index === correctIndex) {
            className += " border-success bg-success-light text-success";
          } else if (index === selected) {
            className += " border-destructive bg-destructive-light text-destructive";
          } else {
            className += " text-foreground-subtle";
          }
        } else {
          className += " text-foreground hover:border-primary-300";
        }
        return (
          <button key={index} disabled={disabled} onClick={() => onSelect(index)} className={className}>
            <span className="mr-2 font-semibold text-foreground-subtle">
              {String.fromCharCode(65 + index)}.
            </span>
            {option}
          </button>
        );
      })}
    </div>
  );
}
