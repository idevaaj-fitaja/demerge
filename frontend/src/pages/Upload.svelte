<script>
  import { fetchSignatureStatus, fetchSignatureDetails, getUploadUrls, processUploadedFiles } from '../lib/api.js'
  import { supabase } from '../lib/supabase.js'

  let employeeName = $state('')
  let files = $state([])
  let uploading = $state(false)
  let message = $state(null)
  let messageType = $state('')

  let sigStatus = $state(null)
  let sigDetails = $state(null)
  let checking = $state(false)
  let fileInput = $state(null)
  let uploadDone = $state(false)

  async function handleUpload() {
    if (!employeeName || files.length === 0) return
    uploading = true
    message = null
    sigStatus = null
    sigDetails = null
    uploadDone = false
    try {
      const filenames = files.map(f => f.name)
      const urlData = await getUploadUrls(employeeName, filenames)
      if (!urlData.success) {
        message = urlData.message
        messageType = 'error'
        return
      }

      const uploaded = []
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        const urlInfo = urlData.uploads[i]
        if (supabase && urlInfo.token) {
          const { error } = await supabase.storage
            .from('documents')
            .uploadToSignedUrl(urlInfo.storage_path, urlInfo.token, file)
          if (error) throw new Error(`Upload failed: ${error.message}`)
        } else {
          const res = await fetch(urlInfo.signed_url, {
            method: 'PUT',
            body: file,
            headers: { 'Content-Type': 'application/pdf' }
          })
          if (!res.ok) throw new Error(`Upload failed for ${file.name}`)
        }
        uploaded.push({ storage_path: urlInfo.storage_path, filename: file.name })
      }

      const result = await processUploadedFiles(employeeName, uploaded)

      if (result.success) {
        message = result.message
        messageType = 'success'
        files = []
        if (fileInput) fileInput.value = ''
        uploadDone = true
        await checkSignature()
      } else {
        message = result.message
        messageType = 'error'
        uploadDone = true
      }
    } catch (e) {
      message = `Error: ${e.message}`
      messageType = 'error'
    } finally {
      uploading = false
    }
  }

  async function checkSignature() {
    if (!employeeName) return
    checking = true
    try {
      sigStatus = await fetchSignatureStatus(employeeName)
      sigDetails = await fetchSignatureDetails(employeeName)
    } catch {
      sigStatus = null
      sigDetails = null
    } finally {
      checking = false
    }
  }

  function handleFileInput(e) {
    files = Array.from(e.target.files)
  }

  function removeFile(index) {
    files = files.filter((_, i) => i !== index)
  }

  function handleClearStatus() {
    sigStatus = null
    sigDetails = null
    uploadDone = false
  }

  function handleResetFields() {
    employeeName = ''
    files = []
    sigStatus = null
    sigDetails = null
    message = null
    uploadDone = false
    if (fileInput) fileInput.value = ''
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }
</script>

<div>
  <h1 class="text-2xl font-bold tracking-tight">Merge</h1>
  <p class="text-sm text-muted mt-1">Check signatures and merge employee documents</p>

  <div class="mt-6 space-y-4">
    <div>
      <label class="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">Employee Name</label>
      <input
        type="text"
        bind:value={employeeName}
        placeholder="e.g. John Doe Day"
        class="w-full border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-ink transition-colors"
      />
    </div>

    <div>
      <label class="block text-xs font-semibold uppercase tracking-wider text-muted mb-1.5">Documents (PDF)</label>
      <input
        type="file"
        accept=".pdf"
        multiple
        bind:this={fileInput}
        onchange={handleFileInput}
        class="w-full border border-dashed border-border rounded-lg px-3 py-6 text-sm text-muted file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-ink file:text-white file:text-xs file:font-medium file:cursor-pointer hover:border-ink transition-colors"
      />
    </div>

    {#if files.length > 0}
      <div class="border border-border rounded-lg divide-y divide-border">
        {#each files as file, i}
          <div class="flex items-center justify-between px-3 py-2">
            <div class="flex items-center gap-2 text-sm">
              <span class="text-muted">📄</span>
              <span>{file.name}</span>
              <span class="text-xs text-muted">({formatSize(file.size)})</span>
            </div>
            <button
              onclick={() => removeFile(i)}
              class="text-xs text-muted hover:text-red-500 transition-colors"
            >
              ✕
            </button>
          </div>
        {/each}
      </div>
      <p class="text-xs text-muted">{files.length} file(s) selected</p>
    {/if}

    <button
      onclick={handleUpload}
      disabled={!employeeName || files.length === 0 || uploading}
      class="w-full bg-ink text-white py-2.5 rounded-md text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#333] transition-colors"
    >
      {#if uploading}Checking & Merging...{:else}Check Signatures & Merge{/if}
    </button>

    {#if message}
      <div class="text-sm px-3 py-2 rounded-md {messageType === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}">
        {message}
      </div>
    {/if}

    <div class="flex gap-2">
      <button
        class="flex-1 border border-border bg-white text-ink py-2 rounded-md text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={!sigStatus && !uploadDone}
        onclick={handleClearStatus}
      >
        Clear Status
      </button>
      <button
        class="flex-1 border border-border bg-white text-ink py-2 rounded-md text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        disabled={!employeeName && files.length === 0}
        onclick={handleResetFields}
      >
        Reset
      </button>
    </div>
  </div>

  {#if sigStatus || checking}
    <div class="mt-8">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-muted mb-3">Signature Status</h2>

      {#if checking}
        <div class="border border-border rounded-lg p-6 text-center">
          <div class="text-xs text-muted">Scanning documents...</div>
        </div>
      {:else if sigStatus}
        <div class="border border-border rounded-lg p-4">
          {#if sigStatus.status === 'all_signed'}
            <div class="text-green-700 font-semibold text-sm">● All Signed</div>
            <div class="text-xs text-muted mt-1">{sigStatus.message || ''}</div>
          {:else if sigStatus.status === 'partially_signed'}
            <div class="text-yellow-600 font-semibold text-sm">◐ Partially Signed</div>
            <div class="text-xs text-muted mt-1">{sigStatus.message || ''}</div>
          {:else}
            <div class="text-red-500 font-semibold text-sm">○ Not Signed</div>
            <div class="text-xs text-muted mt-1">{sigStatus.message || 'No signatures detected'}</div>
          {/if}

          {#if sigDetails?.documents?.length > 0}
            <div class="mt-3 pt-3 border-t border-border space-y-2">
              {#each sigDetails.documents as doc}
                <div class="flex items-center justify-between text-xs py-1.5">
                  <span class="font-medium">{doc.document_name}</span>
                  {#if doc.is_signed}
                    <span class="text-green-700">● {doc.platform?.toUpperCase() || 'SIGNED'}</span>
                  {:else}
                    <span class="text-muted">○ Unsigned</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>
