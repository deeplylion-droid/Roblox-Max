// Processo principale di Electron: una finestra sola con la build di Vite (dist/index.html).
// Niente menu, niente integrazione con Node nella pagina: il gioco è la stessa build della versione web.
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('node:path');

// le GPU con la blacklist di Chromium: il gioco ha bisogno di WebGL2 con i float
app.commandLine.appendSwitch('ignore-gpu-blocklist');
// l'audio parte subito (il gioco ha già la schermata d'avvertenza prima del primo suono)
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 900,
    minWidth: 960,
    minHeight: 540,
    backgroundColor: '#05080d',
    title: 'SPLASHLAND IS CLOSED!',
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  });
  Menu.setApplicationMenu(null);
  win.once('ready-to-show', () => win.show());
  // F11: schermo intero (anche dalle opzioni del gioco, con l'API del browser)
  win.webContents.on('before-input-event', (_e, input) => {
    if (input.type === 'keyDown' && input.key === 'F11') win.setFullScreen(!win.isFullScreen());
  });
  // i link esterni (se mai ce ne saranno) si aprono nel browser, non nel gioco
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
  win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
