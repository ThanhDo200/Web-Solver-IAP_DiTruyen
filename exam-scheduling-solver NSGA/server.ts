import express from "express";
import path from "path";
import fs from "fs";
import { createServer as createViteServer } from "vite";
import { spawn, ChildProcessWithoutNullStreams } from 'child_process';

const ENGINE_DIR = path.join(process.cwd(), '..', 'exam-scheduling-engine-main NSGA II');
const BENCHMARK_DIR = path.join(process.cwd(), '..', 'benchmark-iap-main');

function engineDataDir() {
  return path.join(ENGINE_DIR, 'data');
}

function csvEscape(val: unknown): string {
  return `"${String(val ?? '').replace(/"/g, '""')}"`;
}

/** Ghi CSV cán bộ với header chuẩn mà Python loader/benchmark đọc được */
function writeStaffCsvForEngine(filePath: string, staff: Array<Record<string, unknown>>) {
  const headers = [
    'MS của CÁN BỘ COI THI',
    'Giới tính',
    'Tuổi',
    'Khoảng cách đến Cơ sở 1 (km)',
    'Khoảng cách đến Cơ sở 2 (km)',
  ];
  const rows = staff.map((s) =>
    [
      s.id ?? s['MS của CÁN BỘ COI THI'] ?? '',
      s.gender ?? s['Giới tính'] ?? 'Nam',
      s.age ?? s['Tuổi'] ?? 40,
      s.distCS1 ?? s['Khoảng cách đến Cơ sở 1 (km)'] ?? 0,
      s.distCS2 ?? s['Khoảng cách đến Cơ sở 2 (km)'] ?? 0,
    ].map(csvEscape).join(',')
  );
  fs.writeFileSync(filePath, `\uFEFF${headers.join(',')}\n${rows.join('\n')}`, 'utf-8');
}

/** Ghi CSV ca thi với header chuẩn mà Python loader/benchmark đọc được */
function writeShiftCsvForEngine(filePath: string, shifts: Array<Record<string, unknown>>) {
  const headers = [
    'Ca thi',
    'Ngày',
    'GIỜ',
    'Thời gian',
    'Thứ',
    'MS Ca thi',
    'Cơ sở',
    'Số lượng cán bộ cần thiết',
  ];
  const rows = shifts.map((s) =>
    [
      s.name ?? s['Ca thi'] ?? s.id ?? '',
      s.date ?? s['Ngày'] ?? '',
      s.time ?? s['GIỜ'] ?? '',
      s.duration ?? s['Thời gian'] ?? 150,
      s.dayOfWeek ?? s['Thứ'] ?? '',
      s.id ?? s['MS Ca thi'] ?? '',
      s.facility ?? s['Cơ sở'] ?? 'Cơ sở 1',
      s.staffRequired ?? s['Số lượng cán bộ cần thiết'] ?? 2,
    ].map(csvEscape).join(',')
  );
  fs.writeFileSync(filePath, `\uFEFF${headers.join(',')}\n${rows.join('\n')}`, 'utf-8');
}

function debugLog(hypothesisId: string, location: string, message: string, data: Record<string, unknown>) {
  // #region agent log
  try {
    const logPath = path.join(process.cwd(), '..', 'debug-529a9e.log');
    fs.appendFileSync(
      logPath,
      JSON.stringify({
        sessionId: '529a9e',
        hypothesisId,
        location,
        message,
        data,
        timestamp: Date.now(),
      }) + '\n',
      'utf-8'
    );
  } catch (_) { /* ignore */ }
  // #endregion
}

function parseCsvLine(text: string): string[] {
  let insideQuote = false;
  const entries: string[] = [];
  let current = '';
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"') {
      if (insideQuote && next === '"') {
        current += '"';
        i++;
      } else {
        insideQuote = !insideQuote;
      }
    } else if (char === ',' && !insideQuote) {
      entries.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  entries.push(current.trim());
  return entries;
}

function readCsvFile(filePath: string): string[][] {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, 'utf-8').replace(/^\uFEFF/, '');
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map(parseCsvLine);
}

