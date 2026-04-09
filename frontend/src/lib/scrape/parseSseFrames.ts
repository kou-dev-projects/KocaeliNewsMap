export type ParsedSseFrame = {
  id?: string;
  event?: string;
  data?: string;
  isComment: boolean;
};

export function parseSseFrames(buffer: string): {
  frames: ParsedSseFrame[];
  remaining: string;
} {
  const normalizedBuffer = buffer.replace(/\r\n/g, "\n");
  const frames: ParsedSseFrame[] = [];
  let position = 0;
  let delimiterIndex = normalizedBuffer.indexOf("\n\n");

  while (delimiterIndex !== -1) {
    const rawFrame = normalizedBuffer.slice(position, delimiterIndex);
    position = delimiterIndex + 2;

    if (rawFrame.trim()) {
      const frame: ParsedSseFrame = { isComment: false };

      for (const rawLine of rawFrame.split("\n")) {
        const line = rawLine.replace(/\r$/, "");

        if (!line) {
          continue;
        }

        if (line.startsWith(":")) {
          frame.isComment = true;
          continue;
        }

        const separatorIndex = line.indexOf(":");
        if (separatorIndex === -1) {
          continue;
        }

        const field = line.slice(0, separatorIndex);
        const value =
          line[separatorIndex + 1] === " "
            ? line.slice(separatorIndex + 2)
            : line.slice(separatorIndex + 1);

        if (field === "id") {
          frame.id = value;
        } else if (field === "event") {
          frame.event = value;
        } else if (field === "data") {
          frame.data = frame.data ? `${frame.data}\n${value}` : value;
        }
      }

      if (frame.isComment || frame.data) {
        frames.push(frame);
      }
    }

    delimiterIndex = normalizedBuffer.indexOf("\n\n", position);
  }

  return {
    frames,
    remaining: normalizedBuffer.slice(position),
  };
}
