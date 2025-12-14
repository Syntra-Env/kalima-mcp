import os from 'os';
import path from 'path';
import fs from 'fs';
import { spawn, spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

let tauriDriverProcess;
let exit = false;

function repoRoot() {
  return path.resolve(__dirname, '..', '..');
}

function resolveTauriDriverBinary() {
  const binaryName = process.platform === 'win32' ? 'tauri-driver.exe' : 'tauri-driver';
  return path.resolve(os.homedir(), '.cargo', 'bin', binaryName);
}

function resolveNativeWebDriverBinary() {
  if (process.platform !== 'win32') return null;

  const fromEnv = (process.env.MSEDGEDRIVER_PATH || '').trim();
  if (fromEnv) return fromEnv;

  const toolsPath = path.resolve(repoRoot(), 'tools', 'webdriver', 'msedgedriver.exe');
  if (fs.existsSync(toolsPath)) return toolsPath;

  try {
    const result = spawnSync('where.exe', ['msedgedriver.exe'], { encoding: 'utf8' });
    if (result.status === 0 && typeof result.stdout === 'string') {
      const candidate = result.stdout
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)[0];
      if (candidate && fs.existsSync(candidate)) return candidate;
    }
  } catch {
    // ignore
  }

  try {
    const base = path.resolve(process.env.LOCALAPPDATA || '', 'Microsoft', 'WinGet', 'Packages');
    if (fs.existsSync(base)) {
      const entries = fs.readdirSync(base, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        if (!entry.name.toLowerCase().startsWith('microsoft.edgedriver_')) continue;
        const candidate = path.join(base, entry.name, 'msedgedriver.exe');
        if (fs.existsSync(candidate)) return candidate;
      }
    }
  } catch {
    // ignore
  }

  return null;
}

function resolveAppBinary() {
  const candidates = [
    path.resolve(repoRoot(), 'desktop', 'src-tauri', 'target', 'debug', process.platform === 'win32' ? 'app.exe' : 'app'),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

function closeTauriDriver() {
  exit = true;
  tauriDriverProcess?.kill();
}

function onShutdown(fn) {
  const cleanup = () => {
    try {
      fn();
    } finally {
      process.exit();
    }
  };

  process.on('exit', cleanup);
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('SIGHUP', cleanup);
  process.on('SIGBREAK', cleanup);
}

onShutdown(() => closeTauriDriver());

export const config = {
  host: '127.0.0.1',
  port: 4444,
  specs: ['./specs/**/*.e2e.js'],
  maxInstances: 1,
  capabilities: [
    {
      maxInstances: 1,
      'tauri:options': {
        application: resolveAppBinary(),
      },
    },
  ],
  reporters: ['spec'],
  framework: 'mocha',
  mochaOpts: {
    ui: 'bdd',
    timeout: 60_000,
  },

  onPrepare: () => {
    spawnSync(
      'cargo',
      ['build', '--manifest-path', path.resolve(repoRoot(), 'desktop', 'src-tauri', 'Cargo.toml')],
      {
        cwd: repoRoot(),
        stdio: 'inherit',
      }
    );
  },

  beforeSession: () => {
    const tauriDriver = resolveTauriDriverBinary();
    if (!fs.existsSync(tauriDriver)) {
      // eslint-disable-next-line no-console
      console.error(
        `tauri-driver not found at ${tauriDriver}. Install it with: cargo install tauri-driver --locked`
      );
      process.exit(1);
    }

    const args = [];
    const nativeDriver = resolveNativeWebDriverBinary();
    if (nativeDriver) {
      args.push('--native-driver', nativeDriver);
    }

    tauriDriverProcess = spawn(tauriDriver, args, {
      stdio: [null, process.stdout, process.stderr],
    });

    tauriDriverProcess.on('error', (error) => {
      // eslint-disable-next-line no-console
      console.error('tauri-driver error:', error);
      process.exit(1);
    });

    tauriDriverProcess.on('exit', (code) => {
      if (!exit) {
        // eslint-disable-next-line no-console
        console.error('tauri-driver exited with code:', code);
        process.exit(1);
      }
    });
  },

  afterSession: () => {
    closeTauriDriver();
  },
};
