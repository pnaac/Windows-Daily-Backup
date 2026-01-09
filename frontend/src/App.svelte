<script>
  import { onMount, tick } from "svelte";
  import {
    auth,
    provider,
    signInWithPopup,
    signOut,
    onAuthStateChanged,
  } from "./lib/firebase";
  import { backupStore } from "./stores/backupStore";
  import FleetView from "./routes/FleetView.svelte";
  import SystemDetailView from "./routes/SystemDetailView.svelte";
  import AuditLogsView from "./routes/AuditLogsView.svelte";
  import { Icons } from "./components/Icons";

  // State
  let user = null;
  let loadingAuth = true;
  let currentView = "fleet"; // 'fleet' or 'system'
  let selectedSystemId = null;

  // UI State
  let isSidebarCollapsed = localStorage.getItem("sidebar_collapsed") === "true";

  // Theme State: 'system' | 'kriplani_light' | 'kriplani_dark'
  let themePreference = localStorage.getItem("theme_preference") || "system";
  let activeTheme = "kriplani_light"; // The actual applied theme (resolved from system)

  function resolveSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "kriplani_dark"
      : "kriplani_light";
  }

  function applyTheme() {
    if (themePreference === "system") {
      activeTheme = resolveSystemTheme();
    } else {
      activeTheme = themePreference;
    }
    document.documentElement.setAttribute("data-theme", activeTheme);
  }

  // Auth & Theme Listener
  onMount(() => {
    applyTheme();

    // Listen for System Theme Changes
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (themePreference === "system") applyTheme();
    };
    mediaQuery.addEventListener("change", handleChange);

    const unsubscribe = onAuthStateChanged(auth, (u) => {
      user = u;
      loadingAuth = false;
      if (user) {
        backupStore.init(user.uid);
      }
    });
    return () => {
      unsubscribe();
      mediaQuery.removeEventListener("change", handleChange);
    };
  });

  // Actions
  async function login() {
    try {
      await signInWithPopup(auth, provider);
    } catch (e) {
      alert("Login Failed: " + e.message);
    }
  }

  function logout() {
    backupStore.destroy();
    signOut(auth);
    user = null;
  }

  function toggleTheme() {
    // Cycle: System -> Light -> Dark -> System
    if (themePreference === "system") themePreference = "kriplani_light";
    else if (themePreference === "kriplani_light")
      themePreference = "kriplani_dark";
    else themePreference = "system";

    localStorage.setItem("theme_preference", themePreference);
    applyTheme();
  }

  function toggleSidebar() {
    isSidebarCollapsed = !isSidebarCollapsed;
    localStorage.setItem("sidebar_collapsed", String(isSidebarCollapsed));
  }

  // Routing
  function handleSelectSystem(event) {
    selectedSystemId = event.detail;
    currentView = "system";
  }

  function goBack() {
    currentView = "fleet";
    selectedSystemId = null;
  }
</script>

