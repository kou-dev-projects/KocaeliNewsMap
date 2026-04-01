import { spawn } from "node:child_process";
import { access, readFile } from "node:fs/promises";
import path from "node:path";

const CHROME_CANDIDATES = [
  process.env.PWA_CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);

const LOCAL_QA_PORT = Number(process.env.PWA_QA_PORT || "3101");
const NEXT_BIN_PATH = path.join(process.cwd(), "node_modules", "next", "dist", "bin", "next");
export const DEFAULT_BASE_URL =
  process.env.PWA_BASE_URL || `http://127.0.0.1:${LOCAL_QA_PORT}`;

export async function resolveChromePath() {
  for (const candidate of CHROME_CANDIDATES) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // Try next candidate.
    }
  }

  throw new Error(
    "No supported Chrome/Edge executable was found. Set PWA_CHROME_PATH to continue.",
  );
}

export function resolveOutputPath(filename) {
  return path.join(process.cwd(), filename);
}

export async function readJsonFile(filename) {
  const raw = await readFile(resolveOutputPath(filename), "utf-8");
  return JSON.parse(raw);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(baseUrl, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(baseUrl, {
        redirect: "manual",
      });
      if (response.ok || response.status === 307 || response.status === 308) {
        return;
      }
    } catch {
      // Retry until timeout.
    }
    await sleep(500);
  }

  throw new Error(`Timed out waiting for QA server at ${baseUrl}.`);
}

async function stopServer(child) {
  if (!child || child.killed) {
    return;
  }

  child.kill();
  await Promise.race([
    new Promise((resolve) => child.once("exit", resolve)),
    sleep(5000),
  ]);
}

export async function withQaServer(run) {
  if (process.env.PWA_BASE_URL) {
    return run(DEFAULT_BASE_URL);
  }

  const child = spawn(
    process.execPath,
    [NEXT_BIN_PATH, "start", "--hostname", "127.0.0.1", "--port", String(LOCAL_QA_PORT)],
    {
      cwd: process.cwd(),
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  const stderrChunks = [];
  child.stderr.on("data", (chunk) => {
    stderrChunks.push(chunk);
  });

  try {
    await waitForServer(DEFAULT_BASE_URL);
    return await run(DEFAULT_BASE_URL);
  } catch (error) {
    const stderr = Buffer.concat(stderrChunks).toString("utf-8").trim();
    if (stderr) {
      throw new Error(
        `${error instanceof Error ? error.message : String(error)}\n${stderr}`,
      );
    }
    throw error;
  } finally {
    await stopServer(child);
  }
}