function parseStaffRows(rows: string[][]) {
  if (rows.length <= 1) return [];

  const removeAccents = (str: string) => {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase().trim();
  };

  const rawHeaders = rows[0];
  const normalizedHeaders = rawHeaders.map(h => removeAccents(h).replace(/\s+/g, ''));

  const getColIdx = (targets: string[]) => {
    return normalizedHeaders.findIndex(h => targets.some(t => h === t || (t.length > 2 && h.includes(t))));
  };

  // Chỉ giữ các cột thực tế có trong file của bạn
  const idIdx = getColIdx(['mscuacanbo', 'coithi', 'macanbo', 'mscb', 'id']);
  const genderIdx = getColIdx(['gioitinh', 'gender']);
  const ageIdx = getColIdx(['tuoi', 'age']);
  const cs1Idx = getColIdx(['khoangcachdencoso1', 'distcs1', 'cs1']);
  const cs2Idx = getColIdx(['khoangcachdencoso2', 'distcs2', 'cs2']);

  const staff: any[] = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (!row || row.length === 0 || row.every(cell => cell.trim() === "")) continue;

    // Lấy ID: Ưu tiên idIdx, nếu không thấy thì lấy cột 0
    const id = (idIdx >= 0 ? row[idIdx] : row[0])?.replace(/^"|"$/g, '').trim();
    if (!id) continue;

    staff.push({
      id,
      name: `Cán bộ ${id}`, // Tự động đặt tên theo Mã số vì file không có cột Tên
      gender: (genderIdx >= 0 ? row[genderIdx] : 'Nam')?.replace(/^"|"$/g, '').trim(),
      age: parseInt(row[ageIdx >= 0 ? ageIdx : 0] || '40', 10) || 40,
      distCS1: parseFloat(row[cs1Idx >= 0 ? cs1Idx : 0] || '0') || 0,
      distCS2: parseFloat(row[cs2Idx >= 0 ? cs2Idx : 0] || '0') || 0,
      assignedCount: 0,
    });
  }
  return staff;
}

function normalizeFacilityValue(facility: string): string {
  const raw = (facility || '').trim();
  const lower = raw.toLowerCase();
  if (
    /\bcs\s*2\b/i.test(lower) ||
    /cơ\s*sở\s*2/i.test(lower) ||
    /co\s*so\s*2/i.test(lower) ||
    /^2$/.test(lower) ||
    (lower.includes('so') && /(^|\s)2(\s|$)/.test(lower))
  ) {
    return 'Cơ sở 2';
  }
  if (
    /\bcs\s*1\b/i.test(lower) ||
    /cơ\s*sở\s*1/i.test(lower) ||
    /co\s*so\s*1/i.test(lower) ||
    /^1$/.test(lower) ||
    (lower.includes('so') && /(^|\s)1(\s|$)/.test(lower))
  ) {
    return 'Cơ sở 1';
  }
  return raw || 'Cơ sở 1';
}

function parseShiftRows(rows: string[][]) {
  if (rows.length <= 1) return [];

  const removeAccents = (str: string) => {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase().trim();
  };

  const rawHeaders = rows[0];
  const normalizedHeaders = rawHeaders.map(h => removeAccents(h).replace(/\s+/g, ''));

  const getColIdx = (targets: string[]) => {
    return normalizedHeaders.findIndex(h => targets.some(t => h === t || (t.length > 2 && h.includes(t))));
  };

  const idIdx = getColIdx(['mscathi', 'macathi', 'id']);
  const nameIdx = getColIdx(['cathi', 'tencathi', 'shiftname']);
  const dateIdx = getColIdx(['ngay', 'date', 'ngaythi']);
  const timeIdx = getColIdx(['gio', 'time', 'thoigian', 'giothi']);
  const dowIdx = getColIdx(['thu', 'dayofweek', 'dow']);
  const facilityIdx = getColIdx(['coso', 'facility', 'cs', 'campus']);
  
  // Thêm từ khóa 'thiet' và 'cb' để bắt cột "Số lượng cán bộ cần thiết" chắc chắn hơn
  const reqIdx = getColIdx(['soluongcanbocanthiet', 'soluongcb', 'staffrequired', 'soluong', 'canbo', 'sl', 'thiet']);

  const shifts: any[] = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (!row || row.length === 0 || row.every(cell => cell.trim() === "")) continue;

    const id = (idIdx >= 0 ? row[idIdx] : row[0])?.replace(/^"|"$/g, '').trim();
    if (!id) continue;

    const facilityRaw = (facilityIdx >= 0 ? row[facilityIdx] : '')?.replace(/^"|"$/g, '').trim();
    const facility = normalizeFacilityValue(facilityRaw);
    
    const rawStaffReq = reqIdx >= 0 ? row[reqIdx] : '';

    shifts.push({
      id,
      name: (nameIdx >= 0 ? row[nameIdx] : id)?.replace(/^"|"$/g, '').trim(),
      date: (dateIdx >= 0 ? row[dateIdx] : '')?.replace(/^"|"$/g, '').split(' ')[0] ?? '',
      time: (timeIdx >= 0 ? row[timeIdx] : '')?.replace(/^"|"$/g, '').trim() ?? '',
      dayOfWeek: (dowIdx >= 0 ? row[dowIdx] : '')?.replace(/^"|"$/g, '').trim() ?? '',
      facility,
      staffRequired: parseInt(rawStaffReq || '2', 10) || 2,
    });
  }
  return shifts;
}

