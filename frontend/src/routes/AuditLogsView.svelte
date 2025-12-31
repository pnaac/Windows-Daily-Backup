<script>
  import { auditLogs, backupStore } from "../stores/backupStore";
  import { fade, slide } from "svelte/transition";

  let searchQuery = "";

  // Filter logs based on search query
  $: filteredLogs = $auditLogs.filter((log) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (log.user && log.user.toLowerCase().includes(query)) ||
      (log.action && log.action.toLowerCase().includes(query)) ||
      (log.target && log.target.toLowerCase().includes(query)) ||
      (log.details && JSON.stringify(log.details).toLowerCase().includes(query))
    );
  });

  function exportToCSV() {
    if (filteredLogs.length === 0) return;

    const headers = ["Timestamp", "User", "Action", "Target", "Details"];
    const csvContent = [
      headers.join(","),
      ...filteredLogs.map((log) => {
        const row = [
          new Date(log.timestamp).toISOString(),
          log.user || "Unknown",
          log.action,
          log.target,
          `"${JSON.stringify(log.details || {}).replace(/"/g, '""')}"`, // Escape quotes
        ];
        return row.join(",");
      }),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_logs_${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
</script>

<div class="h-full flex flex-col p-2 md:p-6" in:fade={{ duration: 200 }}>
  <!-- Header -->
  <header
    class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4"
  >
    <div>
      <h1 class="text-3xl font-bold text-base-content">Audit Log</h1>
      <p class="text-base-content/60 mt-1">
        Track administrative actions and system changes
      </p>
    </div>

    <div class="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
      <!-- Search Input -->
      <div class="join w-full md:w-auto">
        <div class="relative w-full md:w-64">
          <input
            type="text"
            placeholder="Search logs..."
            bind:value={searchQuery}
            class="input input-bordered input-sm w-full pr-10 bg-base-100 placeholder:text-base-content/40"
          />
          <div
            class="absolute inset-y-0 right-3 flex items-center pointer-events-none"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4 text-base-content/40"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>
      </div>

      <!-- Export Button -->
      <button
        class="btn btn-sm btn-outline gap-2"
        on:click={exportToCSV}
        disabled={filteredLogs.length === 0}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Export CSV
      </button>

      <!-- Stats Card -->
      <div
        class="stats bg-base-200 shadow-sm text-base-content border border-base-300 hidden lg:inline-grid"
      >
        <div class="stat place-items-center py-1 px-4">
          <div
            class="stat-title text-base-content/60 text-xs uppercase tracking-wider"
          >
            Total Events
          </div>
          <div class="stat-value text-primary text-xl">
            {$auditLogs.length}
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Content (Data Grid) -->
  <div
    class="flex-1 overflow-hidden bg-base-100 rounded-2xl border border-base-300 shadow-sm flex flex-col"
  >
    {#if $backupStore.loading}
      <div class="h-full flex items-center justify-center">
        <span class="loading loading-ring loading-lg text-primary"></span>
      </div>
    {:else if filteredLogs.length === 0}
      <div
        class="h-full flex flex-col items-center justify-center text-base-content/50"
      >
        <div class="w-16 h-16 mb-4 opacity-50">
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
        <p>
          {searchQuery ? "No logs match your search" : "No audit logs found"}
        </p>
      </div>
    {:else}
      <div class="overflow-x-auto flex-1 h-full">
        <table class="table table-pin-rows w-full text-left">
          <thead
            class="text-xs uppercase bg-base-200/50 text-base-content/70 backdrop-blur-md z-10"
          >
            <tr>
              <th class="py-4 px-6 font-medium tracking-wider w-48">Time</th>
              <th class="py-4 px-6 font-medium tracking-wider w-40">User</th>
              <th class="py-4 px-6 font-medium tracking-wider w-32">Action</th>
              <th class="py-4 px-6 font-medium tracking-wider w-48">Target</th>
              <th class="py-4 px-6 font-medium tracking-wider">Details</th>
            </tr>
          </thead>
          <tbody class="text-sm divide-y divide-base-200">
            {#each filteredLogs as log (log.timestamp)}
              <tr class="hover:bg-base-200/30 transition-colors group">
                <td
                  class="py-3 px-6 whitespace-nowrap text-base-content/70 font-mono text-xs"
                >
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td class="py-3 px-6 font-medium text-base-content">
                  <div class="flex items-center gap-2">
                    <div class="avatar placeholder">
                      <div
                        class="bg-neutral text-neutral-content rounded-full w-6"
                      >
                        <span class="text-xs">
                          {log.user ? log.user.charAt(0).toUpperCase() : "?"}
                        </span>
                      </div>
                    </div>
                    <span class="truncate max-w-[150px]" title={log.user}
                      >{log.user || "Unknown"}</span
                    >
                  </div>
                </td>
                <td class="py-3 px-6">
                  {#if log.action.includes("DELETE")}
                    <span
                      class="badge badge-error badge-sm font-medium gap-1 bg-error/10 text-error border-0"
                    >
                      {log.action}
                    </span>
                  {:else if log.action.includes("CREATE")}
                    <span
                      class="badge badge-success badge-sm font-medium gap-1 bg-success/10 text-success border-0"
                    >
                      {log.action}
                    </span>
                  {:else if log.action.includes("UPDATE")}
                    <span
                      class="badge badge-warning badge-sm font-medium gap-1 bg-warning/10 text-warning border-0"
                    >
                      {log.action}
                    </span>
                  {:else}
                    <span
                      class="badge badge-ghost badge-sm bg-base-300 text-base-content"
                    >
                      {log.action}
                    </span>
                  {/if}
                </td>
                <td
                  class="py-3 px-6 text-base-content/80 font-mono text-xs truncate max-w-[200px]"
                  title={log.target}
                >
                  {log.target}
                </td>
                <td
                  class="py-3 px-6 text-base-content/60 text-xs font-mono max-w-md"
                >
                  <div class="truncate" title={JSON.stringify(log.details)}>
                    {typeof log.details === "object"
                      ? JSON.stringify(log.details)
                      : log.details}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
