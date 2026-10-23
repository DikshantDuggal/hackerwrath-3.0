import express from 'express';
import http from 'http';
import { spawn, ChildProcess } from 'child_process';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const PYTHON_PORT = Number(process.env.PYTHON_BACKEND_PORT || 8000);
const isDev = process.env.NODE_ENV !== 'production';

let pythonProc: ChildProcess | null = null;

function startPythonBackend(): void {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  pythonProc = spawn(pythonCmd, ['-m', 'app.asgi_stdlib_runner'], {
    env: {
      ...process.env,
      PYTHON_BACKEND_PORT: String(PYTHON_PORT),
    },
    stdio: 'inherit',
    cwd: __dirname,
  });

  pythonProc.on('exit', (code) => {
    console.error(`Python FastAPI backend exited with code ${code}; restarting in 2s...`);
    setTimeout(startPythonBackend, 2000);
  });
}

function proxyToPython(req: express.Request, res: express.Response): void {
  const options: http.RequestOptions = {
    hostname: '127.0.0.1',
    port: PYTHON_PORT,
    path: req.originalUrl,
    method: req.method,
    headers: {
      ...req.headers,
      host: `127.0.0.1:${PYTHON_PORT}`,
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.status(proxyRes.statusCode || 500);
    Object.entries(proxyRes.headers).forEach(([key, value]) => {
      if (value !== undefined) {
        res.setHeader(key, value);
      }
    });
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    res.status(502).json({
      detail: `Python FastAPI backend unavailable on port ${PYTHON_PORT}: ${err.message}`,
    });
  });

  req.pipe(proxyReq);
}

async function startServer(): Promise<void> {
  startPythonBackend();

  const app = express();

  // Forward all backend API routes to the Python FastAPI service
  app.use(['/health', '/transcribe', '/analyze', '/calls', '/sync', '/telegram', '/internal'], (req, res) => {
    proxyToPython(req, res);
  });

  if (isDev) {
    // In dev, Vite handles the frontend via its own dev server
    const { createServer } = await import('vite');
    const vite = await createServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    // In production, serve the built frontend
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n🛡️  SURAKSHA MVP running on http://localhost:${PORT}`);
    console.log(`   Python FastAPI backend on 127.0.0.1:${PYTHON_PORT}`);
    console.log(`   Mode: ${isDev ? 'development' : 'production'}\n`);
  });
}

startServer();
