<script>
  import { onMount } from 'svelte'
  import { fetchPackages, fetchDocuments, fetchSignatureDetails, mergePackage, deletePackage, getDownloadUrl, getDocumentDownloadUrl, bulkDeletePackages, bulkDownloadPackages } from '../lib/api.js'

  let packages = $state([])
  let loading = $state(true)
  let search = $state('')
  let expanded = $state(null)
  let confirming = $state(null)
  let merging = $state(null)
  let deleting = $state(null)
  let actionMessage = $state(null)

  let docs = $state([])
  let sigs = $state(null)
  let loadingDocs = $state(false)

  let selected = $state({})
  let bulkAction = $state(null)

  onMount(async () => {
    await loadPackages()
  })

  async function loadPackages() {
    loading = true
    try {
      packages = await fetchPackages()
    } catch (e) {
      console.error(e)
    } finally {
      loading = false
    }
  }

  function toggleSelect(empName) {
    selected = { ...selected, [empName]: !selected[empName] }
  }

  function toggleSelectAll() {
    const allSelected = filtered.length > 0 && filtered.every(p => selected[p.employee_name])
    const next = {}
    if (!allSelected) {
      for (const p of filtered) next[p.employee_name] = true
    }
    selected = next
  }

  let selectedCount = $derived(Object.values(selected).filter(Boolean).length)
  let allSelected = $derived(filtered.length > 0 && filtered.every(p => selected[p.employee_name]))

  async function handleBulkDelete() {
    const names = Object.keys(selected).filter(k => selected[k])
    if (!names.length) return
    bulkAction = 'delete'
    actionMessage = null
    try {
      const result = await bulkDeletePackages(names)
      selected = {}
      actionMessage = { type: 'success', text: `Deleted ${result.deleted.length} employee(s)` }
      await loadPackages()
    } catch (e) {
      actionMessage = { type: 'error', text: e.message }
    } finally {
      bulkAction = null
      setTimeout(() => actionMessage = null, 3000)
    }
  }

  async function handleBulkDownload() {
    const names = Object.keys(selected).filter(k => selected[k])
    if (!names.length) return
    bulkAction = 'download'
    actionMessage = null
    try {
      await bulkDownloadPackages(names)
      actionMessage = { type: 'success', text: 'Download started' }
    } catch (e) {
      actionMessage = { type: 'error', text: e.message }
    } finally {
      bulkAction = null
      setTimeout(() => actionMessage = null, 3000)
    }
  }

  async function toggleExpand(empName) {
    if (expanded === empName) {
      expanded = null
      docs = []
      sigs = null
      return
    }
    expanded = empName
    confirming = null
    loadingDocs = true
    docs = []
    sigs = null
    try {
      const [d, s] = await Promise.all([
        fetchDocuments(empName),
        fetchSignatureDetails(empName)
      ])
      docs = d || []
      sigs = s
    } catch (e) {
      console.error(e)
    } finally {
      loadingDocs = false
    }
  }

  async function handleMerge(empName) {
    merging = empName
    actionMessage = null
    try {
      await mergePackage(empName)
      actionMessage = { type: 'success', text: `Merged documents for ${empName}` }
      await loadPackages()
    } catch (e) {
      actionMessage = { type: 'error', text: e.message }
    } finally {
      merging = null
      setTimeout(() => actionMessage = null, 3000)
    }
  }

  async function handleDelete(empName) {
    deleting = empName
    actionMessage = null
    try {
      await deletePackage(empName)
      confirming = null
      actionMessage = { type: 'success', text: `Deleted all data for ${empName}` }
      await loadPackages()
    } catch (e) {
      actionMessage = { type: 'error', text: e.message }
    } finally {
      deleting = null
      setTimeout(() => actionMessage = null, 3000)
    }
  }

  function sigMap() {
    const map = {}
    if (sigs?.documents) {
      for (const sd of sigs.documents) {
        map[sd.document_name] = sd
      }
    }
    return map
  }

  let filtered = $derived(
    search
      ? packages.filter(p => p.employee_name.toLowerCase().includes(search.toLowerCase()))
      : packages
  )
</script>

