<script>
  import { fetchSignatureStatus, fetchSignatureDetails, processUploadedFiles } from '../lib/api.js'
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
  let dragOver = $state(false)

  let uploadProgress = $state({ current: 0, total: 0, phase: '', fileName: '' })

  function sanitizeName(name) {
    return name.replace(/[^a-zA-Z0-9._-]/g, '_').toLowerCase().slice(0, 50)
  }

  function sanitizeFilename(name) {
    return name.replace(/[^a-zA-Z0-9._-]/g, '_')
  }

  function addFiles(newFiles) {
    const pdfOnly = Array.from(newFiles).filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'))
    if (pdfOnly.length === 0) {
      message = 'Only PDF files are accepted'
      messageType = 'error'
      return
    }
    files = [...files, ...pdfOnly]
  }

  function handleDrop(e) {
    e.preventDefault()
    dragOver = false
    if (uploading) return
    addFiles(e.dataTransfer.files)
  }

  function handleDragOver(e) {
    e.preventDefault()
    if (!uploading) dragOver = true
  }

  function handleDragLeave(e) {
    e.preventDefault()
    dragOver = false
  }

  async function handleUpload() {
    if (!employeeName || files.length === 0) return
    uploading = true
    message = null
    sigStatus = null
    sigDetails = null
    uploadDone = false
    uploadProgress = { current: 0, total: files.length, phase: 'upload', fileName: '' }
    try {
      if (!supabase) {
        throw new Error('Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.')
      }

      const safeName = sanitizeName(employeeName)
      const uploaded = []

      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        uploadProgress = { current: i + 1, total: files.length, phase: 'upload', fileName: file.name }
        const safeFilename = sanitizeFilename(file.name)
        const hash = Math.random().toString(36).slice(2, 10)
        const storagePath = `raw/${safeName}/${hash}_${safeFilename}`

        const { error } = await supabase.storage
          .from('documents')
          .upload(storagePath, file, { contentType: 'application/pdf' })

        if (error) throw new Error(`Upload failed for ${file.name}: ${error.message}`)
        uploaded.push({ storage_path: storagePath, filename: file.name })
      }

      uploadProgress = { current: files.length, total: files.length, phase: 'process', fileName: '' }
      const result = await processUploadedFiles(employeeName, uploaded)

      if (result.success) {
        message = result.message
        messageType = 'success'
        files = []
        if (fileInput) fileInput.value = ''
        uploadDone = true
        uploadProgress = { current: 0, total: 0, phase: 'done', fileName: '' }
        await checkSignature()
      } else {
        message = result.message
        messageType = 'error'
        uploadDone = true
        uploadProgress = { current: 0, total: 0, phase: '', fileName: '' }
      }
    } catch (e) {
      message = `Error: ${e.message}`
      messageType = 'error'
      uploadProgress = { current: 0, total: 0, phase: '', fileName: '' }
    } finally {
      uploading = false
    }
  }

  async function checkSignature() {
    if (!employeeName) return
    checking = true
    uploadProgress = { current: 0, total: 0, phase: 'scan', fileName: '' }
    try {
      sigStatus = await fetchSignatureStatus(employeeName)
      sigDetails = await fetchSignatureDetails(employeeName)
    } catch {
      sigStatus = null
      sigDetails = null
    } finally {
      checking = false
      uploadProgress = { current: 0, total: 0, phase: '', fileName: '' }
    }
  }

  function handleFileInput(e) {
    addFiles(e.target.files)
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
    uploadProgress = { current: 0, total: 0, phase: '', fileName: '' }
    if (fileInput) fileInput.value = ''
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  let progressPercent = $derived(
    uploadProgress.phase === 'upload' && uploadProgress.total > 0
      ? Math.round((uploadProgress.current / uploadProgress.total) * 100)
      : uploadProgress.phase === 'process' || uploadProgress.phase === 'scan'
        ? 100
        : 0
  )
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
      <div
        class="relative border-2 border-dashed rounded-lg transition-colors cursor-pointer
          {dragOver ? 'border-ink bg-ink/5' : 'border-border hover:border-ink'}"
        ondrop={handleDrop}
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        onclick={() => fileInput?.click()}
        role="button"
        tabindex="0"
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInput?.click() }}
      >
        <input
          type="file"
          accept=".pdf"
          multiple
          bind:this={fileInput}
          onchange={handleFileInput}
          class="hidden"
        />
        <div class="px-3 py-8 text-center">
          {#if dragOver}
            <div class="text-ink font-medium text-sm">Drop PDFs here</div>
          {:else}
            <div class="text-muted">
              <svg class="w-8 h-8 mx-auto mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6v12m-6-6h12" />
              </svg>
              <div class="text-sm font-medium">Drop PDFs here or <span class="text-ink underline">browse</span></div>
              <div class="text-xs mt-1">Multiple files accepted</div>
            </div>
          {/if}
        </div>
      </div>
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

    {#if uploading || checking}
      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted">
            {#if uploadProgress.phase === 'upload'}
              Uploading {uploadProgress.fileName}...
            {:else if uploadProgress.phase === 'process'}
              Processing documents...
            {:else if uploadProgress.phase === 'scan'}
              Scanning signatures...
            {:else}
              Working...
            {/if}
          </span>
          <span class="font-medium">
            {#if uploadProgress.phase === 'upload'}
              {uploadProgress.current}/{uploadProgress.total}
            {:else if uploadProgress.phase === 'process'}
              100%
            {:else if uploadProgress.phase === 'scan'}
              Scanning...
            {/if}
          </span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            class="bg-ink h-2 rounded-full transition-all duration-300 ease-out"
            style="width: {progressPercent}%"
          ></div>
        </div>
      </div>
    {/if}

    <button
      onclick={handleUpload}
      disabled={!employeeName || files.length === 0 || uploading}
      class="w-full bg-ink text-white py-2.5 rounded-md text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#333] transition-colors flex items-center justify-center gap-2"
    >
      {#if uploading}
        <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        Uploading...
      {:else}
        Check Signatures & Merge
      {/if}
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
          <div class="flex items-center justify-center gap-2 text-xs text-muted">
            <svg class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Scanning documents...
          </div>
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
