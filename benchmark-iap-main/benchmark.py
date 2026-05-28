import os
import sys
import pandas as pd
import numpy as np
import itertools
from collections import Counter

# =====================
# CẤU HÌNH MẶC ĐỊNH (CLI standalone)
# =====================
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_ENGINE_ROOT = os.path.normpath(os.path.join(_REPO_ROOT, '..', 'exam-scheduling-engine-main NSGA II'))

DEFAULT_STAFF_FILE = os.path.join(_ENGINE_ROOT, 'data', 'can_bo_new.csv')
DEFAULT_SHIFT_FILE = os.path.join(_ENGINE_ROOT, 'data', 'ca_thi_new.csv')
DEFAULT_SCHEDULE_FILE = os.path.join(_ENGINE_ROOT, 'outputs', 'Ket_Qua_Xep_Lich.xlsx')

SCHEDULE_SHEET_NAMES = ['Ca Thi', 'Kết quả phân ca', 'Ket qua phan ca']

WEIGHT_FAIRNESS = 8
WEIGHT_DISTANCE = 0.1
WEIGHT_DISTANCE_FAIRNESS = 0.5
WEIGHT_SAME_DAY_DIFF_FACILITY = 6
WEIGHT_MIN_SHIFT = 5
WEIGHT_AGE_PRIORITY = 3
WEIGHT_PARTNER_DIVERSITY = 0.2
WEIGHT_CONSECUTIVE_SHIFTS = 4
AGE_THRESHOLD = 45
MAX_PARTNER_REPETITION = 2

# =====================
# HÀM TIỆN ÍCH
# =====================
def _read_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        return pd.read_excel(path)
    return pd.read_csv(path, encoding='utf-8-sig')


def _read_schedule(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.xlsx', '.xls'):
        xl = pd.ExcelFile(path)
        for sheet in SCHEDULE_SHEET_NAMES:
            if sheet in xl.sheet_names:
                return pd.read_excel(path, sheet_name=sheet)
        return pd.read_excel(path, sheet_name=xl.sheet_names[0])
    return _read_table(path)


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in normalized:
            return normalized[key]
    for col in df.columns:
        col_lower = str(col).strip().lower()
        for cand in candidates:
            if cand.lower() in col_lower:
                return col
    return None


def _rename_staff_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(col).strip() for col in out.columns]
    mapping = {}
    id_col = _find_col(out, ['MS_CB', 'MS của CÁN BỘ COI THI', 'Mã cán bộ', 'Mã số cán bộ', 'id'])
    if id_col:
        mapping[id_col] = 'MS_CB'
    gender_col = _find_col(out, ['Gioi_Tinh', 'Giới tính', 'gender'])
    if gender_col:
        mapping[gender_col] = 'Gioi_Tinh'
    age_col = _find_col(out, ['Tuoi', 'Tuổi', 'age'])
    if age_col:
        mapping[age_col] = 'Tuoi'
    cs1_col = _find_col(out, ['KC_CS1', 'Khoảng cách đến Cơ sở 1 (km)', 'Khoảng cách đến CS1', 'distCS1'])
    if cs1_col:
        mapping[cs1_col] = 'KC_CS1'
    cs2_col = _find_col(out, ['KC_CS2', 'Khoảng cách đến Cơ sở 2 (km)', 'Khoảng cách đến CS2', 'distCS2'])
    if cs2_col:
        mapping[cs2_col] = 'KC_CS2'
    return out.rename(columns=mapping)


def _rename_shift_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(col).strip() for col in out.columns]
    mapping = {}
    ms_col = _find_col(out, ['MS_CA', 'MS Ca thi', 'Mã ca thi', 'id'])
    if ms_col:
        mapping[ms_col] = 'MS_CA'
    cs_col = _find_col(out, ['Co_So', 'Cơ sở', 'facility'])
    if cs_col:
        mapping[cs_col] = 'Co_So'
    req_col = _find_col(out, ['SL_Yeu_Cau', 'Số lượng cán bộ cần thiết', 'staffRequired'])
    if req_col:
        mapping[req_col] = 'SL_Yeu_Cau'
    date_col = _find_col(out, ['Ngay_Goc', 'Ngày', 'date'])
    if date_col:
        mapping[date_col] = 'Ngay_Goc'
    time_col = _find_col(out, ['Gio_Goc', 'GIỜ', 'time', 'Thời gian'])
    if time_col:
        mapping[time_col] = 'Gio_Goc'
    dow_col = _find_col(out, ['Thu', 'Thứ', 'dayOfWeek'])
    if dow_col:
        mapping[dow_col] = 'Thu'
    return out.rename(columns=mapping)