function resolvePythonExe(): string {
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH;
  const candidates = [
    path.join(process.cwd(), '.venv', 'Scripts', 'python.exe'),
    path.join(process.cwd(), '.venv', 'bin', 'python'),
    path.join(process.cwd(), '..', 'exam-scheduling-engine-main NSGA II', '.venv', 'Scripts', 'python.exe'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return 'python';
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Convert body parser JSON syntax errors into JSON responses.
  app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
    if (err instanceof SyntaxError && 'body' in err) {
      return res.status(400).json({ success: false, message: 'Invalid JSON body', error: err.message });
    }
    next(err);
  });

  // Dataset on disk (same files the Python solver reads)
  app.get('/api/data', (_req, res) => {
    try {
      const dataDir = engineDataDir();
      const staff = parseStaffRows(readCsvFile(path.join(dataDir, 'can_bo_new.csv')));
      const shifts = parseShiftRows(readCsvFile(path.join(dataDir, 'ca_thi_new.csv')));
      return res.json({ success: true, staff, shifts });
    } catch (err: any) {
      return res.status(500).json({ success: false, message: err.message, staff: [], shifts: [] });
    }
  });

  // Solver API - run Python backend and capture JSON output
  let currentProcess: ChildProcessWithoutNullStreams | null = null;

  const isSolverActive = (proc: ChildProcessWithoutNullStreams | null) => {
    return proc !== null && proc.exitCode === null && proc.signalCode === null;
  };

  app.get('/api/solve/status', (req, res) => {
    return res.json({
      success: true,
      active: !!currentProcess && isSolverActive(currentProcess),
      hasProcess: !!currentProcess,
      pid: currentProcess?.pid ?? null,
      exitCode: currentProcess?.exitCode ?? null,
      signalCode: currentProcess?.signalCode ?? null,
    });
  });

  app.post('/api/solve', (req, res) => {
    console.log('[api/solve] incoming request', { body: req.body, currentProcess: currentProcess ? { pid: currentProcess.pid, exitCode: currentProcess.exitCode, signalCode: currentProcess.signalCode, killed: currentProcess.killed } : null });

    if (currentProcess && isSolverActive(currentProcess)) {
      return res.status(409).json({ success: false, message: 'Solver already running' });
    }
    if (currentProcess && !isSolverActive(currentProcess)) {
      console.log('[api/solve] stale solver process detected, clearing currentProcess');
      currentProcess = null;
    }

    try {
      const repoRoot = ENGINE_DIR;
      const pythonExe = resolvePythonExe();
      const scriptPath = path.join(repoRoot, 'main.py');
      const cwd = repoRoot;
      //const config = req.body?.config || {};

      // Run the solver without creating Excel output during API solve.
      // const args: string[] = [
      //   scriptPath,
      //   '--skip-export',
      //   '--json-summary',
      // ];
      
      // --- ĐOẠN SỬA 1: Gửi cấu hình & dữ liệu từ frontend xuống Python qua stdin ---

      const dataDir = path.join(repoRoot, 'data');
      if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
      }

      // ⚠️ REMOVED: Don't overwrite ca_thi_new.csv & can_bo_new.csv during /api/solve
      // These files are already uploaded correctly via /api/upload-csv
      // The frontend sends MERGED shifts (aggregateShifts) which has fewer rows than original!
      // Re-writing them here corrupts the data (68 shifts → 58 shifts)
      
      // OLD CODE (CAUSING TRUNCATION):
      // if (req.body?.staff && Array.isArray(req.body.staff) && req.body.staff.length > 0) {
      //   const staffCsvPath = path.join(dataDir, 'can_bo_new.csv');
      //   writeStaffCsvForEngine(staffCsvPath, req.body.staff);
      // }
      // if (req.body?.shifts && Array.isArray(req.body.shifts) && req.body.shifts.length > 0) {
      //   const shiftCsvPath = path.join(dataDir, 'ca_thi_new.csv');
      //   writeShiftCsvForEngine(shiftCsvPath, req.body.shifts);
      // }
      
      console.log(`[Node.js] Using pre-uploaded CSV files from /api/upload-csv`);
      // =================================================================

      
      const wrapperScript = path.join(repoRoot, 'backend_wrapper.py');
      const args: string[] = [
        wrapperScript,
        // '--backend-root',
        // repoRoot
      ];

      console.log(`Starting NSGA-II Python solver with: ${pythonExe}`);
      console.log(`Solver script: ${wrapperScript}`);
      console.log(`Working directory: ${cwd}`);
      console.log(`Solver args: ${args.join(' ')}`);

      const proc = spawn(pythonExe, args, {
        cwd,
        env: {
          ...process.env,
          PYTHONUTF8: '1',
          PYTHONIOENCODING: 'utf-8',
          PYTHONUNBUFFERED: '1',
        },
      });
      currentProcess = proc;

      // Gửi cấu hình trọng số & yêu cầu đè dữ liệu xuống Python qua stdin
      if (req.body) {
        proc.stdin.write(JSON.stringify(req.body));
        proc.stdin.end();
      }
      // --- HẾT ĐOẠN SỬA 1 ---

      let stdoutBuf = '';
      let stderrBuf = '';

      proc.stdout.on('data', (chunk: Buffer) => {
        const s = chunk.toString();
        stdoutBuf += s;
        // Mirror Python stdout to Node terminal so user can observe solver progress live
        try { console.log('[python stdout]', s); } catch (e) { /* ignore logging errors */ }
      });

      proc.stderr.on('data', (chunk: Buffer) => {
        stderrBuf += chunk.toString();
        console.error('[python stderr]', chunk.toString());
      });

      proc.on('error', (err: any) => {
        currentProcess = null;
        console.error('Python process error:', err);
        res.status(500).json({ success: false, message: String(err) });
      });

      const parseSolverJson = (raw: string) => {
        const trimmed = raw.trim();
        if (!trimmed) return null;

        // Prefer a single-line payload emitted by backend_wrapper.py
        const lines = trimmed.split(/\r?\n/);
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i].trim();
          if (line.startsWith('{') && line.includes('"success"')) {
            try {
              return JSON.parse(line);
            } catch (_) {
              /* try next line */
            }
          }
        }

        try {
          return JSON.parse(trimmed);
        } catch (_) {
          const lastOpen = trimmed.lastIndexOf('{');
          const lastClose = trimmed.lastIndexOf('}');
          if (lastOpen >= 0 && lastClose > lastOpen) {
            const candidate = trimmed.slice(lastOpen, lastClose + 1);
            try {
              return JSON.parse(candidate);
            } catch (__) {
              return null;
            }
          }
          return null;
        }
      };

      proc.on('close', (code: number) => {
        currentProcess = null;
        if (code === 0) {
          // backend_wrapper logs to stderr; JSON may appear on stdout OR stderr (Windows)
          const combined = `${stdoutBuf}\n${stderrBuf}`;
          const parsed: any =
            parseSolverJson(stdoutBuf) ||
            parseSolverJson(stderrBuf) ||
            parseSolverJson(combined);

          // #region agent log
          debugLog('F', 'server.ts:close', 'parsed solver response', {
            stdoutLen: stdoutBuf.length,
            stderrLen: stderrBuf.length,
            parsedSuccess: !!parsed?.success,
            assignmentCount: parsed?.assignments?.length ?? 0,
            hasPenalties: !!parsed?.metrics?.penalties,
            totalPenalty: parsed?.metrics?.totalPenalty ?? null,
            penaltyKeys: parsed?.metrics?.penalties ? Object.keys(parsed.metrics.penalties) : [],
          });
          // #endregion

          if (parsed?.success && Array.isArray(parsed.assignments)) {
            return res.json({
              ...parsed,
              algorithm: parsed.algorithm || 'NSGA-II',
            });
          }

          return res.status(500).json({
            success: false,
            message: 'Solver finished but returned no parseable assignments JSON.',
            algorithm: 'NSGA-II',
            assignments: [],
            metrics: parsed?.metrics ?? {},
            stdoutLen: stdoutBuf.length,
            stderrLen: stderrBuf.length,
          });
        }
        return res.status(500).json({ success: false, message: `Python solver exited with code ${code}`, raw: stdoutBuf, stderr: stderrBuf });
      });
    } catch (err: any) {
      currentProcess = null;
      res.status(500).json({ success: false, message: err.message });
    }
  });


  // =================================================================
  // 🚀 API NHẬN DATA CSV THUẦN TỪ FRONTEND VÀ GHI THÀNH FILE VẬT LÝ
  // =================================================================
  app.post('/api/upload-csv', (req, res) => {
    const { type, filename, text } = req.body;
    console.log(`[api/upload-csv] Nhận yêu cầu lưu file: ${filename} (Loại: ${type})`);

    if (!text) {
      return res.status(400).json({ success: false, message: 'Dữ liệu file trống!' });
    }

    try {
      // Xác định đường dẫn đến thư mục data của Engine Python
      const repoRoot = ENGINE_DIR;
      const dataDir = path.join(repoRoot, 'data');

      // Tự động tạo thư mục 'data' nếu chưa tồn tại
      if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
      }

      // Ép tên file cố định theo chuẩn để Python dễ nạp (hoặc dùng filename tùy chọn)
      const targetFileName = type === 'staff' ? 'can_bo_new.csv' : 'ca_thi_new.csv';
      const targetPath = path.join(dataDir, targetFileName);

      // Ghi file kèm mã hóa BOM UTF-8 để tránh lỗi tiếng Việt có dấu khi Excel/Python đọc
      fs.writeFileSync(targetPath, `\uFEFF${text}`, 'utf-8');
      console.log(`[Node.js] Đã ghi file thành công: ${targetPath}`);

      return res.json({ 
        success: true, 
        message: `Đã lưu file thành công thành ${targetFileName}` 
      });
    } catch (error: any) {
      console.error('[api/upload-csv] Lỗi ghi file:', error);
      return res.status(500).json({ success: false, message: error.message });
    }
  });
  
  //----------------------------------------------------------------------------------



  app.post('/api/solve/stop', async (req, res) => {
    if (!currentProcess) return res.json({ success: false, message: 'No solver running' });
    try {
      currentProcess.kill();
      currentProcess = null;
      return res.json({ success: true, message: 'Solver stopped' });
    } catch (err: any) {
      return res.status(500).json({ success: false, message: err.message });
    }
  });

  // Benchmark API — score latest exported schedule for distribution dashboard
  app.get('/api/benchmark', (_req, res) => {
    try {
      const pythonExe = resolvePythonExe();
      const scriptPath = path.join(BENCHMARK_DIR, 'benchmark_wrapper.py');
      const schedulePath = path.join(ENGINE_DIR, 'outputs', 'Ket_Qua_Xep_Lich.xlsx');
      const staffPath = path.join(ENGINE_DIR, 'data', 'can_bo_new.csv');
      const shiftPath = path.join(ENGINE_DIR, 'data', 'ca_thi_new.csv');

      if (!fs.existsSync(schedulePath)) {
        return res.status(404).json({
          success: false,
          message: 'Chưa có file kết quả. Hãy chạy solver trước.',
        });
      }

      const proc = spawn(pythonExe, [scriptPath], {
        cwd: BENCHMARK_DIR,
        env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' },
      });

      proc.stdin.write(JSON.stringify({ staffPath, shiftPath, schedulePath }));
      proc.stdin.end();

      let stdoutBuf = '';
      let stderrBuf = '';
      proc.stdout.on('data', (chunk: Buffer) => { stdoutBuf += chunk.toString(); });
      proc.stderr.on('data', (chunk: Buffer) => { stderrBuf += chunk.toString(); });

      proc.on('close', (code: number) => {
        if (code !== 0) {
          return res.status(500).json({ success: false, message: 'Benchmark failed', stderr: stderrBuf });
        }
        try {
          const line = stdoutBuf.trim().split(/\r?\n/).pop() || '{}';
          const bench = JSON.parse(line);
          return res.json({
            success: true,
            metrics: {
              penalties: bench.penalties,
              totalPenalty: bench.total_penalty,
              hard: bench.hard,
              soft: bench.soft,
            },
          });
        } catch (err: any) {
          return res.status(500).json({ success: false, message: err.message, raw: stdoutBuf });
        }
      });
    } catch (err: any) {
      return res.status(500).json({ success: false, message: err.message });
    }
  });

  // Export Excel - Chỉ việc lấy file đã tạo gửi về, KHÔNG chạy lại Python
  app.post('/api/export', async (req, res) => {
    try {
      const repoRoot = ENGINE_DIR;
      const outFile = path.join(repoRoot, 'outputs', 'Ket_Qua_Xep_Lich.xlsx');

      if (fs.existsSync(outFile)) {
        return res.download(outFile, 'Ket_Qua_Xep_Lich.xlsx');
      } else {
        return res.status(404).json({
          success: false,
          message: 'Không tìm thấy file kết quả. Vui lòng đảm bảo thuật toán đã chạy xong.',
        });
      }
    } catch (err: any) {
      return res.status(500).json({ success: false, message: err.message });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
