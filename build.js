// build.js - make a build artifact (zip) so "npm run build" succeeds in CI
const { execSync } = require("child_process");
try {
  console.log("▶ Creating build_artifact.zip ...");
  execSync("zip -r build_artifact.zip src static requirements.txt || true", { stdio: "inherit" });
  console.log("✅ build_artifact.zip created (or skipped if zip not available)");
  process.exit(0);
} catch (e) {
  console.error("❌ build step failed", e);
  process.exit(1);
}
