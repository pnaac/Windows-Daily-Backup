<script>
  import { backupStore, logAuditAction } from "../stores/backupStore";
  import { auth } from "../lib/firebase";
  import { createEventDispatcher } from "svelte";
  import { Icons } from "../components/Icons";
  import { db, ref, update, remove } from "../lib/firebase";

  export let systemId;
  export let currentUser; // Received from App.svelte

  const dispatch = createEventDispatcher();
  // Subscribe to store and derive data for this system
  // @ts-ignore
  $: systemMeta = $backupStore.systems[systemId]?.meta || {};
  // @ts-ignore
  $: jobs = $backupStore.configurations[systemId] || {};
  // @ts-ignore
  $: jobStates = $backupStore.runtime_state[systemId]?.job_states || {};

  $: kpiTotalJobs = Object.keys(jobs).length;

  // Local State
  let isEditing = false;
  let editingJobId = null;
  let jobForm = {
    name: "",
    source_path: "",
    remote_folder: "",
    schedule: { type: "daily", time: "21:00" },
    retention: { days: 60 },
  };

  // Nickname State
  let isEditingNickname = false;
  let newNickname = "";

  function startEditNickname() {
    newNickname = systemMeta.nickname || systemMeta.hostname || "";
    isEditingNickname = true;
  }
  function saveNickname() {
    update(ref(db, `systems/${systemId}/meta`), { nickname: newNickname });
    logAuditAction(
      currentUser?.email,
      "UPDATE_NICKNAME",
      systemId,
      `Changed nickname to "${newNickname}"`
    );
    isEditingNickname = false;
  }
  function openJobEditor(jobId = null) {
    isEditing = true;
    editingJobId = jobId;
    if (jobId && jobs[jobId]) {
      jobForm = JSON.parse(JSON.stringify(jobs[jobId])); // Deep copy
    } else {
      jobForm = {
        name: "New Backup Job",
        source_path: "D:\\",
        remote_folder: "Backups",
        schedule: { type: "daily", time: "21:00" },
        retention: { days: 60 },
      };
    }
  }

  function saveJob() {
    const id = editingJobId || `JOB_${Date.now()}`;
    update(ref(db, `configurations/${systemId}/${id}`), jobForm);

    logAuditAction(
      currentUser?.email,
      editingJobId ? "UPDATE_JOB" : "CREATE_JOB",
      systemId,
      `Saved job "${jobForm.name}" (${id})`
    );
    isEditing = false;
  }

  // Confirmation Modal State
  let confirmState = {
    isOpen: false,
    title: "",
    message: "",
    isDanger: false,
    onConfirm: () => {},
  };

  function openConfirmModal({ title, message, isDanger, onConfirm }) {
    confirmState = { isOpen: true, title, message, isDanger, onConfirm };
    // @ts-ignore
    document.getElementById("confirmation_modal").showModal();
  }

  function handleConfirm() {
    confirmState.onConfirm();
    // @ts-ignore
    document.getElementById("confirmation_modal").close();
    confirmState.isOpen = false;
  }

  function triggerJob(jobId) {
    openConfirmModal({
      title: "Run Backup Job?",
      message: `Are you sure you want to run "${jobs[jobId].name}" immediately?`,
      isDanger: false,
      onConfirm: () => {
        update(ref(db, `control/${systemId}`), { trigger_now: jobId });
        logAuditAction(
          currentUser?.email,
          "TRIGGER_JOB",
          systemId,
          `Manually triggered job "${jobs[jobId].name}"`
        );
      },
    });
  }

  $: kpiLastActive = Object.values(jobStates).reduce((latest, state) => {
    if (!state.last_run) return latest;
    return state.last_run > latest ? state.last_run : latest;
  }, ""); // Init empty strings, because "2024" < "Never" in string compare

  $: kpiLastActiveDisplay = kpiLastActive || "Never";

  $: kpiHealth = Object.values(jobStates).filter(
    (s) => s.status === "Success"
  ).length;

  function deleteJob(jobId) {
    openConfirmModal({
      title: "Delete Job?",
      message: "This will permanently remove this backup configuration.",
      isDanger: true,
      onConfirm: () => {
        const jobName = jobs[jobId]?.name || jobId;
        update(ref(db, `configurations/${systemId}/${jobId}`), null);
        logAuditAction(
          currentUser?.email,
          "DELETE_JOB",
          systemId,
          `Deleted job "${jobName}" (${jobId})`
        );
      },
    });
  }

  function deleteSystem() {
    if (currentUser?.email?.toLowerCase() === "admin@kriplanibuilders.com") {
      openConfirmModal({
        title: "DANGER: Delete System?",
        message:
          "Are you sure you want to PERMANENTLY delete this system?\n\nThis will remove all configurations, logs, and metadata for this machine from the dashboard.\n\nThe Agent on the machine will need to be re-run to re-register.",
        isDanger: true,
        onConfirm: () => {
          // Delete from all paths
          remove(ref(db, `systems/${systemId}`));
          remove(ref(db, `configurations/${systemId}`));
          remove(ref(db, `control/${systemId}`));
          remove(ref(db, `runtime_state/${systemId}`));
          logAuditAction(
            currentUser?.email,
            "DELETE_SYSTEM",
            systemId,
            `Deleted entire system: ${systemMeta.hostname || systemId}`
          );

          dispatch("back"); // Go back to fleet view
        },
      });
    }
  }

  // Error Modal State
  let selectedErrorMessage = "";

  function showError(msg) {
    selectedErrorMessage = msg;
    // @ts-ignore
    document.getElementById("error_modal").showModal();
  }

  function handleDayInput(e) {
    let val = parseInt(e.target.value);
    if (isNaN(val)) return;
    if (val < 1) jobForm.schedule.day = 1;
    else if (val > 31) jobForm.schedule.day = 31;
    else jobForm.schedule.day = val;
  }

  // Job logs state
  let expandedJobId = null;
  // @ts-ignore
  $: systemLogs = $backupStore.logs[systemId] || {};

  function toggleExpand(jobId) {
    if (expandedJobId === jobId) {
      expandedJobId = null;
    } else {
      expandedJobId = jobId;
    }
  }

  /**
   * @typedef {Object} LogEntry
   * @property {string} job_id
   * @property {string} job_name
   * @property {number|string} timestamp
   * @property {string} [status]
   * @property {string} [type]
   * @property {string} [size]
   */

  /**
   * @param {string} jobId
   * @param {string} jobName
   * @returns {LogEntry[]}
   */
  function getJobLogs(jobId, jobName) {
    // @ts-ignore
    const logs = /** @type {LogEntry[]} */ (Object.values(systemLogs));

    return logs
      .filter((log) => log.job_id === jobId || log.job_name === jobName) // Support legacy logs by name
      .sort((a, b) => {
        // Sort newest first
        const dateA = new Date(a.timestamp);
        const dateB = new Date(b.timestamp);
        return dateB.getTime() - dateA.getTime();
      })
      .slice(0, 10); // Show last 10
  }
