<script>
  import { fleetData } from "../stores/backupStore";
  import { createEventDispatcher } from "svelte";
  import { Icons } from "../components/Icons";

  const dispatch = createEventDispatcher();

  let searchQuery = "";

  $: filteredFleet = $fleetData.filter(
    (sys) =>
      sys.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sys.id.toLowerCase().includes(searchQuery.toLowerCase())
  );
</script>

<div>
  <!-- Action Toolbar -->
  <div
    class="flex flex-col md:flex-row justify-between items-center mb-8 gap-4"
  >
    <div>
      <h2 class="text-2xl font-bold text-base-content tracking-tight">
        System Fleet
      </h2>
      <p class="text-base-content/60 text-sm mt-1">
        Monitor {filteredFleet.length} active agents
      </p>
    </div>

    <div class="flex gap-3 w-full md:w-auto">
      <div class="relative w-full md:w-64">
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Search systems..."
          class="input input-sm input-bordered w-full pl-9 focus:input-primary"
        />
        <svg
          class="w-4 h-4 absolute left-3 top-2.5 text-base-content/40"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          ></path></svg
        >
      </div>

      <a
        href="/downloads/KriplaniBackupAgent_Installer.exe"
        download
        class="btn btn-sm btn-primary gap-2 shadow-lg shadow-primary/30 text-white"
      >
        {@html Icons.download} Windows Agent
      </a>
    </div>
  </div>

  <!-- Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
    <!-- New System Card (Placeholder) -->
    <div
      class="border border-dashed border-base-300 rounded-xl flex items-center justify-center p-8 bg-base-100/50 hover:bg-base-100 transition-all hover:border-primary/50 group cursor-pointer h-[180px]"
    >
      <div
        class="text-center opacity-60 group-hover:opacity-100 transition-opacity"
      >
        <div
          class="mx-auto w-10 h-10 rounded-full bg-base-200 flex items-center justify-center mb-2 group-hover:bg-primary/10 group-hover:text-primary transition-colors"
        >
          <span class="text-xl">+</span>
        </div>
        <h4 class="font-semibold text-sm">Register New Node</h4>
        <p class="text-xs mt-1 max-w-[150px] mx-auto">
          Run the Agent executable on a machine to auto-join.
        </p>
      </div>
    </div>

    <!-- System Cards -->
    {#each filteredFleet as system (system.id)}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <div
        class="card bg-base-100 shadow-sm border border-base-200 hover:shadow-md hover:border-primary/40 transition-all duration-200 cursor-pointer group"
        on:click={() => dispatch("select", system.id)}
      >
        <div class="card-body p-5">
          <!-- Header -->
          <div class="flex justify-between items-start mb-4">
            <div class="flex gap-3 items-center">
              <div
                class="w-10 h-10 rounded-lg bg-base-200 flex items-center justify-center text-base-content/70"
              >
                {@html Icons.server}
              </div>
              <div>
                <h3
                  class="font-bold text-base text-base-content group-hover:text-primary transition-colors truncate max-w-[150px]"
                  title={system.name}
                >
                  {system.name}
                </h3>
                <div
                  class="text-[10px] font-mono text-base-content/40 tracking-wide uppercase"
                >
                  {system.os}
                </div>
              </div>
            </div>
            <div
              class="badge badge-sm font-semibold {system.status === 'Online'
                ? 'badge-success text-white'
                : 'badge-ghost text-base-content/40'}"
            >
              {system.status}
            </div>
          </div>

          <!-- Metrics -->
          <div class="grid grid-cols-2 gap-2 mt-auto">
            <div class="bg-base-200/50 rounded-lg p-2">
              <div
                class="text-[10px] uppercase text-base-content/40 font-bold tracking-wider"
              >
                Jobs
              </div>
              <div class="text-lg font-semibold text-base-content">
                {system.jobCount}
              </div>
            </div>
            <div class="bg-base-200/50 rounded-lg p-2">
              <div
                class="text-[10px] uppercase text-base-content/40 font-bold tracking-wider"
              >
                Health
              </div>
              <div
                class="text-lg font-semibold {system.status === 'Online'
                  ? 'text-success'
                  : 'text-base-content/30'}"
              >
                {system.status === "Online" ? "100%" : "--"}
              </div>
            </div>
          </div>

          <!-- Footer ID -->
          <div
            class="mt-4 pt-3 border-t border-base-200 flex justify-between items-center"
          >
            <code class="text-[10px] text-base-content/30"
              >{system.id.slice(0, 8)}...</code
            >
            <span
              class="text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity"
              >Manage &rarr;</span
            >
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
