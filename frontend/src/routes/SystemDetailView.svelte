<script>
  import { backupStore, logAuditAction } from "../stores/backupStore";
  import { auth } from "../lib/firebase";
  import { createEventDispatcher } from "svelte";
  import { Icons } from "../components/Icons";
  import { db, ref, update } from "../lib/firebase";

  export let systemId;

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
      auth.currentUser?.email,
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
      auth.currentUser?.email,
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
        auth.currentUser?.email,
        "TRIGGER_JOB",
        systemId,
        `Manually triggered job "${jobs[jobId].name}"`
      );
    }
  }

  function deleteJob(jobId) {
    if (confirm("Delete this job configuration?")) {
      const jobName = jobs[jobId]?.name || jobId;
      update(ref(db, `configurations/${systemId}/${jobId}`), null);
      logAuditAction(
        auth.currentUser?.email,
        "DELETE_JOB",
        systemId,
        `Deleted job "${jobName}" (${jobId})`
      );
    }
  }
</script>

<div class="max-w-7xl mx-auto">
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
            class="text-3xl font-bold text-base-content flex items-center gap-3 cursor-pointer group"
            on:click={startEditNickname}
            title="Click to rename"
          >
            {systemMeta.nickname || systemMeta.hostname || systemId}
            <span
              class="opacity-0 group-hover:opacity-100 text-sm text-base-content/40 font-normal"
              >✎</span
            >
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
            <th>Last Run Status</th>
            <th class="text-right">Actions</th>
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
                class="text-xs font-mono text-base-content/60 max-w-[200px] truncate"
                title={job.source_path}>{job.source_path}</td
              >
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
                          ? 'text-error'
                          : 'text-base-content/40'}"
                    >
                      {state.status || "Pending"}
                    </span>
                  </div>
                  <span class="text-[10px] text-base-content/40 mt-1"
                    >{state.last_run || "Never"}</span
                  >
                </div>
              </td>
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
            </tr>
          {/each}

          {#if Object.keys(jobs).length === 0}
            <tr>
              <td
                colspan="5"
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
                placeholder="D:\Data"
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
