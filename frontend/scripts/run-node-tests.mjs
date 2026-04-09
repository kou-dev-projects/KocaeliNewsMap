import { spawnSync } from "node:child_process";

function getNodeHelpText() {
  const result = spawnSync(process.execPath, ["--help"], {
    encoding: "utf8",
  });

  return `${result.stdout || ""}\n${result.stderr || ""}`;
}

const helpText = getNodeHelpText();
const args = [
  "--experimental-strip-types",
  "--experimental-specifier-resolution=node",
  "--test",
];

if (helpText.includes("--test-isolation")) {
  args.push("--test-isolation=none");
}

if (helpText.includes("--test-concurrency")) {
  args.push("--test-concurrency=1");
}

args.push("tests/**/*.test.mts");

const result = spawnSync(process.execPath, args, {
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error);
  process.exit(1);
}

process.exit(result.status ?? 1);
