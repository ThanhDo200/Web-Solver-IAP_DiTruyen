/** 8 ràng buộc mềm benchmark (RB4–RB11) — dùng chung Settings + Distribution chart */
export const SOFT_CONSTRAINTS = [
  {
    key: 'fairness',
    configKey: 'fairnessWeight',
    benchmarkKey: 'RB4_CongBang',
    label: 'fairness schedule',
    description: 'Công bằng số ca trực (RB4)',
    defaultWeight: 8,
    fill: '#8b5cf6',
  },
  {
    key: 'minShift',
    configKey: 'minShiftWeight',
    benchmarkKey: 'RB5_ItNhat1Ca',
    label: 'min shift',
    description: 'Mỗi cán bộ có ít nhất 1 ca (RB5)',
    defaultWeight: 5,
    fill: '#ef4444',
  },
  {
    key: 'distance',
    configKey: 'distanceWeight',
    benchmarkKey: 'RB6_KhoangCach',
    label: 'distance',
    description: 'Tổng quãng đường di chuyển (RB6)',
    defaultWeight: 0.1,
    fill: '#60a5fa',
  },
  {
    key: 'distanceFairness',
    configKey: 'distanceFairnessWeight',
    benchmarkKey: 'RB7_CongBangKhoangCach',
    label: 'distance fairness',
    description: 'Công bằng khoảng cách (RB7)',
    defaultWeight: 0.5,
    fill: '#06b6d4',
  },
  {
    key: 'facilityConflict',
    configKey: 'sameDayDiffFacilityWeight',
    benchmarkKey: 'RB8_NhieuCaCungNgayKhacCoSo',
    label: 'different facility daily',
    description: 'Nhiều ca/ngày khác cơ sở (RB8)',
    defaultWeight: 6,
    fill: '#3b82f6',
  },
  {
    key: 'restGap',
    configKey: 'consecutiveShiftsWeight',
    benchmarkKey: 'RB9_NghiNgoiChuaDu',
    label: 'insufficient rest',
    description: 'Ca liên tiếp chưa đủ nghỉ (RB9)',
    defaultWeight: 4,
    fill: '#f59e0b',
  },
  {
    key: 'agePriority',
    configKey: 'agePriorityWeight',
    benchmarkKey: 'RB10_UuTienNguoiLonTuoi',
    label: 'age priority',
    description: 'Ưu tiên người lớn tuổi (RB10)',
    defaultWeight: 3,
    fill: '#64748b',
  },
  {
    key: 'partnerDiversity',
    configKey: 'partnerDiversityWeight',
    benchmarkKey: 'RB11_DaDangCongSu',
    label: 'partner diversity',
    description: 'Đa dạng cặp gác chung (RB11)',
    defaultWeight: 0.2,
    fill: '#a855f7',
  },
] as const;

export type SoftConstraintKey = (typeof SOFT_CONSTRAINTS)[number]['key'];
export type SoftConstraintConfigKey = (typeof SOFT_CONSTRAINTS)[number]['configKey'];

export type SoftConstraintWeights = Record<SoftConstraintConfigKey, number>;

export function defaultSoftConstraintWeights(): SoftConstraintWeights {
  return Object.fromEntries(
    SOFT_CONSTRAINTS.map((c) => [c.configKey, c.defaultWeight])
  ) as SoftConstraintWeights;
}

export function buildSolverConfig(weights: SoftConstraintWeights) {
  return { ...weights };
}
