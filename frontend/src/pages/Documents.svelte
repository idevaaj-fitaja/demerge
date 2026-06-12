<script>
  import { onMount } from 'svelte'
  import { fetchPackages, fetchDocuments, fetchSignatureDetails, mergePackage, deletePackage, getDownloadUrl, getDocumentDownloadUrl, bulkDeletePackages, bulkDownloadPackages } from '../lib/api.js'

  let { navigate } = $props()

  let packages = $state([])
  let loading = $state(true)
  let search = $state('')
  let expanded = $state(null)
  let merging = $state(null)
  let deleting = $state(null)
  let actionMessage = $state(null)

  let docs = $state([])
  let sigs = $state(null)
  let loadingDocs = $state(false)

  let selected = $state({})
  let bulkAction = $state(null)

  let confirmModal = $state(null)

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

  let selectedCount = $derived(Object.values(selected).filter(Boolean).length)

  function showBulkDeleteConfirm() {
    const names = Object.keys(selected).filter(k => selected[k])
    if (!names.length) return
    confirmModal = {
      type: 'bulk-delete',
      title: `Delete ${names.length} employee(s)?`,
      message: `This will permanently delete all documents and merged PDFs for: ${names.join(', ')}`,
      onConfirm: executeBulkDelete
    }
  }

  async function executeBulkDelete() {
    const names = Object.keys(selected).filter(k => selected[k])
    confirmModal = null
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

  function showDeleteConfirm(empName, hasMerged) {
    confirmModal = {
      type: 'single-delete',
      title: `Delete ${empName}?`,
      message: hasMerged
        ? `This will permanently delete all documents and the merged PDF for ${empName}.`
        : `This will permanently delete all documents for ${empName}.`,
      onConfirm: () => executeDelete(empName)
    }
  }

  async function executeDelete(empName) {
    confirmModal = null
    deleting = empName
    actionMessage = null
    try {
      await deletePackage(empName)
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
      {#if !search}
        <button
          onclick={() => navigate('merge')}
          class="mt-4 px-4 py-2 bg-ink text-white text-xs font-medium rounded-md hover:bg-[#333] transition-colors"
        >
          Go to Merge
        </button>
      {/if}
    </div>
  {:else}
    <input
      type="text"
      bind:value={search}
      placeholder="Search employee..."
      class="w-full border border-border rounded-md px-3 py-2 text-sm mt-6 focus:outline-none focus:border-ink transition-colors"
    />

    {#if selectedCount > 0}
      <div class="flex items-center justify-between mt-4 px-4 py-3 bg-ink text-white rounded-lg">
        <span class="text-sm font-medium">{selectedCount} selected</span>
        <div class="flex items-center gap-3">
          <button
            class="px-4 py-1.5 bg-white/15 hover:bg-white/25 rounded-md text-xs font-medium transition-colors disabled:opacity-30 flex items-center gap-1.5"
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
            class="px-4 py-1.5 bg-red-500 hover:bg-red-600 rounded-md text-xs font-medium transition-colors disabled:opacity-30 flex items-center gap-1.5"
            disabled={bulkAction === 'delete'}
            onclick={showBulkDeleteConfirm}
          >
            {#if bulkAction === 'delete'}
              <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Deleting...
            {:else}
              🗑 Delete
            {/if}
          </button>
          <button
            class="px-4 py-1.5 bg-white/15 hover:bg-white/25 rounded-md text-xs font-medium transition-colors"
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
            <div class="px-4 py-4 border-t border-border bg-white">
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

                  <button
                    class="w-full border border-border py-2 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors disabled:opacity-30"
                    disabled={merging === empName || deleting === empName}
                    onclick={() => showDeleteConfirm(empName, hasMerged)}
                  >
                    🗑 Delete
                  </button>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    {#if actionMessage}
      <div
        class="fixed bottom-6 right-6 text-sm px-4 py-2.5 rounded-lg shadow-lg border z-50
          {actionMessage.type === 'success' ? 'bg-green-50 text-green-700 border-green-200' : ''}
          {actionMessage.type === 'error' ? 'bg-red-50 text-red-700 border-red-200' : ''}"
      >
        {actionMessage.text}
      </div>
    {/if}
  {/if}

  {#if confirmModal}
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={() => confirmModal = null} role="presentation">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()}>
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
            <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div>
            <h3 class="text-sm font-semibold">{confirmModal.title}</h3>
            <p class="text-xs text-muted mt-0.5">{confirmModal.message}</p>
          </div>
        </div>
        <div class="flex gap-2 mt-5">
          <button
            class="flex-1 border border-border py-2 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors"
            onclick={() => confirmModal = null}
          >
            Cancel
          </button>
          <button
            class="flex-1 bg-red-500 text-white py-2 rounded-md text-xs font-medium hover:bg-red-600 transition-colors"
            onclick={confirmModal.onConfirm}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  {/if}

</div>
