const API_BASE = import.meta.env.VITE_API_URL || '/api'
const HEALTH_URL = `${API_BASE.replace('/api', '')}/health`

export async function fetchPackages() {
  const res = await fetch(`${API_BASE}/packages/`)
  if (!res.ok) throw new Error('Failed to fetch packages')
  return res.json()
}

export async function fetchPackagesWithStatus() {
  const res = await fetch(`${API_BASE}/packages/with-status`)
  if (!res.ok) throw new Error('Failed to fetch packages')
  return res.json()
}

export async function fetchDocuments(employeeName) {
  const res = await fetch(`${API_BASE}/documents/${employeeName}`)
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function fetchSignatureStatus(employeeName) {
  try {
    const res = await fetch(`${API_BASE}/packages/${employeeName}/signature-status`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchSignatureDetails(employeeName) {
  try {
    const res = await fetch(`${API_BASE}/packages/${employeeName}/signatures`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function uploadDocuments(employeeName, files) {
  const formData = new FormData()
  formData.append('employee_name', employeeName)
  for (const file of files) {
    formData.append('files', file)
  }

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData
  })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export async function processUploadedFiles(employeeName, files) {
  const res = await fetch(`${API_BASE}/documents/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_name: employeeName, files })
  })
  if (!res.ok) throw new Error('Process failed')
  return res.json()
}

export async function mergePackage(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/merge`, {
    method: 'POST'
  })
  if (!res.ok) throw new Error('Merge failed')
  return res.json()
}

export async function deletePackage(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}`, {
    method: 'DELETE'
  })
  if (!res.ok) throw new Error('Delete failed')
  return res.json()
}

export async function clearDocumentStatus(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/clear-status`, {
    method: 'POST'
  })
  if (!res.ok) throw new Error('Failed to clear status')
  return res.json()
}

export async function resetDocumentFields(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/reset-fields`, {
    method: 'POST'
  })
  if (!res.ok) throw new Error('Failed to reset fields')
  return res.json()
}

export async function checkHealth() {
  try {
    const res = await fetch(HEALTH_URL)
    return res.ok
  } catch {
    return false
  }
}

export function getDownloadUrl(employeeName) {
  return `${API_BASE}/packages/${encodeURIComponent(employeeName)}/download`
}

export function getDocumentDownloadUrl(employeeName, docId) {
  return `${API_BASE}/packages/${encodeURIComponent(employeeName)}/download/${docId}`
}