<div>
  <h1 class="text-2xl font-bold tracking-tight">Documents</h1>
  <p class="text-sm text-muted mt-1">Manage and download document packages</p>

  {#if loading}
    <div class="mt-8 text-sm text-muted">Loading...</div>
  {:else if filtered.length === 0}
    <div class="mt-8 bg-[#fafafa] border border-border rounded-lg p-12 text-center">
      <div class="text-3xl mb-3 opacity-30">📭</div>
      <div class="text-sm font-medium">{search ? 'No results' : 'No documents yet'}</div>
      <div class="text-xs text-muted mt-1">{search ? 'Try a different search' : 'Merge first'}</div>
    </div>
  {:else}
    <input
      type="text"
      bind:value={search}
      placeholder="Search employee..."
      class="w-full border border-border rounded-md px-3 py-2 text-sm mt-6 focus:outline-none focus:border-ink transition-colors"
    />

    {#if selectedCount > 0}
      <div class="flex items-center justify-between mt-4 px-3 py-2.5 bg-ink text-white rounded-lg text-sm">
        <span>{selectedCount} selected</span>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1 bg-white/20 rounded text-xs font-medium hover:bg-white/30 transition-colors disabled:opacity-30 flex items-center gap-1.5"
            disabled={bulkAction === 'download'}
            onclick={handleBulkDownload}
          >
            {#if bulkAction === 'download'}
              <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Downloading...
            {:else}
              ⬇ Download ZIP
            {/if}
          </button>
          <button
            class="px-3 py-1 bg-red-500 rounded text-xs font-medium hover:bg-red-600 transition-colors disabled:opacity-30 flex items-center gap-1.5"
            disabled={bulkAction === 'delete'}
            onclick={handleBulkDelete}
          >
            {#if bulkAction === 'delete'}
              <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Deleting...
            {:else}
              🗑 Delete
            {/if}
          </button>
          <button
            class="px-3 py-1 bg-white/20 rounded text-xs font-medium hover:bg-white/30 transition-colors"
            onclick={() => selected = {}}
          >
            ✕ Clear
          </button>
        </div>
      </div>
    {/if}

    <div class="space-y-2 mt-4">
      {#each filtered as pkg}
        {@const empName = pkg.employee_name}
        {@const isOpen = expanded === empName}
        {@const hasMerged = !!pkg.merged_pdf_path}
        {@const isChecked = !!selected[empName]}

        <div class="border border-border rounded-lg overflow-hidden {isOpen ? 'border-ink' : 'hover:border-ink'} transition-colors">
          <div class="flex items-center bg-[#fafafa] hover:bg-[#f0f0f0] transition-colors">
            <label class="flex items-center px-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isChecked}
                onchange={(e) => { e.stopPropagation(); toggleSelect(empName) }}
                class="w-4 h-4 rounded border-border text-ink focus:ring-ink cursor-pointer"
              />
            </label>
            <button
              class="w-full text-left py-3 pr-4 flex items-center justify-between"
              onclick={() => toggleExpand(empName)}
            >
              <div class="flex items-center gap-3">
                <span class="text-sm font-semibold">{empName}</span>
                <span class="text-xs text-muted">— {pkg.document_count || 0} docs</span>
                {#if hasMerged}
                  <span class="text-xs text-green-700 bg-green-50 px-1.5 py-0.5 rounded">Merged</span>
                {:else}
                  <span class="text-xs text-muted bg-gray-100 px-1.5 py-0.5 rounded">Not merged</span>
                {/if}
              </div>
              <svg class="w-4 h-4 text-muted transition-transform {isOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {#if isOpen}
            <div class="px-4 py-4 border-t border-border bg-white ml-10">
              <div class="grid grid-cols-4 gap-4">
                <div class="col-span-3">
                  {#if loadingDocs}
                    <div class="flex items-center gap-2 text-xs text-muted">
                      <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                      Scanning documents...
                    </div>
                  {:else if docs.length > 0}
                    {@const sm = sigMap()}
                    <div class="space-y-1.5">
                      {#each docs as doc}
                        {@const sig = sm[doc.original_filename]}
                        <div class="flex items-center justify-between text-xs py-2 px-3 rounded {sig?.is_signed ? 'bg-green-50' : 'bg-red-50'}">
                          <div class="flex items-center gap-2">
                            <span class={sig?.is_signed ? 'text-green-700' : 'text-red-500'}>
                              {sig?.is_signed ? '●' : '○'}
                            </span>
                            <span class="font-medium">{doc.original_filename}</span>
                          </div>
                          <div class="flex items-center gap-3">
                            {#if sig?.is_signed}
                              <span class="text-green-700">{sig.platform?.toUpperCase() || 'SIGNED'}</span>
                            {:else}
                              <span class="text-red-500">Unsigned</span>
                            {/if}
                            <a
                              href={getDocumentDownloadUrl(empName, doc.id)}
                              target="_blank"
                              class="text-muted hover:text-ink transition-colors"
                              title="Download"
                            >
                              ⬇
                            </a>
                          </div>
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <div class="text-xs text-muted">No documents</div>
                  {/if}
                </div>

                <div class="space-y-2">
                  {#if hasMerged}
                    <a
                      href={getDownloadUrl(empName)}
                      target="_blank"
                      class="block w-full text-center bg-ink text-white py-2 rounded-md text-xs font-medium hover:bg-[#333] transition-colors"
                    >
                      ⬇ Download Merged
                    </a>
                  {:else}
                    <button
                      class="w-full bg-ink text-white py-2 rounded-md text-xs font-medium hover:bg-[#333] transition-colors disabled:opacity-30 flex items-center justify-center gap-1.5"
                      disabled={merging === empName}
                      onclick={() => handleMerge(empName)}
                    >
                      {#if merging === empName}
                        <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        Merging...
                      {:else}
                        🔀 Merge All Signed
                      {/if}
                    </button>
                  {/if}

                  {#if confirming === empName}
                    <div class="text-xs text-muted mb-1">Are you sure?</div>
                    <div class="grid grid-cols-2 gap-1.5">
                      <button
                        class="bg-red-500 text-white py-1.5 rounded-md text-xs font-medium hover:bg-red-600 transition-colors disabled:opacity-30 flex items-center justify-center gap-1.5"
                        disabled={deleting === empName}
                        onclick={() => handleDelete(empName)}
                      >
                        {#if deleting === empName}
                          <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                          Deleting...
                        {:else}
                          Yes
                        {/if}
                      </button>
                      <button
                        class="border border-border py-1.5 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors"
                        disabled={deleting === empName}
                        onclick={() => confirming = null}
                      >
                        No
                      </button>
                    </div>
                  {:else}
                    <button
                      class="w-full border border-border py-2 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors disabled:opacity-30"
                      disabled={merging === empName || deleting === empName}
                      onclick={() => confirming = empName}
                    >
                      🗑 Delete
                    </button>
                  {/if}
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if actionMessage}
      <div
        class="fixed bottom-6 right-6 text-sm px-4 py-2.5 rounded-lg shadow-lg border
          {actionMessage.type === 'success' ? 'bg-green-50 text-green-700 border-green-200' : ''}
          {actionMessage.type === 'error' ? 'bg-red-50 text-red-700 border-red-200' : ''}"
      >
        {actionMessage.text}
      </div>
    {/if}
  {/if}

</div>
