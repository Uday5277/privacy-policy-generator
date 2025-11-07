// test.js - runs Python pytest so npm test triggers your Python tests in CI
const { execSync } = require("child_process");
try {
  console.log("▶ Running Python tests via pytest...");
  execSync("pytest --maxfail=1 --disable-warnings -q", { stdio: "inherit" });
  console.log("✅ pytest passed");
  process.exit(0);
} catch (err) {
  console.error("❌ pytest failed");
  process.exit(1);
}
