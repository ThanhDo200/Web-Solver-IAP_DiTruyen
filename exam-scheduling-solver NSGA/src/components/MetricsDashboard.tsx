import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  Legend,
  ComposedChart,
  Line,
  ReferenceLine
} from 'recharts';
import { ShieldCheck, TrendingUp, Award, BarChartHorizontal } from "lucide-react";
import type { Staff, Shift } from "@/lib/mock-data";
import {
  assignmentSlotKey,
  extractFacilityFromAssignmentShiftId,
  findShiftBySlot,
  normalizeFacility,
} from "@/lib/shift-utils";
import { SOFT_CONSTRAINTS } from "@/lib/soft-constraints";

// =========================================================================
// 📊 BIỂU ĐỒ 1: WORKLOAD CHART (HIỂN THỊ Ở CỘT TRÁI RỘNG)
// =========================================================================
interface WorkloadChartProps {
  hasResults: boolean;
  isSolverRunning?: boolean;
  metrics: any;
  assignments: any[];
  staff: Staff[];
}

export function WorkloadChart({ hasResults, isSolverRunning = false, metrics, assignments, staff }: WorkloadChartProps) {
  const showChart = staff.length > 0 && (hasResults || isSolverRunning);
  // Bộ đếm số ca theo từng cơ sở cho cán bộ (Hỗ trợ định dạng chuỗi gộp và đơn lẻ)
  const shiftsPerStaffPerFacility = staff.reduce<Record<string, { cs1: number; cs2: number; total: number }>>((acc, s) => {
    acc[s.id] = { cs1: 0, cs2: 0, total: 0 };
    return acc;
  }, {});

  assignments.forEach(item => {
    if (!item.shiftId || !item.staffIds) return;
    
    // Phân tách chuỗi gộp (phòng hờ dữ liệu benchmark ngăn cách bởi dấu chấm phẩy)
    const shiftParts = item.shiftId.split(';').map((p: string) => p.trim()).filter(Boolean);
    
    item.staffIds.forEach((id: string) => {
      if (!shiftsPerStaffPerFacility[id]) {
        shiftsPerStaffPerFacility[id] = { cs1: 0, cs2: 0, total: 0 };
      }
      
      shiftParts.forEach((part: string) => {
        shiftsPerStaffPerFacility[id].total += 1;
        
        if (part.includes('Cơ sở 1') || part.includes('CS1') || part.includes('cs1')) {
          shiftsPerStaffPerFacility[id].cs1 += 1;
        } else if (part.includes('Cơ sở 2') || part.includes('CS2') || part.includes('cs2')) {
          shiftsPerStaffPerFacility[id].cs2 += 1;
        }
      });
    });
  });

  // Mảng dữ liệu phân tải công việc kết hợp khoảng cách địa lý (km)
  const workloadData = staff.map(s => {
    const data = shiftsPerStaffPerFacility[s.id] || { cs1: 0, cs2: 0, total: 0 };
    const travelDistance = (s.distCS1 * data.cs1) + (s.distCS2 * data.cs2);
    
    return { 
      name: s.id, 
      shifts: data.total, 
      travelDistance: Math.round(travelDistance * 10) / 10,
      fullName: s.name 
    };
  });

  // Ngưỡng ca gác lý tưởng dựa trên trung bình thực tế
  const averageShifts = metrics?.avg_shifts_per_staff || metrics?.avgShifts || 
    (workloadData.reduce((sum, row) => sum + row.shifts, 0) / Math.max(workloadData.length, 1));
  const idealMin = Math.max(0, Math.round(averageShifts - 1));
  const idealMax = Math.round(averageShifts + 1);

  const averageTravelDistance = workloadData.length > 0 
    ? Math.round((workloadData.reduce((sum, row) => sum + row.travelDistance, 0) / workloadData.length) * 10) / 10
    : 0;

  return (
    <Card className="border-slate-200 shadow-sm bg-white">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-slate-500 uppercase tracking-tight flex items-center gap-2">
            <BarChartHorizontal size={14} className="text-blue-600" />
            Comprehensive Assignee Workload
          </CardTitle>
          {hasResults && <Award size={16} className="text-amber-500 animate-bounce" />}
        </div>
        <CardDescription className="text-[10px]">Total shifts (Left Axis) and cumulative travel distance (Right Axis) mapped per invigilator across the term.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full mt-4">
          {!showChart ? (
            <div className="h-full flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-200 text-slate-400 text-xs italic">
              Awaiting solver execution for workload mapping
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={workloadData} margin={{ top: 10, right: 10, left: -30, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 6, fill: '#94a3b8' }} 
                  interval={0}
                    
                  angle={-90}        
                  textAnchor="end"   
                  height={45}   
                />
                <YAxis 
                  yAxisId="left"
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 9, fill: '#94a3b8' }} 
                  label={{ value: 'Shifts Assigned', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 9, fill: '#64748b', fontWeight: 600 } }}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 9, fill: '#94a3b8' }} 
                  label={{ value: 'Travel Distance (km)', angle: 90, position: 'insideRight', offset: -5, style: { fontSize: 9, fill: '#8b5cf6', fontWeight: 600 } }}
                />
                <Tooltip 
                  cursor={{ fill: '#f8fafc' }} 
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', fontSize: '11px' }}
                  labelClassName="font-bold text-slate-900"
                />
                <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '15px' }} />
                <Bar yAxisId="left" dataKey="shifts" fill="#3b82f6" radius={[2, 2, 0, 0]} name="Shifts Count">
                  {workloadData.map((entry: any, index: number) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.shifts > idealMax ? '#ef4444' : entry.shifts < idealMin ? '#f59e0b' : '#3b82f6'} 
                      fillOpacity={0.85}
                    />
                  ))}
                </Bar>
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="travelDistance" 
                  stroke="#8b5cf6" 
                  strokeWidth={2.5}
                  dot={{ r: 1, strokeWidth: 1 }}
                  name="Total Distance (km)"
                />
                <ReferenceLine 
                  yAxisId="right"
                  y={averageTravelDistance}
                  stroke="#10b981"
                  strokeDasharray="4 4"
                  label={{ value: `Avg: ${averageTravelDistance} km`, position: 'insideTopRight', fill: '#10b981', fontSize: 9, fontWeight: 600 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
        {showChart && (
          <div className="mt-3 flex flex-wrap items-center justify-center text-[9px] font-bold uppercase tracking-wider gap-4 border-t border-slate-50 pt-3">
            <div className="flex items-center gap-1.5">
               <div className="w-2.5 h-2.5 rounded bg-blue-500 opacity-80" />
               <span className="text-slate-500">Ideal Workload ({idealMin}-{idealMax} ca)</span>
            </div>
            <div className="flex items-center gap-1.5">
               <div className="w-2.5 h-2.5 rounded bg-amber-500 opacity-80" />
               <span className="text-slate-500">Underloaded ca</span>
            </div>
            <div className="flex items-center gap-1.5">
               <div className="w-2.5 h-2.5 rounded bg-red-500 opacity-80" />
               <span className="text-slate-500">Overloaded ca</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =========================================================================
// 📈 BIỂU ĐỒ 2: PERFORMANCE METRICS & COMPLIANCE STATUS (CỘT PHẢI GỌN)
// =========================================================================
interface PerformanceMetricsProps {
  hasResults: boolean;
  metrics: any;
  assignments: any[];
  shifts: Shift[];
}

function normalizeDate(rawDate: string) {
  if (!rawDate) return '';
  const trimmed = rawDate.trim();
  const dmy = trimmed.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (dmy) return `${dmy[3]}-${dmy[2]}-${dmy[1]}`;
  const iso = trimmed.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const ymd = trimmed.match(/(\d{4})(\d{2})(\d{2})/);
  if (ymd) return `${ymd[1]}-${ymd[2]}-${ymd[3]}`;
  return trimmed;
}

function extractFacility(shiftId: string) {
  return extractFacilityFromAssignmentShiftId(shiftId);
}

function extractSessionKey(shiftId: string) {
  const cleaned = shiftId.replace(/\((Cơ sở [12]|CS[12])\)/i, '').trim();
  const parts = cleaned.split(' - ').map(part => part.trim()).filter(Boolean);
  if (parts.length <= 1) return cleaned;
  return parts.slice(1).join(' - ');
}

function parseAssignmentShift(shiftId: string) {
  const dateMatch = shiftId.match(/(\d{2}\/\d{2}\/\d{4})|(?:\d{4}-\d{2}-\d{2})|(?:\d{8})/);
  const rawDate = dateMatch?.[0] ?? '';
  return {
    facility: extractFacility(shiftId),
    date: normalizeDate(rawDate),
    sessionKey: extractSessionKey(shiftId),
  };
}

function findMatchingShift(shiftId: string, shifts: Shift[]) {
  const slot = assignmentSlotKey(shiftId);
  if (slot) {
    const exact = findShiftBySlot(shifts, slot.id, slot.facility);
    if (exact) return exact;
  }

  const normalizedAssignment = parseAssignmentShift(shiftId);
  const normalizedDate = normalizedAssignment.date;
  const normalizedFacility = normalizeFacility(normalizedAssignment.facility);
  const normalizedSession = normalizedAssignment.sessionKey.toLowerCase();

  return shifts.find((shift) => {
    const shiftDate = normalizeDate(shift.date || '');
    const shiftFacility = normalizeFacility(shift.facility || '');
    if (normalizedDate && shiftDate && normalizedDate !== shiftDate) return false;
    if (normalizedFacility && shiftFacility && normalizedFacility !== shiftFacility) return false;

    const shiftName = `${shift.name || ''} ${shift.time || ''}`.toLowerCase();
    if (normalizedSession && shiftName.includes(normalizedSession)) return true;
    return false;
  });
}

export function PerformanceMetrics({ hasResults, metrics, assignments, shifts }: PerformanceMetricsProps) {
  const parsedAssignments = assignments.map((assignment) => {
    const parsed = parseAssignmentShift(assignment.shiftId || '');
    return {
      ...assignment,
      facility: parsed.facility,
      date: parsed.date,
      sessionKey: parsed.sessionKey,
      matchedShift: findMatchingShift(assignment.shiftId || '', shifts),
    };
  });

  // 8 ràng buộc mềm benchmark (RB4–RB11)
  const penaltyDistributionData = SOFT_CONSTRAINTS.map((c) => ({
    name: c.label,
    penalty: metrics?.penalties?.[c.key] ?? 0,
    fill: c.fill,
  }));

  // Sort from smallest to largest penalty so chart displays ascending order
  penaltyDistributionData.sort((a, b) => (a.penalty || 0) - (b.penalty || 0));

  const totalPenalty = penaltyDistributionData.reduce((sum, item) => sum + (item.penalty || 0), 0);

  // Note: Local compliance checking removed - now using backend's hard constraint verification
  // The backend has already validated all hard constraints during optimization
  
  const hardConstraintStatus = metrics?.hard;
  
  // If all hard constraints pass, everything is good
  const allHardConstraintPass = hardConstraintStatus && 
    Object.values(hardConstraintStatus).every((c: any) => c?.pass === true);
  
  // Map hard constraint status to single compliance indicator
  const overallHardConstraintStatus: 'green' | 'amber' | 'red' | 'gray' = !hasResults
    ? 'gray'
    : allHardConstraintPass
      ? 'green'
      : 'red';

  // All three compliance indicators show same status since they're all hard constraints
  // that are verified together by the backend
  const facilityStatus = overallHardConstraintStatus;
  const exactCountStatus = overallHardConstraintStatus;
  const duplicateSessionStatus = overallHardConstraintStatus;

  return (
    <div className="space-y-8">
      {/* Khối biểu đồ điểm phạt thành phần */}
      <Card className="border-slate-200 shadow-sm bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-slate-500 uppercase tracking-tight flex items-center gap-2">
            <TrendingUp size={14} className="text-violet-600" />
            Soft Constraint Penalty Distribution
          </CardTitle>
          <CardDescription className="text-[10px]">Breakdown of penalty points calculated from the benchmark scoring matrix (Lower values mean higher quality).</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4 mb-4 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <div className="font-semibold">Total Penalty</div>
            <div className="text-slate-900 font-bold">{totalPenalty.toFixed(1)}</div>
          </div>
          <div className="h-[240px] w-full mt-2">
            {!hasResults ? (
               <div className="h-full flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-200 text-slate-400 text-xs italic">
                Solve to populate penalty matrix distribution
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={penaltyDistributionData} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 9, fill: '#475569', fontWeight: 600 }} 
                    width={110}
                  />
                  <Tooltip 
                    cursor={{ fill: '#f1f5f9', opacity: 0.4 }}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', fontSize: '11px' }}
                  />
                  <Bar dataKey="penalty" name="Điểm phạt" radius={[0, 4, 4, 0]} barSize={10}>
                    {penaltyDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Khối đèn tín hiệu luật cứng/mềm */}
      <Card className="border-slate-200 shadow-sm bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold text-slate-500 uppercase tracking-tight flex items-center gap-2">
            <ShieldCheck size={14} className="text-emerald-600" />
            Compliance Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ComplianceRow label="Facility Constraints (Ràng buộc Cơ sở)" status={facilityStatus} />
          <ComplianceRow label="Đảm bảo số lượng cán bộ chính xác cho mỗi ca thi" status={exactCountStatus} />
          <ComplianceRow label="Không gán một cán bộ vào hai ca cùng MS Ca thi" status={duplicateSessionStatus} />
        </CardContent>
      </Card>
    </div>
  );
}

// =========================================================================
// 🟢 ĐÈN TÍN HIỆU TRAFFIC LIGHTS (HÀM HELPER ĐỂ HIỂN THỊ STATUS)
// =========================================================================
function ComplianceRow({ label, status }: { label: string, status: 'green' | 'amber' | 'red' | 'gray' }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-50 pb-2 last:border-none last:pb-0">
      <span className="text-xs font-semibold text-slate-600 font-mono tracking-tight">{label}</span>
      <div className="flex gap-1.5 p-1 bg-slate-50 rounded-full">
        <TrafficLight color={status} />
      </div>
    </div>
  );
}

function TrafficLight({ color }: { color: 'green' | 'amber' | 'red' | 'gray' }) {
  const colors = {
    green: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]',
    amber: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]',
    red: 'bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]',
    gray: 'bg-slate-300'
  };
  return <div className={`w-2 h-2 rounded-full ${colors[color]}`} />;
}
