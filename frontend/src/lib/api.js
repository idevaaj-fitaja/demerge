const API_BASE = import.meta.env.VITE_API_URL || '/api'
const API_KEY = import.meta.env.VITE_API_KEY || ''
const HF_TOKEN = import.meta.env.VITE_HF_TOKEN || ''
const HEALTH_URL = `${API_BASE.replace('/api', '')}/health`

function getHeaders(contentType) {
  const headers = {}
  if (contentType) headers['Content-Type'] = contentType
  if (API_KEY) headers['X-API-Key'] = API_KEY
  if (HF_TOKEN) headers['Authorization'] = `Bearer ${HF_TOKEN}`
  return headers
}

export async function fetchPackages() {
  const res = await fetch(`${API_BASE}/packages/`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch packages')
  return res.json()
}

export async function fetchPackagesWithStatus() {
  const res = await fetch(`${API_BASE}/packages/with-status`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch packages')
  return res.json()
}

export async function fetchDocuments(employeeName) {
  const res = await fetch(`${API_BASE}/documents/${employeeName}`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function fetchSignatureStatus(employeeName) {
  try {
    const res = await fetch(`${API_BASE}/packages/${employeeName}/signature-status`, { headers: getHeaders() })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function fetchSignatureDetails(employeeName) {
  try {
    const res = await fetch(`${API_BASE}/packages/${employeeName}/signatures`, { headers: getHeaders() })
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
    headers: getHeaders(),
    body: formData
  })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export async function processUploadedFiles(employeeName, files) {
  const res = await fetch(`${API_BASE}/documents/process`, {
    method: 'POST',
    headers: getHeaders('application/json'),
    body: JSON.stringify({ employee_name: employeeName, files })
  })
  if (!res.ok) throw new Error('Process failed')
  return res.json()
}

export async function mergePackage(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/merge`, {
    method: 'POST',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Merge failed')
  return res.json()
}

export async function deletePackage(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}`, {
    method: 'DELETE',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Delete failed')
  return res.json()
}

export async function bulkDeletePackages(employeeNames) {
  const res = await fetch(`${API_BASE}/packages/bulk-delete`, {
    method: 'POST',
    headers: getHeaders('application/json'),
    body: JSON.stringify({ employee_names: employeeNames })
  })
  if (!res.ok) throw new Error('Bulk delete failed')
  return res.json()
}

export async function bulkDownloadPackages(employeeNames) {
  const res = await fetch(`${API_BASE}/packages/bulk-download`, {
    method: 'POST',
    headers: getHeaders('application/json'),
    body: JSON.stringify({ employee_names: employeeNames })
  })
  if (!res.ok) throw new Error('Bulk download failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'merged_documents.zip'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function clearDocumentStatus(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/clear-status`, {
    method: 'POST',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to clear status')
  return res.json()
}

export async function resetDocumentFields(employeeName) {
  const res = await fetch(`${API_BASE}/packages/${employeeName}/reset-fields`, {
    method: 'POST',
    headers: getHeaders()
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

export async function cleanupExpired() {
  try {
    const res = await fetch(`${API_BASE}/documents/cleanup`, {
      method: 'POST',
      headers: getHeaders()
    })
    return res.ok ? res.json() : null
  } catch {
    return null
  }
}
