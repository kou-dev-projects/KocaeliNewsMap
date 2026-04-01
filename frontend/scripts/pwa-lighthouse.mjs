import { spawn } from "node:child_process";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  readJsonFile,
  resolveChromePath,
  resolveOutputPath,
  withQaServer,
} from "./pwa-shared.mjs";

const chromePath = await resolveChromePath();
const outputPath = resolveOutputPath("lighthouse-pwa-report.json");
const tempDir = resolveOutputPath(".lighthouse-tmp");
const lighthouseCliPath = resolveOutputPath("node_modules/lighthouse/cli/index.js");

await mkdir(tempDir, { recursive: true });

await withQaServer(async (baseUrl) => {
  const args = [
    baseUrl,
    "--only-categories=pwa",
    `--chrome-path=${chromePath}`,
    "--output=json",
    `--output-path=${outputPath}`,
    "--quiet",
    "--no-enable-error-reporting",
  ];

  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [lighthouseCliPath, ...args], {
      cwd: process.cwd(),
      env: {
        ...process.env,
        TEMP: tempDir,
        TMP: tempDir,
        TMPDIR: tempDir,
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
    const stdoutChunks = [];
    const stderrChunks = [];

    child.stdout.on("data", (chunk) => {
      stdoutChunks.push(chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderrChunks.push(chunk);
    });

    child.on("exit", (code) => {
      if (code === 0) {
        const stdout = Buffer.concat(stdoutChunks).toString("utf-8").trim();
        if (stdout) {
          console.log(stdout);
        }
        resolve(undefined);
        return;
      }

      readFile(outputPath, "utf-8")
        .then(() => {
          const stderr = Buffer.concat(stderrChunks).toString("utf-8");
          const isWindowsCleanupNoise =
            stderr.includes("Launcher.destroyTmp") &&
            stderr.includes("EPERM") &&
            stderr.includes(".lighthouse-tmp");
          if (!isWindowsCleanupNoise) {
            console.warn(
              `Lighthouse exited with code ${code ?? -1}, but a report file was produced. Continuing with that report.`,
            );
          }
          resolve(undefined);
        })
        .catch(() => {
          const stderr = Buffer.concat(stderrChunks).toString("utf-8").trim();
          reject(
            new Error(
              `Lighthouse exited with code ${code ?? -1}.${stderr ? `\n${stderr}` : ""}`,
            ),
          );
        });
    });
    child.on("error", reject);
  });
});

const report = JSON.parse(await readFile(outputPath, "utf-8"));
const officialPwaScore =
  report.categories?.pwa?.score == null
    ? null
    : Math.round(report.categories.pwa.score * 100);

function getCategoryScore(name) {
  const score = report.categories?.[name]?.score;
  return score == null ? null : Math.round(score * 100);
}

async function hasFile(relativePath) {
  try {
    await access(path.join(process.cwd(), relativePath));
    return true;
  } catch {
    return false;
  }
}

async function buildDerivedReadinessChecks(baseUrl) {
  const manifest = await readJsonFile("public/manifest.json");
  const offlineSummary = await readJsonFile("pwa-offline-summary.json").catch(() => null);
  const manifestIcons = Array.isArray(manifest.icons) ? manifest.icons : [];
  const requiredFieldsPresent = Boolean(
    typeof manifest.name === "string" &&
      manifest.name.trim() &&
      typeof manifest.short_name === "string" &&
      manifest.short_name.trim() &&
      typeof manifest.start_url === "string" &&
      manifest.start_url.trim() &&
      typeof manifest.display === "string" &&
      manifest.display.trim() &&
      typeof manifest.theme_color === "string" &&
      manifest.theme_color.trim() &&
      typeof manifest.background_color === "string" &&
      manifest.background_color.trim(),
  );

  const hasStandardIcons =
    manifestIcons.some(
      (icon) => icon.src === "/icons/icon-192.png" && icon.sizes === "192x192",
    ) &&
    manifestIcons.some(
      (icon) => icon.src === "/icons/icon-512.png" && icon.sizes === "512x512",
    );

  const hasMaskableIcons =
    manifestIcons.some(
      (icon) =>
        icon.src === "/icons/icon-maskable-192.png" &&
        String(icon.purpose || "").includes("maskable"),
    ) &&
    manifestIcons.some(
      (icon) =>
        icon.src === "/icons/icon-maskable-512.png" &&
        String(icon.purpose || "").includes("maskable"),
    );

  const checks = [
    {
      id: "secure-context",
      label: "App is served from a secure local origin",
      passed: /^https:\/\//.test(baseUrl) || /127\.0\.0\.1|localhost/.test(baseUrl),
    },
    {
      id: "manifest-fields",
      label: "Manifest includes required installability fields",
      passed: requiredFieldsPresent,
    },
    {
      id: "standard-icons",
      label: "Manifest includes 192px and 512px icons",
      passed: hasStandardIcons,
    },
    {
      id: "maskable-icons",
      label: "Manifest includes maskable icons",
      passed: hasMaskableIcons,
    },
    {
      id: "apple-touch-icon",
      label: "Apple touch icon asset exists",
      passed: await hasFile("public/icons/apple-touch-icon.png"),
    },
    {
      id: "service-worker",
      label: "Service worker file exists",
      passed: await hasFile("public/sw.js"),
    },
    {
      id: "offline-fallback",
      label: "Offline fallback document exists",
      passed: await hasFile("public/offline.html"),
    },
    {
      id: "offline-map-smoke",
      label: "Offline map smoke test passed",
      passed: Boolean(offlineSummary?.passed),
    },
  ];

  const passedChecks = checks.filter((check) => check.passed).length;
  const score = Math.round((passedChecks / checks.length) * 100);

  return {
    checks,
    score,
  };
}

const derivedReadiness = await buildDerivedReadinessChecks(report.finalDisplayedUrl);
const summaryScore = officialPwaScore ?? derivedReadiness.score;
const usedDerivedReadiness = officialPwaScore == null;

await writeFile(
  resolveOutputPath("lighthouse-pwa-summary.json"),
  JSON.stringify(
    {
      score: summaryScore,
      url: report.finalDisplayedUrl,
      category: "pwa",
      officialPwaScore,
      usedDerivedReadiness,
      note: usedDerivedReadiness
        ? "The dedicated Lighthouse PWA category is deprecated in current Chrome/Lighthouse builds. This summary falls back to a reproducible PWA readiness score based on installability and offline checks."
        : undefined,
      readinessChecks: usedDerivedReadiness ? derivedReadiness.checks : undefined,
      lighthouseScores: {
        performance: getCategoryScore("performance"),
        accessibility: getCategoryScore("accessibility"),
        bestPractices: getCategoryScore("best-practices"),
        seo: getCategoryScore("seo"),
      },
    },
    null,
    2,
  ),
  "utf-8",
);

if (usedDerivedReadiness) {
  console.log(
    `Official Lighthouse PWA category is unavailable. Derived PWA readiness score: ${summaryScore}`,
  );
} else {
  console.log(`PWA Lighthouse score: ${summaryScore}`);
}

if (summaryScore < 90) {
  process.exitCode = 1;
}
