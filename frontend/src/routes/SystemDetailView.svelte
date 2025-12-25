<script>
  import { backupStore, logAuditAction } from "../stores/backupStore";
  import { auth } from "../lib/firebase";
  import { createEventDispatcher } from "svelte";
  import { Icons } from "../components/Icons";
  import { db, ref, update } from "../lib/firebase";

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

  function triggerJob(jobId) {
    if (confirm(`Run ${jobs[jobId].name} now?`)) {
      update(ref(db, `control/${systemId}`), { trigger_now: jobId });
      logAuditAction(
        currentUser?.email,
        "TRIGGER_JOB",
        systemId,
        `Manually triggered job "${jobs[jobId].name}"`
      );
    }
  }

  // Calculate KPIs
  $: kpiTotalJobs = Object.keys(jobs).length;
  $: kpiLastActive = Object.values(jobStates).reduce((latest, state) => {
    if (!state.last_run) return latest;
    // Simple string compare works for ISO-like dates, but let's be safe if format varies
    return state.last_run > latest ? state.last_run : latest;
  }, "Never");
  $: kpiHealth = Object.values(jobStates).filter(
    (s) => s.status === "Success"
  ).length;

  function deleteJob(jobId) {
    if (confirm("Delete this job configuration?")) {
      const jobName = jobs[jobId]?.name || jobId;
      update(ref(db, `configurations/${systemId}/${jobId}`), null);
      logAuditAction(
        currentUser?.email,
        "DELETE_JOB",
        systemId,
        `Deleted job "${jobName}" (${jobId})`
      );
    }
  }

  function deleteSystem() {
    if (
      currentUser?.email?.toLowerCase() === "admin@kriplanibuilders.com" &&
      confirm(
        "DANGER: Are you sure you want to PERMANENTLY delete this system?\n\nThis will remove all configurations, logs, and metadata for this machine from the dashboard.\n\nThe Agent on the machine will need to be re-run to re-register."
      )
    ) {
      // ...
      logAuditAction(
        currentUser?.email,
        "DELETE_SYSTEM",
        systemId,
        `Deleted entire system: ${systemMeta.hostname || systemId}`
      );

      dispatch("back"); // Go back to fleet view
    }
  }
</script>

<div class="max-w-7xl mx-auto">
  <!-- KPI Stats Grid -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
    <!-- Stat 1 -->
    <div class="stats shadow bg-base-100 border border-base-200">
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
    <div class="stats shadow bg-base-100 border border-base-200">
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
        <div class="stat-value text-secondary text-2xl">{kpiLastActive}</div>
        <div class="stat-desc">Most recent backup run</div>
      </div>
    </div>

    <!-- Stat 3 -->
    <div class="stats shadow bg-base-100 border border-base-200">
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
      {/if}
    </div>
  </div>

  <!-- Configuration Table -->
  <div
    class="bg-base-100 border border-base-200 rounded-xl shadow-sm overflow-hidden"
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
            {#if currentUser?.email?.toLowerCase() === "admin@kriplanibuilders.com"}
              <th class="text-right">Actions</th>
            {/if}
          </tr>
        </thead>
        <tbody>
          {#each Object.entries(jobs) as [jobId, job]}
            {@const state = jobStates[jobId] || {}}
            <tr class="hover">
              <td class="font-medium text-base-content text-base">
                <div class="flex items-center gap-2">
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
                  >{job.schedule.type} @ {job.schedule.time}</span
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
                      <div
                        class="text-[10px] text-error mt-0.5 max-w-[150px] truncate"
                        title={state.detailed_message}
                      >
                        {state.detailed_message}
                      </div>
                    {/if}
                  </div>
                  <span class="text-[10px] text-base-content/40 mt-1"
                    >{state.last_run || "Never"}</span
                  >
                </div>
              </td>
              {#if currentUser?.email
                ?.trim()
                .toLowerCase() === "admin@kriplanibuilders.com"}
                <td class="text-right">
                  <div class="join">
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
                  </div>
                </td>
              {/if}
            </tr>
          {/each}

          {#if Object.keys(jobs).length === 0}
            <tr>
              <td
                colspan="6"
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
            <select
              bind:value={jobForm.schedule.type}
              class="select select-bordered w-full"
            >
              <option value="daily">Daily</option>
              <option value="monthly">Monthly</option>
            </select>
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
