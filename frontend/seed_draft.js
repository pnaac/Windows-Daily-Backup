
import { db } from "./src/lib/firebase.js";
import { ref, set } from "firebase/database";

const testSystemId = "test-system-001";

async function seed() {
  console.log("Seeding test data...");

  try {
    // Seed System Meta
    await set(ref(db, `systems/${testSystemId}/meta`), {
      hostname: "Verification-Node",
      ip: "192.168.1.100",
      os: "Windows 11 Enterprise",
      nickname: "Original Nickname"
    });

    // Seed Heartbeat (Online)
    await set(ref(db, `systems/${testSystemId}/heartbeat`), Math.floor(Date.now() / 1000));

    console.log("Seeding complete: Created " + testSystemId);
    process.exit(0);
  } catch (error) {
    console.error("Seeding failed", error);
    process.exit(1);
  }
}

// Since this is a module, we depend on how it's executed. 
// For simplicity in this env, we might need to run it via a specific runner or just use the app dev server context.
// Actually, running a standalone script with 'import' requires "type": "module" in package.json (which we have).
// But firebase init might require DOM/Auth if not admin.
// Wait, the frontend firebase.js uses client SDK. It might need auth.
// This approach is risky if rules block unauth writes.
// Better approach: Agent Side Python Script.
