<script>
  import { onMount } from 'svelte'
  import Dashboard from './pages/Dashboard.svelte'
  import Upload from './pages/Upload.svelte'
  import Documents from './pages/Documents.svelte'
  import { checkHealth } from './lib/api.js'

  let page = $state('dashboard')
  let online = $state(false)
  let backendReady = $state(false)

  onMount(() => {
    let retries = 0

    async function poll() {
      const ok = await checkHealth()
      online = ok
      if (ok && !backendReady) {
        backendReady = true
      }
      retries++
      if (!ok && retries < 60) {
        setTimeout(poll, 500)
      }
    }

    poll()
    const interval = setInterval(() => {
      checkHealth().then(v => {
        online = v
        if (v && !backendReady) backendReady = true
      })
    }, 3000)
    return () => clearInterval(interval)
  })

  let pageKey = $derived(backendReady ? `ready-${page}` : `wait-${page}`)

  const nav = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'merge', label: 'Merge' },
    { id: 'documents', label: 'Documents' }
  ]
</script>

<div class="flex min-h-screen">
  <aside class="w-56 bg-[#fafafa] border-r border-border flex flex-col shrink-0">
    <div class="p-5 border-b border-border">
      <h1 class="text-base font-bold tracking-tight">Demerge</h1>
      <p class="text-xs text-muted mt-0.5">Document Management</p>
    </div>

    <nav class="flex-1 p-3 space-y-1">
      {#each nav as item}
        <button
          class="w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors
            {page === item.id
              ? 'bg-ink text-white'
              : 'text-muted hover:bg-border hover:text-ink'}"
          onclick={() => page = item.id}
        >
          {item.label}
        </button>
      {/each}
    </nav>

    <div class="p-4 border-t border-border">
      <div class="flex items-center gap-2 text-xs">
        <span class="w-2 h-2 rounded-full {online ? 'bg-green-600' : 'bg-red-500'}"></span>
        <span class="text-muted">{online ? 'System Online' : 'System Offline'}</span>
      </div>
    </div>
  </aside>

  <main class="flex-1 overflow-auto">
    <div class="max-w-5xl mx-auto px-8 py-8">
      {#if !backendReady}
        <div class="mt-8 text-sm text-muted">Starting backend...</div>
      {:else}
        {#key pageKey}
          {#if page === 'dashboard'}
            <Dashboard navigate={(p) => page = p} />
          {:else if page === 'merge'}
            <Upload />
          {:else if page === 'documents'}
            <Documents navigate={(p) => page = p} />
          {/if}
        {/key}
      {/if}
    </div>
  </main>
</div>