def _rename_schedule_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(col).strip() for col in out.columns]
    mapping = {}
    ms_col = _find_col(out, ['MS_CA', 'MS Ca thi', 'Mã ca thi'])
    if ms_col:
        mapping[ms_col] = 'MS_CA'
    cs_col = _find_col(out, ['Co_So', 'Cơ sở', 'facility'])
    if cs_col:
        mapping[cs_col] = 'Co_So'
    staff_col = _find_col(out, ['DS_Can_Bo_Raw', 'Danh_sách_CB_Phân_công', 'Danh sach CB Phan cong'])
    if staff_col:
        mapping[staff_col] = 'DS_Can_Bo_Raw'
    time_col = _find_col(out, ['Thoi_Gian_Bat_Dau', 'GIỜ', 'Gio_Goc', 'time'])
    if time_col:
        mapping[time_col] = 'Thoi_Gian_Bat_Dau'
    return out.rename(columns=mapping)


def _to_json_safe(obj):
    """Convert numpy/pandas scalars to native Python types for JSON."""
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return _to_json_safe(obj.tolist())
    return obj


def map_penalties_for_frontend(soft: dict) -> dict:
    """Map benchmark soft scores to dashboard metrics.penalties keys (8 RB mềm)."""
    return {
        'fairness': float(soft.get('RB4_CongBang', {}).get('score', 0) or 0),
        'minShift': float(soft.get('RB5_ItNhat1Ca', {}).get('score', 0) or 0),
        'distance': float(soft.get('RB6_KhoangCach', {}).get('score', 0) or 0),
        'distanceFairness': float(soft.get('RB7_CongBangKhoangCach', {}).get('score', 0) or 0),
        'facilityConflict': float(soft.get('RB8_NhieuCaCungNgayKhacCoSo', {}).get('score', 0) or 0),
        'restGap': float(soft.get('RB9_NghiNgoiChuaDu', {}).get('score', 0) or 0),
        'agePriority': float(soft.get('RB10_UuTienNguoiLonTuoi', {}).get('score', 0) or 0),
        'partnerDiversity': float(soft.get('RB11_DaDangCongSu', {}).get('score', 0) or 0),
    }


def apply_weight_overrides(overrides: dict) -> None:
    """Ghi đè hệ số benchmark từ frontend (SettingsModal)."""
    mapping = {
        'fairnessWeight': 'WEIGHT_FAIRNESS',
        'minShiftWeight': 'WEIGHT_MIN_SHIFT',
        'distanceWeight': 'WEIGHT_DISTANCE',
        'distanceFairnessWeight': 'WEIGHT_DISTANCE_FAIRNESS',
        'sameDayDiffFacilityWeight': 'WEIGHT_SAME_DAY_DIFF_FACILITY',
        'consecutiveShiftsWeight': 'WEIGHT_CONSECUTIVE_SHIFTS',
        'agePriorityWeight': 'WEIGHT_AGE_PRIORITY',
        'partnerDiversityWeight': 'WEIGHT_PARTNER_DIVERSITY',
    }
    module = sys.modules[__name__]
    for ui_key, bench_key in mapping.items():
        if ui_key in overrides:
            setattr(module, bench_key, float(overrides[ui_key]))
def clean_staff_list(staff_str):
    if pd.isna(staff_str):
        return []
    return [cb.strip() for cb in str(staff_str).split(',') if cb.strip()]

def get_distance(row):
    if row['Co_So'] == 'Cơ sở 1': return row['KC_CS1']
    if row['Co_So'] == 'Cơ sở 2': return row['KC_CS2']
    return 0

