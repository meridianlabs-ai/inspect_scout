import { ANSIColor, ANSIOutput, ANSIOutputRun, ANSIStyle } from "ansi-output";
import clsx from "clsx";
import { CSSProperties, FC } from "react";
import "./AnsiDisplay.css";

interface ANSIDisplayProps {
  output: string;
  style?: CSSProperties;
  className?: string[] | string;
}

export const ANSIDisplay: FC<ANSIDisplayProps> = ({
  output,
  style,
  className,
}) => {
  const ansiOutput = new ANSIOutput();
  ansiOutput.processOutput(output);

  // Find the index of the first line with output
  const firstOutputIndex = ansiOutput.outputLines.findIndex(
    (line) => line.outputRuns.length > 0
  );

  return (
    <div className={clsx("ansi-display", className)} style={{ ...style }}>
      {ansiOutput.outputLines.map((line, index) => {
        return (
          <div key={index} className={"ansi-display-line"}>
            {!line.outputRuns.length ? (
              index >= firstOutputIndex ? (
                <br />
              ) : null
            ) : (
              line.outputRuns.map((outputRun) => (
                <OutputRun key={outputRun.id} run={outputRun} />
              ))
            )}
          </div>
        );
      })}
    </div>
  );
};

const kForeground = 0;
const kBackground = 1;

interface OutputRunProps {
  run: ANSIOutputRun;
}

const OutputRun: FC<OutputRunProps> = ({ run }) => {
  // Render.
  return <span style={computeCSSProperties(run)}>{run.text}</span>;
};

const computeCSSProperties = (outputRun: ANSIOutputRun) => {
  return !outputRun.format
    ? {}
    : {
        ...computeStyles(outputRun.format.styles || []),
        ...computeForegroundBackgroundColor(
          kForeground,
          outputRun.format.foregroundColor
        ),
        ...computeForegroundBackgroundColor(
          kBackground,
          outputRun.format.backgroundColor
        ),
      };
};

const computeStyles = (styles: ANSIStyle[]) => {
  let cssProperties = {};
  styles.forEach((style) => {
    switch (style) {
      // Bold.
      case ANSIStyle.Bold:
        cssProperties = { ...cssProperties, ...{ fontWeight: "bold" } };
        break;

      // Dim.
      case ANSIStyle.Dim:
        cssProperties = { ...cssProperties, ...{ fontWeight: "lighter" } };
        break;

      // Italic.
      case ANSIStyle.Italic:
        cssProperties = { ...cssProperties, ...{ fontStyle: "italic" } };
        break;

      // Underlined.
      case ANSIStyle.Underlined:
        cssProperties = {
          ...cssProperties,
          ...{
            textDecorationLine: "underline",
            textDecorationStyle: "solid",
          },
        };
        break;

      // Slow blink.
      case ANSIStyle.SlowBlink:
        cssProperties = {
          ...cssProperties,
          ...{ animation: "ansi-display-run-blink 1s linear infinite" },
        };
        break;

      // Rapid blink.
      case ANSIStyle.RapidBlink:
        cssProperties = {
          ...cssProperties,
          ...{ animation: "ansi-display-run-blink 0.5s linear infinite" },
        };
        break;

      // Hidden.
      case ANSIStyle.Hidden:
        cssProperties = { ...cssProperties, ...{ visibility: "hidden" } };
        break;

      // CrossedOut.
      case ANSIStyle.CrossedOut:
        cssProperties = {
          ...cssProperties,
          ...{
            textDecorationLine: "line-through",
            textDecorationStyle: "solid",
          },
        };
        break;

      // TODO Fraktur

      // DoubleUnderlined.
      case ANSIStyle.DoubleUnderlined:
        cssProperties = {
          ...cssProperties,
          ...{
            textDecorationLine: "underline",
            textDecorationStyle: "double",
          },
        };
        break;

      // TODO Framed
      // TODO Encircled
      // TODO Overlined
      // TODO Superscript
      // TODO Subscript
    }
  });

  return cssProperties;
};

const isStandardANSIColor = (color: string): boolean => {
  return Object.values(ANSIColor).includes(color as ANSIColor);
};

const computeForegroundBackgroundColor = (
  colorType: number,
  color?: string
) => {
  // Undefined.
  if (!color) {
    return {};
  }

  // One of the standard colors.
  if (isStandardANSIColor(color)) {
    if (colorType === kForeground) {
      return { color: `var(--${color})` };
    } else {
      return { background: `var(--${color})` };
    }
  }

  // TODO@softwarenerd - This isn't hooked up.
  // Custom color (e.g., hex codes).
  if (colorType === kForeground) {
    return { color: color };
  } else {
    return { background: color };
  }
};
