import { writable, derived } from "svelte/store";
import { db, ref, onValue, update as firebaseUpdate, push } from "../lib/firebase";

function createBackupStore() {
  const { subscribe, set, update } = writable({
    systems: {},
    configurations: {},
    runtime_state: {},
    logs: {},
    audit_logs: {},
    loading: true,
    error: null,
  });

  let unsubscribe = () => {};

  return {
    subscribe,
    init: (userId) => {
      // userId not strictly needed if reading whole root, but good practice if rules change
      const rootRef = ref(db, "/");
      unsubscribe = onValue(
        rootRef,
        (snapshot) => {
          const data = snapshot.val() || {};
          update((s) => ({
            ...s,
            systems: data.systems || {},
            configurations: data.configurations || {},
            runtime_state: data.runtime_state || {},
            logs: data.logs || {},
            audit_logs: data.audit_logs || {},
            loading: false,
          }));
        },
        (error) => {
          console.error("Firebase Read Error:", error);
          update((s) => ({ ...s, error: error.message, loading: false }));
        }
      );
    },
    refresh: (userId) => {
      // Force unmount and remount listener
      unsubscribe();
      update((s) => ({ ...s, loading: true }));
      // Small delay to ensure clean state reset visually
      setTimeout(() => {
        const rootRef = ref(db, "/");
        unsubscribe = onValue(
          rootRef,
          (snapshot) => {
            const data = snapshot.val() || {};
            update((s) => ({
              ...s,
              systems: data.systems || {},
              configurations: data.configurations || {},
              runtime_state: data.runtime_state || {},
              logs: data.logs || {},
              audit_logs: data.audit_logs || {},
              loading: false,
            }));
          },
          (error) => {
            console.error("Firebase Read Error:", error);
            update((s) => ({ ...s, error: error.message, loading: false }));
          }
        );
      }, 500);
    },
    destroy: () => unsubscribe(),
  };
}

export const backupStore = createBackupStore();

// Derived Stores for simpler UI consumption
export const fleetData = derived(backupStore, ($store) => {
  return Object.entries($store.systems || {}).map(([id, metaWrapper]) => {
    const meta = metaWrapper.meta || {};
    const state = $store.runtime_state[id] || {};
    const config = $store.configurations[id] || {};
    const heartbeat = parseInt(snapshot_heartbeat(id, $store)) || 0;

    // Check online status (2 mins threshold)
    const isOnline = Date.now() / 1000 - heartbeat < 120;

    return {
      id,
      name: meta.nickname || meta.hostname || id,
      hostname: meta.hostname,
      os: meta.os,
      ip: meta.ip,
      status: isOnline ? "Online" : "Offline",
      jobCount: Object.keys(config).length,
      lastHeartbeat: heartbeat,
    };
  });
});
function snapshot_heartbeat(id, store) {
  try {
    return store.systems[id]?.heartbeat || 0;
  } catch {
    return 0;
  }
}

// Derived store for Audit Logs (sorted newest first)
export const auditLogs = derived(backupStore, ($store) => {
  const logs = $store.audit_logs || {};
  return Object.values(logs).sort((a, b) => b.timestamp - a.timestamp);
});

// Helper to Log Actions
export function logAuditAction(userEmail, action, target, details) {
  const newLogRef = push(ref(db, "audit_logs"));
  firebaseUpdate(newLogRef, {
    timestamp: Date.now(),
    user: userEmail,
    action: action, // e.g., "CREATE_JOB", "UPDATE_NICKNAME"
    target: target, // e.g., "System X"
    details: details, // e.g., "Changed from A to B"
  }).catch((err) => console.error("Failed to write audit log:", err));
}
