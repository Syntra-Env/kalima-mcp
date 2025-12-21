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

function resolveAppBinary() {
  const candidates = [
    path.resolve(
      repoRoot(),
      'desktop',
      'src-tauri',
      'target',
      'debug',
      process.platform === 'win32' ? 'app.exe' : 'app'
    ),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

function closeTauriDriver() {
  exit = true;
  tauriDriverProcess?.kill();
  tauriDriverProcess = undefined;
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

function getWebView2RuntimeVersion() {
  if (process.platform !== 'win32') return null;
  const key =
    'HKLM\\SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  const result = spawnSync('reg.exe', ['query', key, '/v', 'pv'], { encoding: 'utf8' });
  if (result.status !== 0) return null;
  const out = String(result.stdout || '');
  const match = out.match(/\bpv\s+REG_\w+\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/i);
  return match?.[1] || null;
}

function parseDriverVersion(output) {
  // "Microsoft Edge WebDriver 142.0.3595.94 (...)" -> "142.0.3595.94"
  const match = String(output || '').match(/WebDriver\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/i);
  return match?.[1] || null;
}

function resolveNativeWebDriverBinary() {
  if (process.platform !== 'win32') return null;

  const fromEnv = (process.env.MSEDGEDRIVER_PATH || '').trim();
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;

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

  return null;
}

function getNativeDriverVersion(driverPath) {
  try {
    const result = spawnSync(driverPath, ['--version'], { encoding: 'utf8' });
    if (result.status !== 0) return null;
    return parseDriverVersion(result.stdout) || parseDriverVersion(result.stderr);
  } catch {
    return null;
  }
}

function ensureDriverMajorMatchesWebView2() {
  if (process.platform !== 'win32') return;

  const webview2 = getWebView2RuntimeVersion();
  const driverPath = resolveNativeWebDriverBinary();
  const driverVersion = driverPath ? getNativeDriverVersion(driverPath) : null;

  if (!webview2 || !driverVersion) return;
  const webMajor = webview2.split('.')[0];
  const driverMajor = driverVersion.split('.')[0];
  if (webMajor === driverMajor) return;

  throw new Error(
    [
      `WebView2 runtime is ${webview2}, but msedgedriver is ${driverVersion}.`,
      `Install the matching Edge WebDriver (major ${webMajor}) and re-run E2E.`,
      `Suggested shows available versions: winget list --id Microsoft.EdgeDriver`,
      `Upgrade command: winget upgrade --id Microsoft.EdgeDriver --accept-source-agreements --accept-package-agreements`,
      `Or set MSEDGEDRIVER_PATH to a matching msedgedriver.exe.`,
    ].join('\n')
  );
}

export const config = {
  host: '127.0.0.1',
  port: 4444,
  // Single spec aggregator = single worker/session (avoids parallel WebView2 flakiness).
  specs: ['./specs/all.e2e.js'],
  maxInstances: 1,
  capabilities: [
    {
      'wdio:maxInstances': 1,
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
      { cwd: repoRoot(), stdio: 'inherit' }
    );
  },

  beforeSession: () => {
    ensureDriverMajorMatchesWebView2();

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
    if (nativeDriver) args.push('--native-driver', nativeDriver);

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

