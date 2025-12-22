<script>
  import { onMount, onDestroy } from 'svelte';
  import { db, ref, onValue, update } from './lib/firebase';

  // --- STATE ---
  let clientName = "Kriplani Builders";
  let isAgentOnline = false;
  let isDarkMode = true; // Default to Dark for "Enterprise" feel
  let now = Date.now();
  let interval;

  // Data Models
  let state = { status: "Loading...", detailed_message: "Connecting...", agent_heartbeat_epoch: 0 };
  let config = {
    schedule_time: "21:00",
    source_path: "",
    remote_folder: "",
    shutdown_after_backup: false,
    email_recipients: "",
    retention_policy: { keep_daily_days: 60 } // Removed Hourly
  };
  let stats = {
    last_run_date: "Never",
    last_duration_str: "--",
    last_data_transferred_str: "0 MB"
  };
  let history = {};
  let control = { trigger_now: false };

  let showToast = false;
  let backupTriggered = false;

  // --- ICONS ---
  const Icons = {
    check: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
    clock: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
    power: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>`,
    shield: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>`,
    settings: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>`,
    sun: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>`,
    moon: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>`,
    database: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>`
  };

  onMount(() => {
    toggleTheme(true); // Force Dark Mode initially
    const rootRef = ref(db, '/');
    onValue(rootRef, (snapshot) => {
      const data = snapshot.val();
      if (data) {
        if (data.config) config = { ...config, ...data.config };
        if (!config.retention_policy) config.retention_policy = { keep_daily_days: 60 };
        if (data.state) state = { ...state, ...data.state };
        if (data.stats) stats = { ...stats, ...data.stats };
        if (data.control) control = { ...control, ...data.control };
        if (data.history) history = data.history;
        if (control.trigger_now === false) backupTriggered = false;
      }
    });

    interval = setInterval(() => {
      now = Date.now();
      const lastBeat = state.agent_heartbeat_epoch * 1000;
      isAgentOnline = (now - lastBeat) < 120000;
    }, 5000);
  });

  onDestroy(() => clearInterval(interval));

  function toggleTheme(forceDark = null) {
    if (forceDark !== null) isDarkMode = forceDark;
    else isDarkMode = !isDarkMode;
    if (isDarkMode) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }

  function triggerBackup() {
    if (confirm(`⚠️ Start Manual Backup?`)) {
      backupTriggered = true;
      update(ref(db, 'control'), { trigger_now: true });
      update(ref(db, 'state'), { status: "Command Sent...", detailed_message: "Waiting for agent..." });
    }
  }

  function saveSettings() {
    update(ref(db, 'config'), config);
    showToast = true;
    setTimeout(() => showToast = false, 3000);
  }

  // --- KPI LOGIC ---
  $: historyList = Object.values(history || {}).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 7);

  // Helper: Parse "150 MB" or "2.1 GB" to raw MB for charting
  function parseSizeToMB(sizeStr) {
    if (!sizeStr) return 0;
    const num = parseFloat(sizeStr.split(' ')[0]);
    if (sizeStr.includes('GB')) return num * 1024;
    if (sizeStr.includes('KB')) return num / 1024;
    return num; // MB
  }

  // Chart Data
  $: sizeData = historyList.slice().reverse().map(h => parseSizeToMB(h.size || "0 MB"));
  $: maxSize = Math.max(...sizeData, 10);
</script>

<!--
  THEME: Deep Navy / Cyber
  Bg: #0F172A (Slate 900) -> #1E293B (Slate 800)
  Accents: Cyan/Teal for "Tech" feel