{#if loadingAuth}
  <!-- Loading State -->
  <div class="min-h-screen flex items-center justify-center bg-base-200">
    <span class="loading loading-ring loading-lg text-primary"></span>
  </div>
{:else if !user}
  <!-- Enterprise Login Screen (Floating Card Design) -->
  <div
    class="min-h-screen flex items-center justify-center bg-slate-100 p-4 lg:p-12 font-sans"
  >
    <!-- Floating Card Container -->
    <div
      class="w-full max-w-6xl bg-white rounded-2xl lg:rounded-[2rem] shadow-2xl overflow-hidden flex flex-col lg:flex-row min-h-0 lg:min-h-[700px]"
    >
      <!-- Left Side: Branding (Dark Aesthetic) -->
      <div
        class="lg:w-5/12 bg-slate-900 relative p-8 lg:p-12 flex flex-col justify-between overflow-hidden min-h-[300px] lg:min-h-auto"
      >
        <!-- Background Pattern -->
        <div class="absolute inset-0 opacity-20">
          <svg
            class="w-full h-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            <path d="M0 0 L100 0 L100 100 Z" fill="url(#grad2)" />
            <defs>
              <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#7c3aed;stop-opacity:1" />
                <stop
                  offset="100%"
                  style="stop-color:#2dd4bf;stop-opacity:0.5"
                />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <!-- Floating Orbs -->
        <div
          class="absolute top-20 right-10 w-20 h-20 lg:w-32 lg:h-32 bg-primary blur-[60px] lg:blur-[80px] rounded-full opacity-40"
        ></div>
        <div
          class="absolute bottom-20 left-10 w-24 h-24 lg:w-40 lg:h-40 bg-secondary blur-[60px] lg:blur-[80px] rounded-full opacity-30"
        ></div>

        <!-- Brand Content -->
        <div class="relative z-10 mt-6 lg:mt-10">
          <div
            class="w-12 h-1 lg:w-16 bg-secondary rounded-full mb-4 lg:mb-6"
          ></div>
          <h1
            class="text-3xl lg:text-5xl font-bold text-white leading-tight mb-4 lg:mb-6"
          >
            Kriplani<br />Backup System.
          </h1>
          <p class="text-slate-400 text-sm lg:text-lg">
            Next-Gen Enterprise Infrastructure
          </p>
        </div>

        <div class="relative z-10">
          <!-- Version text removed -->
        </div>
      </div>

      <!-- Right Side: Login Form (Clean with Graphics) -->
      <div
        class="lg:w-7/12 bg-white relative p-8 lg:p-24 flex flex-col justify-center py-12 lg:py-0"
      >
        <!-- Decorative Corner Graphic -->
        <svg
          class="absolute top-0 right-0 w-64 h-64 text-slate-50 transform pointer-events-none"
          viewBox="0 0 100 100"
        >
          <circle cx="100" cy="0" r="50" fill="currentColor" />
          <circle cx="80" cy="20" r="10" fill="#e2e8f0" />
        </svg>

        <div class="w-full max-w-md mx-auto relative z-10">
          <div class="mb-12">
            <div
              class="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 text-primary mb-6"
            >
              {@html Icons.shield}
            </div>
            <h2 class="text-4xl font-extrabold text-slate-900 mb-2">
              Get Started.
            </h2>
            <p class="text-slate-500 text-lg">
              Authenticate to access the dashboard.
            </p>
          </div>

          <div class="space-y-6">
            <button
              class="btn btn-block h-16 text-lg font-bold text-white border-0 bg-[#1e293b] hover:bg-slate-800 shadow-xl shadow-[#1e293b]/20 rounded-xl flex items-center justify-center gap-3 transition-transform hover:scale-[1.01] active:scale-[0.99]"
              on:click={login}
            >
              <svg class="w-6 h-6" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"
                />
              </svg>
              <span>Sign in with Google</span>
            </button>
          </div>
        </div>

        <!-- Footer (Relative on Mobile, Absolute on Desktop) -->
        <a
          href="https://pnaac.com"
          target="_blank"
          class="mt-12 w-full text-center lg:mt-0 lg:w-auto lg:absolute lg:bottom-6 lg:right-8 lg:text-right opacity-40 hover:opacity-100 transition-opacity duration-300 group z-10"
        >
          <p
            class="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase mb-0.5 group-hover:text-primary transition-colors"
          >
            Created By
          </p>
          <div class="flex items-center justify-center lg:justify-end gap-1.5">
            <span class="text-xs font-black text-slate-800 tracking-wide">
              PNAAC IT LABS
            </span>
            <!-- User asked to simplify, removing PVT LTD chip to clean up -->
          </div>
        </a>
      </div>
    </div>
  </div>
{:else}
  <!-- App Shell (Custom Flex Layout) -->
  <div class="flex h-screen overflow-hidden bg-base-200 font-sans">
    <!-- Desktop Sidebar (Hidden on Mobile) -->
    <aside
      class="hidden lg:flex flex-col bg-base-100 border-r border-base-300 transition-all duration-300
      {isSidebarCollapsed ? 'w-20' : 'w-72'}"
    >
      <!-- Sidebar Header -->
      <div
        class="h-16 flex items-center justify-between px-4 border-b border-base-300/50"
      >
        {#if !isSidebarCollapsed}
          <div
            class="flex items-center gap-3 overflow-hidden whitespace-nowrap"
          >
            <div
              class="w-8 h-8 rounded-lg bg-primary flex-shrink-0 flex items-center justify-center text-white shadow-lg shadow-primary/40"
            >
              {@html Icons.shield}
            </div>
            <div>
              <div class="font-bold text-lg leading-tight">
                Backup<span class="text-primary">Control</span>
              </div>
            </div>
          </div>
        {:else}
          <div class="w-full flex justify-center">
            <div
              class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shadow-lg shadow-primary/40"
            >
              {@html Icons.shield}
            </div>
          </div>
        {/if}

        <button
          class="btn btn-xs btn-ghost btn-square {isSidebarCollapsed
            ? 'hidden'
            : ''}"
          on:click={toggleSidebar}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg
          >
        </button>
      </div>

      <!-- Collapsed Toggle (if collapsed, show it centered below header) -->
      {#if isSidebarCollapsed}
        <div class="flex justify-center py-2 border-b border-base-300">
          <button
            class="btn btn-xs btn-ghost btn-square rotate-180"
            on:click={toggleSidebar}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg
            >
          </button>
        </div>
      {/if}

      <!-- Menu Items -->
      <ul class="flex-1 overflow-y-auto py-4 space-y-1">
        <li>
          <a
            class="flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors
               {currentView === 'fleet'
              ? 'bg-primary/10 text-primary font-medium'
              : 'text-base-content/70 hover:bg-base-200'}
               {isSidebarCollapsed ? 'justify-center px-2' : ''}"
            on:click={goBack}
            title="Dashboard"
          >
            <span class="w-5 h-5">{@html Icons.dashboard}</span>
            {#if !isSidebarCollapsed}<span>Dashboard</span>{/if}
          </a>
        </li>

        <li>
          <a
            class="flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors
               {currentView === 'audit'
              ? 'bg-primary/10 text-primary font-medium'
              : 'text-base-content/70 hover:bg-base-200'}
               {isSidebarCollapsed ? 'justify-center px-2' : ''}"
            on:click={() => {
              currentView = "audit";
              selectedSystemId = null;
            }}
            title="Audit Logs"
          >
            <span class="w-5 h-5">{@html Icons.box}</span>
            {#if !isSidebarCollapsed}<span>Audit Logs</span>{/if}
          </a>
        </li>

        <li>
          <a
            href="https://console.cloud.google.com/storage/browser/kriplani-backups"
            target="_blank"
            class="flex items-center gap-3 px-4 py-3 mx-2 rounded-lg text-base-content/70 hover:bg-base-200
               {isSidebarCollapsed ? 'justify-center px-2' : ''}"
            title="Backups"
          >
            <span class="w-5 h-5">{@html Icons.database}</span>
            {#if !isSidebarCollapsed}<span>Backups</span>{/if}
          </a>
        </li>

        {#if !isSidebarCollapsed}
          <div class="divider my-4 mx-4"></div>
          {#if user.email === "admin@kriplanibuilders.com"}
            <div
              class="px-6 text-xs font-bold opacity-40 uppercase tracking-widest mb-2"
            >
              Platform
            </div>
            <li>
              <a
                href="https://firebase.google.com"
                target="_blank"
                class="flex items-center gap-3 px-4 py-3 mx-2 rounded-lg text-base-content/70 hover:bg-base-200"
              >
                <span class="w-5 h-5 flex justify-center">🔥</span>
                <span>Firebase</span>
              </a>
            </li>
          {/if}
        {/if}
      </ul>

      <!-- Sidebar Footer -->
      <div class="p-4 border-t border-base-300">
        {#if !isSidebarCollapsed}
          <div class="text-center">
            <p
              class="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase mb-1"
            >
              Created By
            </p>
            <span class="text-xs font-black text-slate-400 tracking-wide"
              >PNAAC IT LABS</span
            >
          </div>
        {:else}
          <div class="flex justify-center text-xs font-bold text-slate-300">
            P
          </div>
        {/if}
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 h-full relative">
      <!-- Top Navbar (Mobile: Branding + Theme | Desktop: Breadcrumbs + Theme) -->
      <header
        class="h-16 flex items-center justify-between px-6 bg-base-100/80 backdrop-blur border-b border-base-300 z-20 sticky top-0"
      >
        <!-- Left: Branding (Mobile) or Breadcrumbs (Desktop) -->
        <div class="flex items-center gap-2">
          <!-- Mobile Brand -->
          <div class="lg:hidden flex items-center gap-2">
            <div
              class="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center shadow-lg shadow-primary/30"
            >
              {@html Icons.shield}
            </div>
            <span class="font-bold text-lg"
              >Backup<span class="text-primary">Control</span></span
            >
          </div>

          <!-- Desktop Breadcrumbs -->
          <div class="hidden lg:block">
            {#if currentView === "system"}
              <div class="text-sm breadcrumbs">
                <ul>
                  <li>
                    <a on:click={goBack} class="opacity-60 hover:opacity-100"
                      >Fleet</a
                    >
                  </li>
                  <li class="font-semibold text-primary">System Details</li>
                </ul>
              </div>
            {:else if currentView === "audit"}
              <h1 class="font-bold text-lg text-base-content/80">Audit Logs</h1>
            {:else}
              <h1 class="font-bold text-lg text-base-content/80">
                Fleet Overview
              </h1>
            {/if}
          </div>
        </div>

        <!-- Right: Actions -->
        <div class="flex items-center gap-2">
          <button
            class="btn btn-sm btn-circle btn-ghost"
            on:click={toggleTheme}
            title="Switch Theme"
          >
            {#if themePreference === "system"}
              🖥️
            {:else if themePreference === "kriplani_light"}
              ☀️
            {:else}
              🌙
            {/if}
          </button>

          <div class="dropdown dropdown-end">
            <label
              tabindex="0"
              class="btn btn-ghost btn-circle avatar placeholder"
            >
              <div class="bg-primary text-primary-content rounded-full w-8">
                <span>{user.email[0].toUpperCase()}</span>
              </div>
            </label>
            <ul
              tabindex="0"
              class="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52 border border-base-300"
            >
              <li class="menu-title px-4 py-2 text-xs opacity-50">
                {user.email}
              </li>
              <li>
                <button on:click={logout} class="text-error">Logout</button>
              </li>
            </ul>
          </div>
        </div>
      </header>

      <!-- Scrollable Content -->
      <main class="flex-1 overflow-y-auto p-4 lg:p-6 pb-24 lg:pb-6">
        {#if currentView === "fleet"}
          <FleetView on:select={handleSelectSystem} currentUser={user} />
        {:else if currentView === "system"}
          <SystemDetailView
            systemId={selectedSystemId}
            currentUser={user}
            on:back={goBack}
          />
        {:else if currentView === "audit"}
          <AuditLogsView />
        {/if}
      </main>
    </div>

    <!-- Mobile Bottom Navigation -->
    <div
      class="btm-nav lg:hidden z-50 border-t border-base-200 bg-base-100/90 backdrop-blur safe-area-bottom"
    >
      <button
        class={currentView === "fleet" || currentView === "system"
          ? "active text-primary"
          : "text-base-content/50"}
        on:click={goBack}
      >
        <span class="w-5 h-5">{@html Icons.dashboard}</span>
        <span class="btm-nav-label text-xs">Home</span>
      </button>

      <button
        class={currentView === "audit"
          ? "active text-primary"
          : "text-base-content/50"}
        on:click={() => {
          currentView = "audit";
          selectedSystemId = null;
        }}
      >
        <span class="w-5 h-5">{@html Icons.box}</span>
        <span class="btm-nav-label text-xs">Logs</span>
      </button>

      <button class="text-base-content/50" on:click={toggleTheme}>
        <span class="w-5 h-5 flex justify-center items-center">
          {#if themePreference === "system"}🖥️{:else if themePreference === "kriplani_light"}☀️{:else}🌙{/if}
        </span>
        <span class="btm-nav-label text-xs">Theme</span>
      </button>
    </div>
  </div>
{/if}
