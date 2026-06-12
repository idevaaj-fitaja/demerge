<script>
  import { onMount } from 'svelte'
  import { fetchPackagesWithStatus, cleanupExpired } from '../lib/api.js'

  let packages = $state([])
  let loading = $state(true)
  let error = $state(null)

  onMount(async () => {
    cleanupExpired()
    try {
      packages = await fetchPackagesWithStatus()
    } catch (e) {
      try {
        const { fetchPackages } = await import('../lib/api.js')
        packages = await fetchPackages()
      } catch (e2) {
        error = e2.message
      }
    } finally {
      loading = false
    }
  })

  function sigIcon(status) {
    if (status === 'all_signed') return '●'
    if (status === 'partially_signed') return '◐'
    return '○'
  }

  let stats = $derived({
    total: packages.length,
    merged: packages.filter(p => p.status === 'merged').length,
    docs: packages.reduce((a, p) => a + (p.document_count || 0), 0),
    signed: packages.filter(p => p.signature_status === 'all_signed').length
  })
</script>

<div>
  <h1 class="text-2xl font-bold tracking-tight">Dashboard</h1>
  <p class="text-sm text-muted mt-1">Overview of document processing</p>

  {#if loading}
    <div class="mt-8 text-sm text-muted">Loading...</div>
  {:else if error}
    <div class="mt-8 text-sm text-red-500">{error}</div>
  {:else}
    <div class="grid grid-cols-4 gap-3 mt-6">
      <div class="bg-[#fafafa] border border-border rounded-lg p-4 hover:border-ink transition-colors">
        <div class="text-2xl font-bold">{stats.total}</div>
        <div class="text-xs text-muted mt-1 uppercase tracking-wider font-medium">Employees</div>
      </div>
      <div class="bg-[#fafafa] border border-border rounded-lg p-4 hover:border-ink transition-colors">
        <div class="text-2xl font-bold">{stats.merged}</div>
        <div class="text-xs text-muted mt-1 uppercase tracking-wider font-medium">Merged</div>
      </div>
      <div class="bg-[#fafafa] border border-border rounded-lg p-4 hover:border-ink transition-colors">
        <div class="text-2xl font-bold">{stats.docs}</div>
        <div class="text-xs text-muted mt-1 uppercase tracking-wider font-medium">Documents</div>
      </div>
      <div class="bg-[#fafafa] border border-border rounded-lg p-4 hover:border-ink transition-colors">
        <div class="text-2xl font-bold text-green-700">{stats.signed}</div>
        <div class="text-xs text-muted mt-1 uppercase tracking-wider font-medium">Fully Signed</div>
      </div>
    </div>

    {#if packages.length > 0}
      <h2 class="text-sm font-semibold uppercase tracking-wider text-muted mt-8 mb-3">Employees</h2>
      <div class="space-y-2">
        {#each packages as pkg}
          <div class="bg-[#fafafa] border border-border rounded-lg px-4 py-3 flex items-center justify-between hover:border-ink transition-colors">
            <div>
              <div class="font-semibold text-sm">{pkg.employee_name}</div>
              <div class="text-xs text-muted">{pkg.document_count || 0} documents</div>
            </div>
            <div class="text-lg">
              {sigIcon(pkg.signature_status)}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="mt-8 bg-[#fafafa] border border-border rounded-lg p-12 text-center">
        <div class="text-3xl mb-3 opacity-30">📭</div>
        <div class="text-sm font-medium">No documents yet</div>
        <div class="text-xs text-muted mt-1">Merge to get started</div>
      </div>
    {/if}
  {/if}
</div>