def load_all_data(
    staff_path: str | None = None,
    shift_path: str | None = None,
    schedule_path: str | None = None,
):
    staff_path = staff_path or DEFAULT_STAFF_FILE
    shift_path = shift_path or DEFAULT_SHIFT_FILE
    schedule_path = schedule_path or DEFAULT_SCHEDULE_FILE

    df_can_bo = _rename_staff_columns(_read_table(staff_path))
    df_ca_thi = _rename_shift_columns(_read_table(shift_path))
    df_lich_truc = _rename_schedule_columns(_read_schedule(schedule_path))

    if 'DS_Can_Bo_Raw' not in df_lich_truc.columns:
        raise ValueError('Schedule file missing staff assignment column (Danh_sách_CB_Phân_công)')

    df_lich_truc['DS_Can_Bo'] = df_lich_truc['DS_Can_Bo_Raw'].apply(clean_staff_list)
    cols_to_keep = ['MS_CA', 'Co_So', 'DS_Can_Bo']
    if 'Thoi_Gian_Bat_Dau' in df_lich_truc.columns:
        cols_to_keep.append('Thoi_Gian_Bat_Dau')
    df_lich_truc_clean = df_lich_truc[cols_to_keep].copy()
    df_merged_lich = pd.merge(df_lich_truc_clean, df_ca_thi, on=['MS_CA', 'Co_So'], how='left')

    if 'Thoi_diem_bat_dau' not in df_merged_lich.columns:
        if 'Ngay_Goc' in df_merged_lich.columns and 'Gio_Goc' in df_merged_lich.columns:
            df_merged_lich['Thoi_diem_bat_dau'] = (
                df_merged_lich['Ngay_Goc'].astype(str) + ' ' + df_merged_lich['Gio_Goc'].astype(str)
            )
        elif 'Thoi_Gian_Bat_Dau' in df_merged_lich.columns:
            df_merged_lich['Thoi_diem_bat_dau'] = df_merged_lich['Thoi_Gian_Bat_Dau']

    return df_can_bo, df_ca_thi, df_merged_lich

# =====================
# ĐÁNH GIÁ RÀNG BUỘC
# =====================
def evaluate_hard_constraints(df_lich_truc):
    report = {
        'RB1_TrungThoiGian': {'pass': True, 'violations': 0, 'details': []},
        'RB2_DuGiamThi': {'pass': True, 'violations': 0, 'details': []},
        'RB3_LienTiepKhacCoSo': {'pass': True, 'violations': 0, 'details': []}
    }
    grouped_time = df_lich_truc.dropna(subset=['Thoi_diem_bat_dau']).groupby('Thoi_diem_bat_dau')
    for time, group in grouped_time:
        if len(group) > 1:
            shift_pairs = itertools.combinations(group.to_dict('records'), 2)
            for shift1, shift2 in shift_pairs:
                overlap = set(shift1['DS_Can_Bo']).intersection(set(shift2['DS_Can_Bo']))
                if overlap:
                    report['RB1_TrungThoiGian']['pass'] = False
                    report['RB1_TrungThoiGian']['violations'] += len(overlap)
                    try:
                        time_str = time.strftime('%H:%M %d/%m/%Y')
                    except:
                        time_str = str(time)
                    for cb in overlap:
                        report['RB1_TrungThoiGian']['details'].append(
                            f"Cán bộ {cb} bị xếp trùng lịch lúc {time_str}: Ca {shift1['MS_CA']} ({shift1['Co_So']}) VÀ Ca {shift2['MS_CA']} ({shift2['Co_So']})"
                        )
    for _, row in df_lich_truc.iterrows():
        actual_count = len(row['DS_Can_Bo'])
        required_count = row['SL_Yeu_Cau']
        if pd.isna(required_count):
            continue
        if actual_count != required_count:
            report['RB2_DuGiamThi']['pass'] = False
            report['RB2_DuGiamThi']['violations'] += 1
            try:
                date_str = pd.to_datetime(row['Ngay_Goc']).strftime('%d/%m/%Y')
            except:
                date_str = str(row['Ngay_Goc'])
            report['RB2_DuGiamThi']['details'].append(
                f"Ca thi {row['MS_CA']} tại {row['Co_So']} (Ngày {date_str}): Yêu cầu {int(required_count)} người, nhưng thực tế đang xếp {actual_count} người."
            )
    df_flat = df_lich_truc.explode('DS_Can_Bo').rename(columns={'DS_Can_Bo': 'MS_CB'})
    df_flat = df_flat.dropna(subset=['MS_CB', 'Ngay_Goc', 'MS_CA'])
    def get_shift_number(ms_ca):
        try:
            # Giả sử định dạng là "Ngay_Ca_1" hoặc "Ca_1" -> lấy số 1
            return int(str(ms_ca).split('_')[-1])
        except:
            return 0

    df_flat['Ca_Thu'] = df_flat['MS_CA'].apply(get_shift_number)
    # Sắp xếp đúng thứ tự: Cán bộ -> Ngày -> Ca thi
    df_flat = df_flat.sort_values(by=['MS_CB', 'Ngay_Goc', 'Ca_Thu'])
    
    grouped_daily_staff = df_flat.groupby(['MS_CB', 'Ngay_Goc'])
    
    for (cb, date), group in grouped_daily_staff:
        if len(group) > 1:
            co_so_list = group['Co_So'].tolist()
            ca_thu_list = group['Ca_Thu'].tolist() # Lấy thêm danh sách số thứ tự ca
            
            for i in range(1, len(co_so_list)):
                # ĐIỀU KIỆN MỚI: 
                # 1. Hiệu số ca phải bằng 1 (liên tiếp nhau)
                # 2. Cơ sở phải khác nhau
                khoang_cach_ca = ca_thu_list[i] - ca_thu_list[i-1]
                
                if khoang_cach_ca == 1 and co_so_list[i] != co_so_list[i-1]:
                    report['RB3_LienTiepKhacCoSo']['pass'] = False
                    report['RB3_LienTiepKhacCoSo']['violations'] += 1
                    report['RB3_LienTiepKhacCoSo']['details'].append(
                        f"Cán bộ {cb} gác 2 ca LIÊN TIẾP ({ca_thu_list[i-1]} & {ca_thu_list[i]}) "
                        f"tại 2 cơ sở khác nhau trong ngày {date}"
                    )
    return report