-->
<main class="h-screen w-screen bg-slate-50 dark:bg-[#0F172A] text-slate-600 dark:text-slate-300 font-sans p-6 overflow-hidden flex flex-col transition-colors duration-500">

  <!-- HEADER -->
  <header class="flex justify-between items-center mb-6 px-2">
    <div class="flex items-center gap-4">
      <div class="p-3 bg-white dark:bg-slate-800 rounded-2xl shadow-sm text-indigo-600 dark:text-cyan-400 border border-slate-200 dark:border-slate-700">
        {@html Icons.shield}
      </div>
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100 tracking-tight leading-none">{clientName}</h1>
        <p class="text-xs font-bold text-indigo-400 dark:text-cyan-500/70 uppercase tracking-widest mt-1">Enterprise Backup Controller</p>
      </div>
    </div>

    <div class="flex items-center gap-4">
      <button class="p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors text-slate-500 dark:text-slate-400" on:click={() => toggleTheme()}>
        {@html isDarkMode ? Icons.sun : Icons.moon}
      </button>

      <div class="flex items-center gap-3 bg-white dark:bg-slate-800 px-4 py-2 rounded-full shadow-sm border border-slate-200 dark:border-slate-700">
        <span class="text-xs font-bold text-slate-400 dark:text-slate-500">AGENT STATUS</span>
        <div class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold
            {isAgentOnline ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}">
            <span class="relative flex h-2 w-2">
              {#if isAgentOnline}
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              {/if}
              <span class="relative inline-flex rounded-full h-2 w-2 {isAgentOnline ? 'bg-emerald-500' : 'bg-slate-400'}"></span>
            </span>
          {isAgentOnline ? 'ONLINE' : 'OFFLINE'}
        </div>
      </div>
    </div>
  </header>

  <!-- GRID LAYOUT -->
  <div class="flex-1 grid grid-cols-12 gap-6 min-h-0">

    <!-- LEFT COLUMN: BI & ANALYTICS -->
    <div class="col-span-4 flex flex-col gap-6 h-full overflow-hidden">

      <!-- 1. STATUS CARD -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col justify-between relative overflow-hidden group">
        <div class="absolute top-0 right-0 p-6 opacity-10 dark:opacity-20 group-hover:scale-110 transition-transform duration-500">
          <div class="w-32 h-32 rounded-full {state.status === 'Idle' ? 'bg-emerald-400' : 'bg-amber-400'} blur-3xl"></div>
        </div>
        <div class="relative z-10">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Current Status</p>
              <h2 class="text-4xl font-bold tracking-tight {state.status === 'Idle' ? 'text-slate-800 dark:text-white' : 'text-amber-500'}">
                {state.status}
              </h2>
            </div>
            <div class="p-3 rounded-2xl {state.status === 'Idle' ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-500' : 'bg-amber-50 dark:bg-amber-500/10 text-amber-500'}">
              {@html state.status === 'Idle' ? Icons.check : Icons.power}
            </div>
          </div>
          <p class="mt-4 text-sm font-medium {state.status === 'Idle' ? 'text-slate-500 dark:text-slate-400' : 'text-amber-500'}">
            {state.detailed_message}
          </p>
        </div>
      </div>

      <!-- 2. BUSINESS KPI: DATA DELTA (Size Chart) -->
      <div class="bg-white dark:bg-slate-800 p-5 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col h-40">
        <div class="flex justify-between items-center mb-4">
          <div class="flex items-center gap-2 text-indigo-500 dark:text-cyan-400">
            {@html Icons.database}
            <span class="text-[10px] font-bold uppercase text-slate-400">Daily Data Transfer</span>
          </div>
          <span class="text-xs font-bold text-slate-700 dark:text-white">{stats.last_data_transferred_str}</span>
        </div>

        <!-- SVG BAR CHART -->
        <div class="flex-1 flex items-end justify-between gap-2">
          {#each sizeData as val, i}
            <div class="w-full bg-slate-100 dark:bg-slate-700/50 rounded-t-sm relative group h-full flex items-end">
              <div class="w-full bg-gradient-to-t from-indigo-500 to-cyan-400 dark:from-cyan-600 dark:to-cyan-400 rounded-t-sm transition-all duration-500 relative"
                   style="height: {(val / maxSize) * 100}%">
                <!-- Tooltip -->
                <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                  {historyList.slice().reverse()[i].size}
                </div>
              </div>
            </div>
          {/each}
          {#if sizeData.length === 0}
            <div class="w-full text-center text-[10px] text-slate-400 self-center">No Data Yet</div>
          {/if}
        </div>
      </div>

      <!-- 3. ACTIVITY LOG -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 flex-1 flex flex-col overflow-hidden">
        <div class="px-6 py-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Recent Activity</h3>
        </div>
        <div class="overflow-y-auto p-2">
          <table class="table w-full text-xs">
            <tbody>
            {#each historyList as item}
              <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                <td class="font-medium text-slate-600 dark:text-slate-300 py-3">{item.timestamp}</td>
                <td class="text-right py-3">{item.size || '-'}</td>
                <td class="text-right py-3">
                  <span class="px-2 py-1 rounded-md font-bold {item.status === 'Success' ? 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-50 dark:bg-red-500/20 text-red-600 dark:text-red-400'}">
                    {item.status}
                  </span>
                </td>
              </tr>
            {/each}
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- RIGHT COLUMN: CONTROL PLANE -->
    <div class="col-span-8 bg-white dark:bg-slate-800 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-8 flex flex-col h-full overflow-y-auto">

      <div class="flex items-center gap-2 mb-6 text-slate-700 dark:text-slate-200">
        <div class="text-indigo-500 dark:text-cyan-400">{@html Icons.settings}</div>
        <h3 class="text-lg font-bold">Configuration & Control</h3>
      </div>

      <div class="space-y-6 flex-1">

        <!-- Row 1: Paths -->
        <div class="grid grid-cols-2 gap-6">
          <div class="form-control">
            <label class="label text-xs font-bold text-slate-400 uppercase mb-1">Local Source Path</label>
            <input type="text" bind:value={config.source_path} class="input input-bordered border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50 focus:bg-white dark:focus:bg-slate-900 transition-all rounded-xl text-sm dark:text-white" placeholder="D:\Data" />
          </div>
          <div class="form-control">
            <label class="label text-xs font-bold text-slate-400 uppercase mb-1">Google Drive Folder</label>
            <input type="text" bind:value={config.remote_folder} class="input input-bordered border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50 focus:bg-white dark:focus:bg-slate-900 transition-all rounded-xl text-sm dark:text-white" placeholder="Backups" />
          </div>
        </div>

        <!-- Row 2: Schedule & Email -->
        <div class="grid grid-cols-2 gap-6">
          <div class="form-control">
            <label class="label text-xs font-bold text-slate-400 uppercase mb-1">Daily Schedule</label>
            <input type="time" bind:value={config.schedule_time} class="input input-bordered border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50 focus:bg-white dark:focus:bg-slate-900 transition-all rounded-xl text-sm dark:text-white" />
          </div>
          <div class="form-control">
            <label class="label text-xs font-bold text-slate-400 uppercase mb-1">Alert Emails</label>
            <input type="text" bind:value={config.email_recipients} class="input input-bordered border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900/50 focus:bg-white dark:focus:bg-slate-900 transition-all rounded-xl text-sm dark:text-white" placeholder="admin@domain.com" />
          </div>
        </div>

        <div class="divider opacity-50 dark:opacity-20"></div>

        <!-- Row 3: Retention Policy (Daily Only) -->
        <div class="bg-indigo-50 dark:bg-slate-700/30 rounded-2xl p-6 border border-indigo-100 dark:border-slate-600">
          <div class="flex items-center gap-2 mb-4">
            <span class="text-indigo-500 dark:text-cyan-400">{@html Icons.folder}</span>
            <span class="text-xs font-bold text-indigo-800 dark:text-cyan-100 uppercase">Retention Policy</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="form-control">
              <label class="label text-xs font-bold text-indigo-400 dark:text-slate-400 uppercase mb-1">Keep Daily Backups (Days)</label>
              <input type="number" bind:value={config.retention_policy.keep_daily_days} class="input input-bordered border-indigo-200 dark:border-slate-500 focus:border-indigo-400 bg-white dark:bg-slate-900/80 rounded-xl text-sm dark:text-white" />
              <label class="label">
                <span class="label-text-alt text-slate-400">Hourly backups are disabled per policy.</span>
              </label>
            </div>
          </div>
        </div>

      </div>

      <!-- BOTTOM ACTION BAR -->
      <div class="mt-8 pt-6 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">

        <div class="flex items-center gap-6">
          <label class="label cursor-pointer gap-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 p-2 rounded-lg transition-colors">
            <input type="checkbox" bind:checked={config.shutdown_after_backup} class="checkbox checkbox-primary checkbox-sm rounded" />
            <span class="label-text font-bold text-slate-500 dark:text-slate-400 text-sm">Shutdown after backup</span>
          </label>

          <!-- Manual Trigger -->
          <button class="btn btn-ghost btn-sm text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 normal-case font-medium"
                  on:click={triggerBackup}
                  disabled={backupTriggered || state.status !== 'Idle'}>
            {backupTriggered ? 'Requesting...' : 'Run Manual Backup'}
          </button>
        </div>

        <!-- Primary Save -->
        <button class="btn btn-primary px-8 rounded-xl shadow-lg shadow-indigo-200/50 dark:shadow-none text-white border-none bg-indigo-600 hover:bg-indigo-700 dark:bg-cyan-600 dark:hover:bg-cyan-700 hover:scale-105 transition-all"
                on:click={saveSettings}>
          Save Configuration
        </button>
      </div>

    </div>

  </div>

  <!-- TOAST -->
  {#if showToast}
    <div class="toast toast-top toast-center z-50">
      <div class="alert bg-emerald-500 dark:bg-emerald-600 text-white shadow-xl rounded-2xl border-none font-bold">
        <span>Configuration Saved Successfully!</span>
      </div>
    </div>
  {/if}

</main>