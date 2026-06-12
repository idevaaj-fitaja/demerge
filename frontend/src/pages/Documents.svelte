<script>
  import { onMount } from 'svelte'
  import { fetchPackages, fetchDocuments, fetchSignatureStatus, fetchSignatureDetails, mergePackage, deletePackage, getDownloadUrl, getDocumentDownloadUrl } from '../lib/api.js'

  let packages = $state([])
  let loading = $state(true)
  let search = $state('')
  let expanded = $state(null)
  let confirming = $state(null)
  let merging = $state(null)
  let actionMessage = $state(null)

  let docs = $state([])
  let sigs = $state(null)
  let loadingDocs = $state(false)

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
    try {
      await deletePackage(empName)
      confirming = null
      await loadPackages()
    } catch (e) {
      actionMessage = { type: 'error', text: e.message }
    }
  }

  function sigIcon(status) {
    if (status === 'all_signed') return '●'
    if (status === 'partially_signed') return '◐'
    return '○'
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

    <div class="space-y-2 mt-4">
      {#each filtered as pkg}
        {@const empName = pkg.employee_name}
        {@const isOpen = expanded === empName}
        {@const hasMerged = !!pkg.merged_pdf_path}

        <div class="border border-border rounded-lg overflow-hidden {isOpen ? 'border-ink' : 'hover:border-ink'} transition-colors">
          <button
            class="w-full text-left px-4 py-3 flex items-center justify-between bg-[#fafafa] hover:bg-[#f0f0f0] transition-colors"
            onclick={() => toggleExpand(empName)}
          >
            <div class="flex items-center gap-3">
              {#await fetchSignatureStatus(empName) then s}
                <span class="text-sm">{sigIcon(s?.status)}</span>
              {:catch}
                <span class="text-sm">○</span>
              {/await}
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

          {#if isOpen}
            <div class="px-4 py-4 border-t border-border bg-white">
              <div class="grid grid-cols-4 gap-4">
                <div class="col-span-3">
                  {#if loadingDocs}
                    <div class="text-xs text-muted">Loading...</div>
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
                      class="w-full bg-ink text-white py-2 rounded-md text-xs font-medium hover:bg-[#333] transition-colors disabled:opacity-30"
                      disabled={merging === empName}
                      onclick={() => handleMerge(empName)}
                    >
                      {#if merging === empName}Merging...{:else}🔀 Merge All Signed{/if}
                    </button>
                  {/if}

                  {#if confirming === empName}
                    <div class="text-xs text-muted mb-1">Are you sure?</div>
                    <div class="grid grid-cols-2 gap-1.5">
                      <button
                        class="bg-red-500 text-white py-1.5 rounded-md text-xs font-medium hover:bg-red-600 transition-colors"
                        onclick={() => handleDelete(empName)}
                      >
                        Yes
                      </button>
                      <button
                        class="border border-border py-1.5 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors"
                        onclick={() => confirming = null}
                      >
                        No
                      </button>
                    </div>
                  {:else}
                    <button
                      class="w-full border border-border py-2 rounded-md text-xs font-medium hover:bg-[#fafafa] transition-colors"
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