</script>

<div class="max-w-7xl mx-auto px-4">
  <!-- KPI Stats Grid -->
  <!-- KPI Stats Grid (Mobile: Horizontal Scroll, Desktop: Grid) -->
  <div
    class="flex overflow-x-auto snap-x snap-mandatory gap-4 mb-6 pb-4 md:grid md:grid-cols-3 md:gap-6 md:pb-0 md:overflow-visible no-scrollbar -mx-4 px-4 md:mx-0 md:px-0"
  >
    <!-- Stat 1 -->
    <div
      class="stats shadow bg-base-100 border border-base-200 min-w-[85vw] md:min-w-0 snap-center"
    >
      <div class="stat">
        <div class="stat-figure text-primary">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="inline-block w-8 h-8 stroke-current"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path></svg
          >
        </div>
        <div
          class="stat-title text-xs font-bold uppercase tracking-widest opacity-60"
        >
          Total Jobs
        </div>
        <div class="stat-value text-primary">{kpiTotalJobs}</div>
        <div class="stat-desc">Configured backup tasks</div>
      </div>
    </div>

    <!-- Stat 2 -->
    <div
      class="stats shadow bg-base-100 border border-base-200 min-w-[85vw] md:min-w-0 snap-center"
    >
      <div class="stat">
        <div class="stat-figure text-secondary">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="inline-block w-8 h-8 stroke-current"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path></svg
          >
        </div>
        <div
          class="stat-title text-xs font-bold uppercase tracking-widest opacity-60"
        >
          Last Activity
        </div>
        <div class="stat-value text-secondary text-2xl">
          {kpiLastActiveDisplay}
        </div>
        <div class="stat-desc">Most recent backup run</div>
      </div>
    </div>

    <!-- Stat 3 -->
    <div
      class="stats shadow bg-base-100 border border-base-200 min-w-[85vw] md:min-w-0 snap-center"
    >
      <div class="stat">
        <div class="stat-figure text-success">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="inline-block w-8 h-8 stroke-current"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            ></path></svg
          >
        </div>
        <div
          class="stat-title text-xs font-bold uppercase tracking-widest opacity-60"
        >
          Health Check
        </div>
        <div class="stat-value text-success">{kpiHealth}/{kpiTotalJobs}</div>
        <div class="stat-desc text-success font-bold">Passing Jobs</div>
      </div>
    </div>
  </div>

  <!-- Header System Info -->
  <div
    class="bg-base-100 border border-base-200 rounded-xl p-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center shadow-sm"
  >
    <div>
      <div class="flex items-center gap-3 mb-1">
        {#if isEditingNickname}
          <div class="join">
            <input
              class="input input-sm join-item input-bordered"
              bind:value={newNickname}
            />
            <button
              class="btn btn-sm btn-success join-item text-white"
              on:click={saveNickname}>Save</button
            >
            <button
              class="btn btn-sm btn-ghost join-item"
              on:click={() => (isEditingNickname = false)}>✕</button
            >
          </div>
        {:else}
          <h1
            class="text-3xl font-bold text-base-content flex items-center gap-3 {currentUser?.email?.toLowerCase() ===
            'admin@kriplanibuilders.com'
              ? 'cursor-pointer group'
              : ''}"
            on:click={() =>
              currentUser?.email?.toLowerCase() ===
                "admin@kriplanibuilders.com" && startEditNickname()}
            title={currentUser?.email?.toLowerCase() ===
            "admin@kriplanibuilders.com"
              ? "Click to rename"
              : ""}
          >
            {systemMeta.nickname || systemMeta.hostname || systemId}
            {#if currentUser?.email?.toLowerCase() === "admin@kriplanibuilders.com"}
              <span
                class="opacity-0 group-hover:opacity-100 text-sm text-base-content/40 font-normal"
                >✎</span
              >
            {/if}
          </h1>
        {/if}
        <div
          class="badge badge-outline text-xs font-mono uppercase tracking-widest bg-base-200 border-base-300"
        >
          {systemMeta.os}
        </div>
      </div>
      <div class="flex gap-4 text-xs text-base-content/50 font-mono">
        <span>ID: {systemId}</span>
        <span>•</span>
        <span>IP: {systemMeta.ip}</span>
      </div>
    </div>

    <div class="flex gap-2 mt-4 md:mt-0">
      <button
        class="btn btn-sm btn-ghost gap-2"
        on:click={() => backupStore.refresh()}
        title="Force Refresh Data"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-4 h-4"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
          />
        </svg>
        Refresh
      </button>

      <button
        class="btn btn-sm btn-primary gap-2 text-white shadow-md shadow-primary/20"
        on:click={() => openJobEditor(null)}
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          ></path></svg
        >
        New Job
      </button>

      {#if currentUser?.email
        ?.trim()
        .toLowerCase() === "admin@kriplanibuilders.com"}
        <button
          class="btn btn-sm btn-error gap-2 text-white"
          on:click={deleteSystem}
        >
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            ></path></svg
          >
          Delete System
        </button>
      {/if}
    </div>
  </div>

  <!-- Mobile Job Cards (App-like View) -->
  <div class="md:hidden space-y-4 mb-8">
    {#each Object.entries(jobs) as [jobId, job] (jobId)}
      {@const state = jobStates[jobId] || {}}
      <div class="card bg-base-100 shadow-sm border border-base-200">
        <div class="card-body p-4">
          <!-- Header: Name + Status -->
          <div class="flex justify-between items-start mb-2">
            <h3
              class="font-bold text-lg text-base-content flex items-center gap-2"
            >
              <div
                class="w-2.5 h-2.5 rounded-full {state.status === 'Running'
                  ? 'bg-indigo-500 animate-pulse'
                  : 'bg-transparent'}"
              ></div>
              {job.name}
            </h3>
            <span
              class="badge {state.status === 'Success'
                ? 'badge-success text-white'
                : state.status === 'Error'
                  ? 'badge-error text-white'
                  : 'badge-ghost'}"
            >
              {state.status || "Pending"}
            </span>
          </div>

          <!-- Schedule Badge -->
          <div class="mb-3">
            <span class="badge badge-sm badge-outline font-mono opacity-70">
              {job.schedule.type} @ {job.schedule.type === "monthly"
                ? `Day ${job.schedule.day}, `
                : ""}{job.schedule.time}
            </span>
          </div>

          <!-- Metdata Grid -->
          <div
            class="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-base-content/60 mb-4"
          >
            <div>Last Run:</div>
            <div class="font-mono text-base-content">
              {state.last_run || "Never"}
            </div>

            <div>Data Moved:</div>
            <div class="font-mono text-base-content">
              {state.last_size || "-"}
            </div>

            <div>Source:</div>
            <div class="font-mono truncate" title={job.source_path}>
              {job.source_path}
            </div>
          </div>

          <!-- Actions Footer -->
          <div class="flex gap-2 pt-3 border-t border-base-100">
            <button
              class="btn btn-sm btn-primary flex-1 text-white shadow-sm shadow-primary/30"
              on:click={() => triggerJob(jobId)}
              disabled={state.status === "Running"}
            >
              Build
            </button>

            <button
              class="btn btn-sm btn-ghost border border-base-200"
              on:click={() => openJobEditor(jobId)}
            >
              Edit
            </button>
            <button
              class="btn btn-sm btn-ghost border border-base-200"
              on:click={() => toggleExpand(jobId)}
            >
              Log
            </button>

            {#if currentUser?.email
              ?.trim()
              .toLowerCase() === "admin@kriplanibuilders.com"}
              <button
                class="btn btn-sm btn-ghost text-error"
                on:click={() => deleteJob(jobId)}
              >
                {@html Icons.trash}
              </button>
            {/if}
          </div>

          {#if expandedJobId === jobId}
            <div class="mt-4 pt-4 border-t border-base-200">
              <h4
                class="text-xs font-bold uppercase tracking-wider text-base-content/50 mb-2"
              >
                Logs History
              </h4>
              <div class="overflow-x-auto">
                <table class="table table-xs w-full">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Status</th>
                      <th>Data</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each getJobLogs(jobId, job.name) as log}
                      <tr>
                        <td class="font-mono">{log.timestamp}</td>
                        <td>
                          <span
                            class={log.status === "Success"
                              ? "text-success"
                              : "text-error"}>{log.status}</span
                          >
                          <span class="text-xs opacity-50 block"
                            >{log.type}</span
                          >
                        </td>
                        <td class="font-mono">{log.size || "-"}</td>
                      </tr>
                    {/each}
                    {#if getJobLogs(jobId, job.name).length === 0}
                      <tr
                        ><td colspan="3" class="text-center opacity-50 italic"
                          >No logs found</td
                        ></tr
                      >
                    {/if}
                  </tbody>
                </table>
              </div>
            </div>
          {/if}
        </div>
      </div>
    {/each}
  </div>

  <!-- Configuration Table (Desktop Only) -->
  <div
    class="hidden md:block bg-base-100 border border-base-200 rounded-xl shadow-sm overflow-hidden"
  >
    <div class="overflow-x-auto">
      <table class="table table-zebra table-lg font-sans">
        <!-- head -->
        <thead
          class="bg-base-200/50 text-base-content/60 uppercase text-xs font-bold tracking-wider"
        >
          <tr>
            <th>Job Name</th>
            <th>Schedule</th>
            <th>Source Path</th>
            <th>Destination ID</th>
            <th>Data Moved</th>
            <th>Last Run Status</th>
            <th class="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each Object.entries(jobs) as [jobId, job]}
            {@const state = jobStates[jobId] || {}}
            <!-- MAIN ROW -->
            <tr
              class="hover cursor-pointer"
              on:click={() => toggleExpand(jobId)}
            >
              <td class="font-medium text-base-content text-base">
                <div class="flex items-center gap-2">
                  <!-- Expansion Arrow -->
                  <svg
                    class="w-4 h-4 transition-transform {expandedJobId === jobId
                      ? 'rotate-90'
                      : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    /></svg
                  >

                  <div
                    class="w-2 h-2 rounded-full {state.status === 'Running'
                      ? 'bg-indigo-500 animate-pulse'
                      : 'bg-transparent'}"
                  ></div>
                  {job.name}
                </div>
              </td>
              <td>
                <span class="badge badge-sm badge-ghost font-mono"
                  >{job.schedule.type} @ {job.schedule.type === "monthly"
                    ? `Day ${job.schedule.day}, `
                    : ""}{job.schedule.time}</span
                >
              </td>
              <td
                class="text-xs font-mono text-base-content/60 max-w-[150px] truncate"
                title={job.source_path}>{job.source_path}</td
              >
              <td
                class="text-xs font-mono text-base-content/60 max-w-[100px] truncate"
                title={job.remote_folder}>{job.remote_folder || "Default"}</td
              >
              <td class="font-mono text-sm font-bold text-base-content/70">
                {state.last_size || "-"}
              </td>
              <td>
                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span
                      class="badge badge-xs {state.status === 'Success'
                        ? 'badge-success'
                        : state.status === 'Error'
                          ? 'badge-error'
                          : 'badge-ghost'}"
                    ></span>
                    <span
                      class="text-sm font-semibold {state.status === 'Success'
                        ? 'text-success'
                        : state.status === 'Error'
                          ? 'text-error cursor-help'
                          : 'text-base-content/40'}"
                      title={state.status === "Error"
                        ? state.detailed_message
                        : ""}
                    >
                      {state.status || "Pending"}
                    </span>
                    {#if state.status === "Error"}
                      <button
                        class="text-[10px] text-error mt-0.5 text-left hover:underline focus:outline-none"
                        on:click|stopPropagation={() =>
                          showError(state.detailed_message)}
                        title="Click to view full error log"
                      >
                        {state.detailed_message &&
                        state.detailed_message.length > 40
                          ? state.detailed_message.slice(0, 40) + "..."
                          : state.detailed_message}
                      </button>
                    {/if}
                  </div>
                  <span class="text-[10px] text-base-content/40 mt-1"
                    >{state.last_run || "Never"}</span
                  >
                </div>
              </td>
              <td class="text-right">
                <div class="join" on:click|stopPropagation>
                  <button
                    class="btn btn-sm btn-ghost join-item tooltip"
                    data-tip="Run Now"
                    on:click={() => triggerJob(jobId)}
                    disabled={state.status === "Running"}
                  >
                    {@html Icons.power}
                  </button>
                  <button
                    class="btn btn-sm btn-ghost join-item tooltip"
                    data-tip="Edit"
                    on:click={() => openJobEditor(jobId)}
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                      ></path></svg
                    >
                  </button>
                  {#if currentUser?.email
                    ?.trim()
                    .toLowerCase() === "admin@kriplanibuilders.com"}
                    <button
                      class="btn btn-sm btn-ghost join-item text-error tooltip"
                      data-tip="Delete"
                      on:click={() => deleteJob(jobId)}
                    >
                      <svg
                        class="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        ></path></svg
                      >
                    </button>
                  {/if}
                </div>
              </td>
            </tr>

            <!-- EXPANDED ROW (HISTORY) -->
            {#if expandedJobId === jobId}
              <tr class="bg-base-200/30">
                <td colspan="7" class="p-0">
                  <div class="p-6">
                    <h4
                      class="text-xs font-bold uppercase tracking-wider text-base-content/50 mb-3 flex items-center gap-2"
                    >
                      <svg
                        class="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        /></svg
                      >
                      Last 10 Runs History
                    </h4>
                    <table
                      class="table table-sm bg-base-100 rounded-lg shadow-sm border border-base-200"
                    >
                      <thead>
                        <tr class="bg-base-200/50">
                          <th>Timestamp</th>
                          <th>Trigger Type</th>
                          <th>Status</th>
                          <th>Data Moved</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each getJobLogs(jobId, job.name) as log}
                          <tr>
                            <td class="font-mono text-xs">{log.timestamp}</td>
                            <td>
                              <span
                                class="badge badge-sm badge-outline {log.type ===
                                'Scheduled'
                                  ? 'opacity-70'
                                  : 'badge-primary'}"
                              >
                                {log.type || "Manual"}
                              </span>
                            </td>
                            <td>
                              <span
                                class="font-bold {log.status === 'Success'
                                  ? 'text-success'
                                  : 'text-error'}"
                              >
                                {log.status}
                              </span>
                            </td>
                            <td class="font-mono text-xs font-bold"
                              >{log.size || "0 B"}</td
                            >
                          </tr>
                        {/each}
                        {#if getJobLogs(jobId, job.name).length === 0}
                          <tr>
                            <td
                              colspan="4"
                              class="text-center py-4 opacity-50 italic"
                              >No history available for this job yet.</td
                            >
                          </tr>
                        {/if}
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            {/if}
          {/each}

          {#if Object.keys(jobs).length === 0}
            <tr>
              <td
                colspan="7"
                class="text-center py-10 text-base-content/40 bg-base-200/20"
              >
                No jobs configured. Click "New Job" to start.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Error Display Modal -->

  <!-- ERROR MODAL -->
  <dialog id="error_modal" class="modal">
    <div class="modal-box border border-error/20">
      <h3 class="font-bold text-lg text-error flex items-center gap-2">
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          ></path></svg
        >
        Job Execution Failed
      </h3>
      <div class="py-4">
        <p class="text-sm opacity-70 mb-2">
          The agent reported the following error:
        </p>
        <div
          class="bg-base-200 p-4 rounded-lg font-mono text-xs break-all text-error"
        >
          {selectedErrorMessage}
        </div>
      </div>
      <div class="modal-action">
        <form method="dialog">
          <button class="btn">Close</button>
        </form>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>

  <!-- CONFIRMATION MODAL -->
  <dialog id="confirmation_modal" class="modal">
    <div class="modal-box bg-base-100">
      <h3
        class="font-bold text-lg {confirmState.isDanger
          ? 'text-error'
          : 'text-base-content'}"
      >
        {confirmState.title}
      </h3>
      <p class="py-4 whitespace-pre-line">{confirmState.message}</p>
      <div class="modal-action">
        <form method="dialog">
          <button class="btn btn-ghost">Cancel</button>
          <button
            class="btn {confirmState.isDanger
              ? 'btn-error'
              : 'btn-primary'} text-white ml-2"
            on:click|preventDefault={handleConfirm}
          >
            Confirm
          </button>
        </form>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>

  <!-- EDIT MODAL -->
  <dialog class="modal {isEditing ? 'modal-open' : ''}">
    <div class="modal-box w-11/12 max-w-3xl bg-base-100">
      <h3 class="font-bold text-xl mb-6 flex items-center gap-2">
        <div
          class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 6v6m0 0v6m0-6h6m-6 0H6"
            ></path></svg
          >
        </div>
        {editingJobId ? "Edit Configuration" : "New Backup Job"}
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Col 1 -->
        <div class="space-y-4">
          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Job Name</label
            >
            <input
              type="text"
              bind:value={jobForm.name}
              class="input input-bordered focus:input-primary"
              placeholder="e.g. Daily Tally Backup"
            />
          </div>

          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Local Source (Windows Path)</label
            >
            <div class="join">
              <input
                type="text"
                bind:value={jobForm.source_path}
                class="input input-bordered join-item w-full font-mono text-sm"
                placeholder="D:\Data or \\Server\Share"
              />
              <button
                class="btn btn-square join-item cursor-default bg-base-200 text-xs text-base-content/50"
                >📂</button
              >
            </div>
          </div>

          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Retention Policy</label
            >
            <div class="flex items-center gap-2">
              <span class="text-sm">Keep snapshots for</span>
              <input
                type="number"
                bind:value={jobForm.retention.days}
                class="input input-bordered w-20 text-center font-bold"
              />
              <span class="text-sm">days</span>
            </div>
          </div>
        </div>

        <!-- Col 2 -->
        <div class="space-y-4">
          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Frequency</label
            >
            <div class="flex gap-2">
              <select
                bind:value={jobForm.schedule.type}
                class="select select-bordered w-full flex-1"
              >
                <option value="daily">Daily</option>
                <option value="monthly">Monthly</option>
              </select>

              {#if jobForm.schedule.type === "monthly"}
                <div class="flex items-center gap-1 w-24 relative">
                  <span class="text-xs">Day</span>
                  <input
                    type="number"
                    min="1"
                    max="31"
                    bind:value={jobForm.schedule.day}
                    on:input={handleDayInput}
                    class="input input-bordered w-full text-center px-1"
                    placeholder="1"
                  />
                </div>
              {/if}
            </div>

            {#if jobForm.schedule.type === "monthly" && jobForm.schedule.day > 28}
              <div
                role="alert"
                class="alert alert-warning py-1 mt-2 text-xs flex"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="stroke-current shrink-0 h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  /></svg
                >
                <span
                  >Warning: Day {jobForm.schedule.day} may not exist in some months.
                  Job will be skipped.</span
                >
              </div>
            {/if}
          </div>

          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Run Time (24h)</label
            >
            <input
              type="time"
              bind:value={jobForm.schedule.time}
              class="input input-bordered"
            />
          </div>

          <div class="form-control">
            <label
              class="label font-bold text-xs uppercase text-base-content/50"
              >Cloud Destination (Subfolder)</label
            >
            <input
              type="text"
              bind:value={jobForm.remote_folder}
              class="input input-bordered"
              placeholder="Default: Backups"
            />
          </div>
        </div>
      </div>

      <div class="modal-action mt-8 pt-4 border-t border-base-200">
        <button class="btn btn-ghost" on:click={() => (isEditing = false)}
          >Cancel</button
        >
        <button class="btn btn-primary px-8 text-white" on:click={saveJob}
          >Save Configuration</button
        >
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button on:click={() => (isEditing = false)}>close</button>
    </form>
  </dialog>
</div>
