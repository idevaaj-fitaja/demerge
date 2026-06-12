const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

let mainWindow = null
let pythonProcess = null
const BACKEND_PORT = 8000
const MAX_RETRIES = 30

const isDev = !app.isPackaged

function getResourcesPath() {
  if (isDev) return path.join(__dirname, '..')
  return path.join(process.resourcesPath)
}

function getPythonPath() {
  const resources = getResourcesPath()
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin'
  const pyName = process.platform === 'win32' ? 'python.exe' : (isDev ? 'python3' : 'python')
  return path.join(resources, 'venv-minimal', binDir, pyName)
}

function startPython() {
  const resources = getResourcesPath()
  const pythonPath = getPythonPath()
  const runScript = path.join(resources, 'run.py')

  pythonProcess = spawn(pythonPath, [runScript], {
    cwd: resources,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, DEMERGE_PACKAGED: isDev ? '0' : '1' },
  })

  pythonProcess.stdout.on('data', (d) => process.stdout.write(`[py] ${d}`))
  pythonProcess.stderr.on('data', (d) => process.stderr.write(`[py] ${d}`))
  pythonProcess.on('exit', (code) => {
    if (code !== 0 && !pythonProcess.killed) {
      setTimeout(startPython, 1000)
    }
  })
}

function waitForBackend(retries = 0) {
  http.get(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
    if (res.statusCode === 200) {
      mainWindow.loadURL(`http://127.0.0.1:${BACKEND_PORT}`)
    } else if (retries < MAX_RETRIES) {
      setTimeout(() => waitForBackend(retries + 1), 500)
    }
  }).on('error', () => {
    if (retries < MAX_RETRIES) {
      setTimeout(() => waitForBackend(retries + 1), 500)
    }
  })
}

const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.whenReady().then(() => {
    mainWindow = new BrowserWindow({
      width: 1100,
      height: 800,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
      show: false,
    })

    mainWindow.once('ready-to-show', () => mainWindow.show())
    mainWindow.loadFile(path.join(__dirname, 'loading.html'))

    startPython()
    setTimeout(() => waitForBackend(), 1500)

    // Handle file downloads — save to ~/Downloads/Demerge/{Employee Name}/{Employee Name}.pdf
    const baseDir = path.join(app.getPath('downloads'), 'Demerge')
    const fs = require('fs')

    mainWindow.webContents.session.on('will-download', (event, item) => {
      const urlStr = item.getURL()
      console.error('DOWNLOAD URL:', urlStr)
      const url = new URL(urlStr)
      const match = url.pathname.match(/\/api\/packages\/([^/]+)\//)
      const empName = match ? decodeURIComponent(match[1]) : 'Unknown'
      const isMerged = url.pathname.endsWith('/download')
      const empDir = path.join(baseDir, empName)
      if (!fs.existsSync(empDir)) fs.mkdirSync(empDir, { recursive: true })

      const filename = isMerged ? `${empName}.pdf` : (item.getFilename() || `${empName}.pdf`)
      const savePath = path.join(empDir, filename)
      item.setSavePath(savePath)
      item.on('done', (event, state) => {
        mainWindow.webContents.send('download-status', {
          filename,
          state,
          success: state === 'completed',
          path: savePath
        })
      })
    })

    // target="_blank" — deny new window, trigger download directly
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      mainWindow.webContents.session.downloadURL(url)
      return { action: 'deny' }
    })
  })

  app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill()
    app.quit()
  })

  app.on('will-quit', () => {
    if (pythonProcess) pythonProcess.kill()
  })
}