def calculate_distance_fairness_score(df_can_bo, df_flat):
    def get_distance(row):
        if row['Co_So'] == 'Cơ sở 1': return row['KC_CS1']
        if row['Co_So'] == 'Cơ sở 2': return row['KC_CS2']
        return 0
    if 'Khoang_Cach_Ca' not in df_flat.columns:
        df_flat['Khoang_Cach_Ca'] = df_flat.apply(get_distance, axis=1)
    distance_by_staff = df_flat.groupby('MS_CB')['Khoang_Cach_Ca'].sum()
    all_staff_distance = distance_by_staff.reindex(df_can_bo['MS_CB'], fill_value=0)
    mu_distance = all_staff_distance.sum() / len(df_can_bo) if len(df_can_bo) > 0 else 0
    total_distance_deviation = abs(all_staff_distance - mu_distance).sum()
    penalty_score = total_distance_deviation * WEIGHT_DISTANCE_FAIRNESS
    total_distance_all = all_staff_distance.sum()
    report = {
        'penalty': round(penalty_score, 2),
        'total_deviation': round(total_distance_deviation, 2),
        'mu_distance': round(mu_distance, 2),
        'total_distance': round(total_distance_all, 2),
        'staff_distances': {cb_id: round(dist, 2) for cb_id, dist in all_staff_distance.items()},
        'details': f"Tổng độ lệch khoảng cách: {round(total_distance_deviation, 2)} km. Trung bình khoảng cách (mu): {round(mu_distance, 2)} km"
    }
    return penalty_score, report

