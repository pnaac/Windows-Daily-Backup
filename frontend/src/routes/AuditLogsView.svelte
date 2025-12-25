<script>
  import { auditLogs, backupStore } from "../stores/backupStore";
  import { fade } from "svelte/transition";

  // Subscribe to the derived store
  // $auditLogs is an array sorted by timestamp DESC
</script>

<div class="h-full flex flex-col" in:fade={{ duration: 200 }}>
  <!-- Header -->
  <header class="flex justify-between items-center mb-8">
    <div>
      <h1
        class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary"
      >
        Audit Log
      </h1>
      <p class="text-slate-400 mt-1">
        Track administrative actions and system changes
      </p>
    </div>

    <div class="stats bg-slate-800 shadow text-slate-200">
      <div class="stat place-items-center p-4">
        <div class="stat-title text-slate-400 text-xs uppercase tracking-wider">
          Total Events
        </div>
        <div class="stat-value text-secondary text-2xl">
          {$auditLogs.length}
        </div>
      </div>
    </div>
  </header>

  <!-- Content (Data Grid) -->
  <div
    class="flex-1 overflow-auto bg-slate-800/50 rounded-2xl border border-slate-700/50 backdrop-blur-sm shadow-xl p-1"
  >
    {#if $backupStore.loading}
      <div class="h-full flex items-center justify-center">
        <span class="loading loading-ring loading-lg text-primary"></span>
      </div>
    {:else if $auditLogs.length === 0}
      <div
        class="h-full flex flex-col items-center justify-center text-slate-500"
      >
        <div class="w-16 h-16 mb-4 opacity-50">
          <!-- Simple Document Text Icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="w-full h-full"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.404 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
        </div>
        <p>No audit logs found.</p>
      </div>
    {:else}
      <table class="table w-full text-left">
        <thead
          class="text-xs text-slate-400 uppercase bg-slate-900/50 sticky top-0 z-10"
        >
          <tr>
            <th class="py-4 px-6 font-medium tracking-wider">Time</th>
            <th class="py-4 px-6 font-medium tracking-wider">User</th>
            <th class="py-4 px-6 font-medium tracking-wider">Action</th>
            <th class="py-4 px-6 font-medium tracking-wider">Target</th>
            <th class="py-4 px-6 font-medium tracking-wider">Details</th>
          </tr>
        </thead>
        <tbody class="text-sm divide-y divide-slate-700/50">
          {#each $auditLogs as log (log.timestamp)}
            <tr class="hover:bg-white/5 transition-colors">
              <td class="py-4 px-6 whitespace-nowrap text-slate-400 font-mono">
                {new Date(log.timestamp).toLocaleString()}
              </td>
              <td class="py-4 px-6 font-medium text-slate-200">
                <div class="flex items-center gap-2">
                  <div class="avatar placeholder">
                    <div class="bg-indigo-900 text-indigo-200 rounded-full w-6">
                      <span class="text-xs"
                        >{log.user
                          ? log.user.charAt(0).toUpperCase()
                          : "?"}</span
                      >
                    </div>
                  </div>
                  {log.user || "Unknown"}
                </div>
              </td>
              <td class="py-4 px-6">
                <!-- Badge color coding -->
                {#if log.action.includes("DELETE")}
                  <span
                    class="badge badge-error badge-sm bg-red-500/20 text-red-300 border-0 font-bold"
                    >{log.action}</span
                  >
                {:else if log.action.includes("CREATE")}
                  <span
                    class="badge badge-success badge-sm bg-emerald-500/20 text-emerald-300 border-0 font-bold"
                    >{log.action}</span
                  >
                {:else if log.action.includes("UPDATE")}
                  <span
                    class="badge badge-warning badge-sm bg-amber-500/20 text-amber-300 border-0 font-bold"
                    >{log.action}</span
                  >
                {:else}
                  <span class="badge badge-ghost badge-sm">{log.action}</span>
                {/if}
              </td>
              <td class="py-4 px-6 text-slate-300 font-mono text-xs">
                {log.target}
              </td>
              <td
                class="py-4 px-6 text-slate-400 max-w-md truncate"
                title={JSON.stringify(log.details)}
              >
                {typeof log.details === "object"
                  ? JSON.stringify(log.details)
                  : log.details}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>
