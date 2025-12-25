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
  let theme = localStorage.getItem("theme") || "kriplani_light";

  // Auth Listener
  onMount(() => {
    document.documentElement.setAttribute("data-theme", theme);
    const unsubscribe = onAuthStateChanged(auth, (u) => {
      user = u;
      loadingAuth = false;
      if (user) {
        backupStore.init(user.uid);
      }
    });
    return unsubscribe;
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
    theme = theme === "kriplani_light" ? "kriplani_dark" : "kriplani_light";
    localStorage.setItem("theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
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
    class="min-h-screen flex items-center justify-center bg-slate-100 p-4 sm:p-6 md:p-8 lg:p-12 font-sans"
  >
    <!-- Floating Card Container -->
    <div
      class="w-full max-w-6xl bg-white rounded-[2rem] shadow-2xl overflow-hidden flex flex-col lg:flex-row min-h-[600px] lg:min-h-[700px]"
    >
      <!-- Left Side: Branding (Dark Aesthetic) -->
      <div
        class="lg:w-5/12 bg-slate-900 relative p-12 flex flex-col justify-between overflow-hidden"
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
          class="absolute top-20 right-10 w-32 h-32 bg-primary blur-[80px] rounded-full opacity-40"
        ></div>
        <div
          class="absolute bottom-20 left-10 w-40 h-40 bg-secondary blur-[80px] rounded-full opacity-30"
        ></div>

        <!-- Brand Content -->
        <div class="relative z-10 mt-10">
          <div class="w-16 h-1 bg-secondary rounded-full mb-6"></div>
          <h1 class="text-5xl font-bold text-white leading-tight mb-6">
            Kriplani<br />Consumables.
          </h1>
          <p class="text-slate-400 text-lg">
            Next-Gen Enterprise Infrastructure
          </p>
        </div>

        <div class="relative z-10">
          <!-- Version text removed -->
        </div>
      </div>

      <!-- Right Side: Login Form (Clean with Graphics) -->
      <div
        class="lg:w-7/12 bg-white relative p-12 lg:p-24 flex flex-col justify-center"
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
              class="btn btn-block h-16 text-lg font-bold !text-white border-0 bg-secondary hover:bg-secondary/80 shadow-xl shadow-secondary/25 rounded-xl flex items-center justify-center gap-3 transition-transform hover:scale-[1.01] active:scale-[0.99]"
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
        <a
          href="https://pnaac.com"
          target="_blank"
          class="absolute bottom-6 right-8 text-right opacity-40 hover:opacity-100 transition-opacity duration-300 group z-10"
        >
          <p
            class="text-[10px] font-bold tracking-[0.2em] text-slate-400 uppercase mb-0.5 group-hover:text-primary transition-colors"
          >
            Developed & Maintained By
          </p>
          <div class="flex items-center justify-end gap-1.5">
            <span class="text-xs font-black text-slate-800 tracking-wide">
              PNAAC IT LABS
            </span>
            <span
              class="px-1 py-px rounded bg-slate-100 text-[9px] font-bold text-slate-500 border border-slate-200"
              >PVT LTD</span
            >
          </div>
        </a>
      </div>
    </div>
  </div>
{:else}
  <!-- App Shell -->
  <div class="drawer lg:drawer-open font-sans bg-base-200 min-h-screen">
    <input id="my-drawer-2" type="checkbox" class="drawer-toggle" />
    <div class="drawer-content flex flex-col">
      <!-- Header -->
      <div
        class="navbar bg-base-100 border-b border-base-300 px-6 sticky top-0 z-30"
      >
        <div class="flex-none lg:hidden">
          <label for="my-drawer-2" class="btn btn-square btn-ghost">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              class="inline-block w-6 h-6 stroke-current"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              ></path></svg
            >
          </label>
        </div>
        <div class="flex-1">
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
          {:else}
            <h1 class="font-bold text-lg text-base-content/80">
              Fleet Overview
            </h1>
          {/if}
        </div>
        <div class="flex-none gap-2">
          <button
            class="btn btn-sm btn-circle btn-ghost"
            on:click={toggleTheme}
          >
            {#if theme === "kriplani_light"}
              🌙
            {:else}
              ☀️
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
      </div>

      <!-- Main Content -->
      <main class="flex-1 p-6 overflow-y-auto">
        {#if currentView === "fleet"}
          <FleetView on:select={handleSelectSystem} currentUser={user} />
        {:else if currentView === "system"}
          <SystemDetailView
            systemId={selectedSystemId}
            currentUser={user}
            on:back={goBack}
          />
        {/if}
      </main>
    </div>

    <!-- Sidebar -->
    <div class="drawer-side z-40">
      <label for="my-drawer-2" class="drawer-overlay"></label>
      <ul
        class="menu p-4 w-72 min-h-full bg-base-100 border-r border-base-300 text-base-content"
      >
        <!-- Sidebar Header -->
        <li class="mb-6">
          <div class="flex items-center gap-3 px-2">
            <div
              class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white shadow-lg shadow-primary/40"
            >
              {@html Icons.shield}
            </div>
            <div>
              <div class="font-bold text-lg leading-tight">
                Backup<span class="text-primary">Control</span>
              </div>
              <div
                class="text-[10px] uppercase tracking-widest opacity-50 font-semibold"
              >
                Enterprise
              </div>
            </div>
          </div>
        </li>

        <!-- Menu Items -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <!-- svelte-ignore a11y-missing-attribute -->
        <li class="mb-1">
          <a
            class:active={currentView === "fleet"}
            on:click={goBack}
            class="font-medium rounded-lg">{@html Icons.dashboard} Dashboard</a
          >
        </li>
        <li>
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <!-- svelte-ignore a11y-missing-attribute -->
          <a
            class:active={currentView === "audit"}
            on:click={() => {
              currentView = "audit";
              selectedSystemId = null;
            }}
            class="font-medium rounded-lg">{@html Icons.box} Audit Logs</a
          >
        </li>

        <div class="divider my-4"></div>

        {#if user.email === "admin@kriplanibuilders.com"}
          <div
            class="px-4 text-xs font-bold opacity-40 uppercase tracking-widest mb-2"
          >
            Platform
          </div>
          <li>
            <a
              href="https://firebase.google.com"
              target="_blank"
              class="font-medium rounded-lg opacity-70">Firebase Console</a
            >
          </li>
        {/if}
      </ul>
    </div>
  </div>
{/if}