def evaluate_soft_constraints(df_can_bo, df_lich_truc):
    report = {}
    total_penalty = 0
    df_flat = df_lich_truc.explode('DS_Can_Bo').rename(columns={'DS_Can_Bo': 'MS_CB'})
    df_flat = df_flat.dropna(subset=['MS_CB'])
    df_flat = pd.merge(df_flat, df_can_bo, on='MS_CB', how='left')
    shift_counts = df_flat['MS_CB'].value_counts()
    total_shifts = len(df_flat)
    total_staff = len(df_can_bo)
    mu = total_shifts / total_staff if total_staff > 0 else 0
    all_shift_counts = shift_counts.reindex(df_can_bo['MS_CB'], fill_value=0)
    total_deviation = abs(all_shift_counts - mu).sum()
    penalty_rb4 = total_deviation * WEIGHT_FAIRNESS
    total_penalty += penalty_rb4
    report['RB4_CongBang'] = {
        'score': round(penalty_rb4, 2), 
        'details': f"Tổng độ lệch: {round(total_deviation, 2)} ca (Trung bình mu = {round(mu, 2)})"
    }
    staff_with_zero_shifts = (all_shift_counts == 0).sum()
    penalty_rb5 = staff_with_zero_shifts * WEIGHT_MIN_SHIFT
    total_penalty += penalty_rb5
    report['RB5_ItNhat1Ca'] = {
        'score': penalty_rb5,
        'details': f"Có {staff_with_zero_shifts} cán bộ không được phân công ca nào."
    }
    df_flat['Khoang_Cach_Ca'] = df_flat.apply(get_distance, axis=1)
    total_distance = df_flat['Khoang_Cach_Ca'].sum()
    penalty_rb6 = total_distance * WEIGHT_DISTANCE
    total_penalty += penalty_rb6
    report['RB6_KhoangCach'] = {
        'score': round(penalty_rb6, 2),
        'details': f"Tổng quãng đường di chuyển: {round(total_distance, 2)} km."
    }
    penalty_rb7, rb7_report = calculate_distance_fairness_score(df_can_bo, df_flat)
    total_penalty += penalty_rb7
    report['RB7_CongBangKhoangCach'] = {
        'score': rb7_report['penalty'],
        'details': rb7_report['details']
    }
    penalty_rb8 = 0
    rb8_violations = 0
    grouped_daily = df_flat.groupby(['MS_CB', 'Ngay_Goc'])
    for (cb, date), group in grouped_daily:
        if len(group) >= 2:
            unique_facilities = group['Co_So'].nunique()
            if unique_facilities > 1:
                rb8_violations += 1
                penalty_rb8 += WEIGHT_SAME_DAY_DIFF_FACILITY
    total_penalty += penalty_rb8
    report['RB8_NhieuCaCungNgayKhacCoSo'] = {
        'score': penalty_rb8,
        'details': f"Vi phạm {rb8_violations} lần (gác >= 2 ca/ngày nhưng phải chạy khác cơ sở)."
    }
    penalty_rb9 = 0
    rb9_violations = 0
    df_sorted = df_flat.sort_values(by=['MS_CB', 'Ngay_Goc', 'MS_CA'])
    grouped_sorted = df_sorted.groupby(['MS_CB', 'Ngay_Goc'])
    for (cb, date), group in grouped_sorted:
        if len(group) >= 2:
            suffix_array = pd.to_numeric(group['MS_CA'].str.split('_').str[-1], errors='coerce').values
            for i in range(1, len(suffix_array)):
                prev_end = suffix_array[i-1]
                curr_start = suffix_array[i]
                if pd.notna(prev_end) and pd.notna(curr_start):
                    if (curr_start - prev_end) == 1:
                        rb9_violations += 1
                        penalty_rb9 += WEIGHT_CONSECUTIVE_SHIFTS
    total_penalty += penalty_rb9
    report['RB9_NghiNgoiChuaDu'] = {
        'score': penalty_rb9,
        'details': f"Vi phạm {rb9_violations} lần trực 2 ca liên tiếp."
    }
    penalty_age = 0
    age_violations = 0
    for cb_row in df_can_bo.to_dict('records'):
        if cb_row['Tuoi'] > AGE_THRESHOLD:
            cb_id = cb_row['MS_CB']
            ca_thuc_te = all_shift_counts.get(cb_id, 0)
            if ca_thuc_te > mu:
                extra_shifts = ca_thuc_te - mu
                age_violations += 1
                penalty_age += extra_shifts * WEIGHT_AGE_PRIORITY
    total_penalty += penalty_age
    report['RB10_UuTienNguoiLonTuoi'] = {
        'score': round(penalty_age, 2),
        'details': f"Có {age_violations} cán bộ >{AGE_THRESHOLD}t bị xếp quá số ca trần."
    }
    all_pairs = []
    for ds in df_lich_truc['DS_Can_Bo']:
        if len(ds) >= 2:
            sorted_ds = sorted(ds)
            all_pairs.extend(itertools.combinations(sorted_ds, 2))
    pair_counts = Counter(all_pairs)
    frequent_pairs = {pair: count for pair, count in pair_counts.items() if count >= MAX_PARTNER_REPETITION}
    rb11_violations = len(frequent_pairs)
    penalty_rb11 = rb11_violations * WEIGHT_PARTNER_DIVERSITY
    total_penalty += penalty_rb11
    report['RB11_DaDangCongSu'] = {
        'score': penalty_rb11,
        'details': f"Có {rb11_violations} cặp đôi phải gác chung với nhau >= {MAX_PARTNER_REPETITION} lần."
    }
    return total_penalty, report

# =====================
# API TÍNH METRIC
# =====================
def benchmark_metrics(
    staff_path: str | None = None,
    shift_path: str | None = None,
    schedule_path: str | None = None,
    weight_overrides: dict | None = None,
):
    if weight_overrides:
        apply_weight_overrides(weight_overrides)
    df_can_bo, df_ca_thi, df_lich_truc = load_all_data(staff_path, shift_path, schedule_path)
    hard = evaluate_hard_constraints(df_lich_truc)
    total_penalty, soft = evaluate_soft_constraints(df_can_bo, df_lich_truc)
    return _to_json_safe({
        'hard': hard,
        'soft': soft,
        'total_penalty': float(total_penalty),
        'penalties': map_penalties_for_frontend(soft),
    })

if __name__ == "__main__":
    result = benchmark_metrics()
    print(result)
