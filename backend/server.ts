import express from 'express';
import http from 'http';
import { spawn, ChildProcess } from 'child_process';
import dotenv from 'dotenv';

dotenv.config();

const PORT = 3000;
const PYTHON_PORT = Number(process.env.PYTHON_BACKEND_PORT || 8000);

let pythonProc: ChildProcess | null = null;

function startPythonBackend(): void {
  pythonProc = spawn('python3', ['-m', 'app.asgi_stdlib_runner'], {
    env: {
      ...process.env,
      PYTHON_BACKEND_PORT: String(PYTHON_PORT),
    },
    stdio: 'inherit',
  });

  pythonProc.on('exit', (code) => {
    console.error(`Python FastAPI backend exited with code ${code}; restarting in 1s...`);
    setTimeout(startPythonBackend, 1000);
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

  // Forward all backend API routes directly to the Python FastAPI service (raw stream for multipart/JSON)
  app.use(['/health', '/transcribe', '/analyze', '/calls', '/sync'], (req, res) => {
    proxyToPython(req, res);
  });

  // Root endpoint returns backend-only API directory JSON (zero UI/HTML dashboard)
  app.get('/', (_req, res) => {
    res.json({
      service: 'AI-Powered Scam-Call Detection Backend (Python FastAPI)',
      mode: 'backend-only',
      endpoints: [
        'GET /health',
        'POST /transcribe',
        'POST /analyze/transcript',
        'POST /calls/{call_id}/segments',
        'GET /calls/{call_id}/risk',
        'GET /calls/{call_id}/history',
        'DELETE /calls/{call_id}',
        'GET /sync/keywords',
        'POST /sync/keywords',
      ],
    });
  });

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Backend gateway listening on http://localhost:${PORT} -> Python FastAPI on 127.0.0.1:${PYTHON_PORT}`);
  });
}

startServer();
