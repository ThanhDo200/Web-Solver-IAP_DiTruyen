
# """
# backend_wrapper.py
# ==================
# Wrapper tự động nhận diện thư mục chạy giải thuật NSGA-II 
# và cập nhật cấu hình dữ liệu mới từ Frontend, sử dụng tên cột đồng bộ rút gọn.
# """
# import sys
# import os
# import json
# import pandas as pd
# from collections import defaultdict

# def main():
#     # 1. TỰ ĐỘNG XÁC ĐỊNH THƯ MỤC BACKEND NGAY TẠI VỊ TRÍ FILE NÀY
#     CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
#     backend_root = CURRENT_DIR

#     # Add backend root to Python path so we can import 'config' and 'src'
#     if backend_root not in sys.path:
#         sys.path.insert(0, backend_root)

#     print(f"[WRAPPER] Thư mục hoạt động backend: {backend_root}")

#     # Read JSON overrides from stdin (if any)
#     stdin_data = ''
#     try:
#         stdin_data = sys.stdin.read()
#     except Exception:
#         stdin_data = ''

#     overrides = {}
#     if stdin_data and stdin_data.strip():
#         try:
#             overrides = json.loads(stdin_data)
#         except Exception as e:
#             print(f"[wrapper] Failed to parse JSON from stdin: {e}", file=sys.stderr)

#     # Safely import the backend config module
#     try:
#         import config
#     except ImportError as e:
#         print(f"[wrapper] Failed to import 'config' from backend-root '{backend_root}': {e}", file=sys.stderr)
#         sys.exit(10)

#     # ==========================================================================
#     # CƠ CHẾ ÉP BUỘC TỰ ĐỘNG: ƯU TIÊN FILE DỮ LIỆU MỚI DO FRONTEND IMPORT
#     # ==========================================================================
#     NEW_STAFF = os.path.join(config.DATA_DIR, "can_bo_new.csv")
#     NEW_SHIFT = os.path.join(config.DATA_DIR, "ca_thi_new.csv")
    
#     if os.path.exists(NEW_STAFF):
#         config.INPUT_STAFF_FILE = NEW_STAFF
#         print(f"[wrapper - FORCE] Đã phát hiện và ép nạp file cán bộ mới: {NEW_STAFF}")
#     else:
#         print(f"[wrapper - INFO] Sử dụng file cán bộ mặc định: {config.INPUT_STAFF_FILE}")
        
#     if os.path.exists(NEW_SHIFT):
#         config.INPUT_SHIFT_FILE = NEW_SHIFT
#         print(f"[wrapper - FORCE] Đã phát hiện và ép nạp file ca thi mới: {NEW_SHIFT}")
#     else:
#         print(f"[wrapper - INFO] Sử dụng file ca thi mặc định: {config.INPUT_SHIFT_FILE}")
#     # ==========================================================================

#     # Xử lý các tham số cấu hình khác từ frontend (UI config gửi xuống nếu có)
#     if "config" in overrides:
#         ui_config = overrides["config"]
#         # Ánh xạ trọng số từ Frontend UI xuống biến nội bộ của file config.py của Python
#         mapping = {
#             "fairnessWeight": "WEIGHT_FAIRNESS",
#             "distanceWeight": "WEIGHT_DISTANCE",
#             "genderWeight": "WEIGHT_GENDER",
#             "ageWeight": "WEIGHT_AGE",
#             "closeShiftWeight": "WEIGHT_CLOSE_SHIFT",
#             "sameDayDiffFacilityWeight": "WEIGHT_SAME_DAY_DIFF_FACILITY",
#             "minShiftWeight": "WEIGHT_MIN_SHIFT",
#             "weekendWeight": "WEIGHT_WEEKEND"
#         }
#         for ui_key, backend_key in mapping.items():
#             if ui_key in ui_config:
#                 try:
#                     setattr(config, backend_key, float(ui_config[ui_key]))
#                     print(f"[wrapper] Overrode config.{backend_key} = {ui_config[ui_key]}")
#                 except Exception as e:
#                     print(f"[wrapper] Failed to set config.{backend_key}: {e}", file=sys.stderr)

#     # Now import backend modules and execute main flow
#     try:
#         from src.loader import load_data
#         from src.model import run_nsga2_scheduler
#         from src.exporter import export_results
#     except Exception as e:
#         print(f"[wrapper] Failed to import backend modules: {e}", file=sys.stderr)
#         raise

#     print("=" * 60)
#     print("[WRAPPER] Running backend with runtime config overrides")
#     print("=" * 60)
#     print(f"[wrapper] Using INPUT_SHIFT_FILE={config.INPUT_SHIFT_FILE}")
#     print(f"[wrapper] Using INPUT_STAFF_FILE={config.INPUT_STAFF_FILE}")

#     try:
#         # Load data from the paths specified in config (dynamically adjusted above)
#         shift_df, staff_df = load_data(config.INPUT_SHIFT_FILE, config.INPUT_STAFF_FILE)
        
#         # Execute NSGA-II core optimization algorithm
#         print(f"[wrapper] shift_df columns: {list(shift_df.columns)}")
#         print(f"[wrapper] staff_df columns: {list(staff_df.columns)}")
#         best_assignments, flattened_slots = run_nsga2_scheduler(shift_df, staff_df)
        
#         # Export the final optimal schedule to the output Excel file
#         export_results(best_assignments, flattened_slots, staff_df, config.OUTPUT_SCHEDULE_FILE)

#         # 🌟 ĐÓNG GÓI JSON SỬ DỤNG TÊN CỘT ĐỒNG BỘ GỌN GÀNG ĐỂ TRẢ VỀ CHO FRONTEND
#         staff_ids = staff_df['Mã cán bộ'].astype(str).tolist()
        
#         if pd.api.types.is_datetime64_any_dtype(flattened_slots['Ngày']):
#             date_strings = flattened_slots['Ngày'].dt.strftime('%d/%m/%Y').astype(str).tolist()
#         else:
#             date_strings = flattened_slots['Ngày'].astype(str).tolist()
            
#         ca_strings = flattened_slots['Ca thi'].astype(str).tolist()
#         cs_strings = flattened_slots['Cơ sở'].astype(str).tolist()

#         assignment_map = defaultdict(list)
#         for slot_index, staff_index in enumerate(best_assignments):
#             # Tái tạo chính xác chuỗi kết hợp truyền thống làm ID ca thi đẩy sang kết quả JSON
#             full_shift_string = f"{date_strings[slot_index]} - {ca_strings[slot_index]} ({cs_strings[slot_index]})"
#             assignment_map[full_shift_string].append(str(staff_ids[staff_index]))

#         output_data = {
#             'success': True,
#             'assignments': [
#                 {'shiftId': shift_id, 'staffIds': staff_list, 'staffNames': staff_list}
#                 for shift_id, staff_list in assignment_map.items()
#             ],
#             'metrics': {
#                 'totalShifts': len(assignment_map),
#                 'totalAssignments': int(len(best_assignments)),
#                 'totalStaff': int(len(staff_ids))
#             }
#         }

#         print(json.dumps(output_data, ensure_ascii=False))
#         print("\n[WRAPPER] PROCESS COMPLETED SUCCESSFULLY!")
#         print("=" * 60)
#     except Exception as e:
#         print(f"\n[WRAPPER] Critical error during execution: {e}", file=sys.stderr)
#         import traceback
#         traceback.print_exc(file=sys.stderr)
#         sys.exit(1)

# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
"""
backend_wrapper.py
==================
Wrapper tự động nhận diện thư mục chạy giải thuật NSGA-II 
và cập nhật cấu hình dữ liệu mới từ Frontend, sử dụng tên cột đồng bộ rút gọn.
Đã cô lập luồng stdout sạch để Node.js parse JSON không bao giờ bị lỗi.
"""
import sys
import os
import json
import pandas as pd
from collections import defaultdict

def main():
    # 🌟 KỸ THUẬT CÔ LẬP LUỒNG: Giữ lại stdout gốc để nhả dữ liệu JSON cuối cùng
    original_stdout = sys.stdout
    # Ép tất cả các lệnh print() thông thường của hệ thống và module import đi qua luồng stderr
    sys.stdout = sys.stderr

    # 1. TỰ ĐỘNG XÁC ĐỊNH THƯ MỤC BACKEND NGAY TẠI VỊ TRÍ FILE NÀY
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    backend_root = CURRENT_DIR

    # Add backend root to Python path so we can import 'config' and 'src'
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    print(f"[WRAPPER] Thư mục hoạt động backend: {backend_root}")

    # Read JSON overrides from stdin (if any)
    stdin_data = ''
    try:
        stdin_data = sys.stdin.read()
    except Exception:
        stdin_data = ''

    overrides = {}
    if stdin_data and stdin_data.strip():
        try:
            overrides = json.loads(stdin_data)
        except Exception as e:
            print(f"[wrapper] Failed to parse JSON from stdin: {e}")

    # Safely import the backend config module
    try:
        import config
    except ImportError as e:
        print(f"[wrapper] Failed to import 'config' from backend-root '{backend_root}': {e}")
        sys.exit(10)

    # ==========================================================================
    # CƠ CHẾ ÉP BUỘC TỰ ĐỘNG: ƯU TIÊN FILE DỮ LIỆU MỚI DO FRONTEND IMPORT
    # ==========================================================================
    NEW_STAFF = os.path.join(config.DATA_DIR, "can_bo_new.csv")
    NEW_SHIFT = os.path.join(config.DATA_DIR, "ca_thi_new.csv")
    
    if os.path.exists(NEW_STAFF):
        config.INPUT_STAFF_FILE = NEW_STAFF
        print(f"[wrapper - FORCE] Đã phát hiện và ép nạp file cán bộ mới: {NEW_STAFF}")
    else:
        print(f"[wrapper - INFO] Sử dụng file cán bộ mặc định: {config.INPUT_STAFF_FILE}")
        
    if os.path.exists(NEW_SHIFT):
        config.INPUT_SHIFT_FILE = NEW_SHIFT
        print(f"[wrapper - FORCE] Đã phát hiện và ép nạp file ca thi mới: {NEW_SHIFT}")
    else:
        print(f"[wrapper - INFO] Sử dụng file ca thi mặc định: {config.INPUT_SHIFT_FILE}")
    # ==========================================================================

    # Xử lý hệ số ràng buộc mềm từ frontend (8 RB benchmark RB4–RB11)
    ui_config = overrides.get("config", {}) if overrides else {}
    BENCHMARK_DEFAULTS = {
        "fairnessWeight": 8,
        "minShiftWeight": 5,
        "distanceWeight": 0.1,
        "distanceFairnessWeight": 0.5,
        "sameDayDiffFacilityWeight": 6,
        "consecutiveShiftsWeight": 4,
        "agePriorityWeight": 3,
        "partnerDiversityWeight": 0.2,
    }
    nsga_weight_bridge = {
        "fairnessWeight": ("STD_DEVIATION_PENALTY", 5_000_000.0),
        "minShiftWeight": ("NO_ASSIGNMENT_PENALTY", 150_000_000.0),
        "distanceWeight": ("TRAVEL_DISTANCE_WEIGHT", 500.0),
        "distanceFairnessWeight": ("DISTANT_HEAVIER_LOAD_PENALTY", 50_000_000.0),
        "sameDayDiffFacilityWeight": ("SAME_DAY_CAMPUS_SWITCH_PENALTY", 25_000_000.0),
        "consecutiveShiftsWeight": ("CONSECUTIVE_SAME_CAMPUS_PENALTY", 200_000_000.0),
        "agePriorityWeight": ("ELDERLY_SHIFT_OVERLOAD_PENALTY", 20_000.0),
        "partnerDiversityWeight": ("REPEAT_PAIR_PENALTY", 200_000_000.0),
    }
    for ui_key, (config_key, default_val) in nsga_weight_bridge.items():
        if ui_key in ui_config:
            try:
                user_val = float(ui_config[ui_key])
                bench_default = float(BENCHMARK_DEFAULTS.get(ui_key, 1))
                scale = user_val / bench_default if bench_default else 1.0
                setattr(config, config_key, default_val * scale)
                print(f"[wrapper] Overrode config.{config_key} = {default_val * scale} (scale={scale:.3f})")
            except Exception as e:
                print(f"[wrapper] Failed to set config.{config_key}: {e}")

    # Now import backend modules and execute main flow
    try:
        from src.loader import load_data
        from src.model import run_nsga2_scheduler
        from src.exporter import export_results
    except Exception as e:
        print(f"[wrapper] Failed to import backend modules: {e}")
        raise

    print("=" * 60)
    print("[WRAPPER] Running backend with runtime config overrides")
    print("=" * 60)
    print(f"[wrapper] Using INPUT_SHIFT_FILE={config.INPUT_SHIFT_FILE}")
    print(f"[wrapper] Using INPUT_STAFF_FILE={config.INPUT_STAFF_FILE}")

    try:
        # Load data from the paths specified in config
        shift_df, staff_df = load_data(config.INPUT_SHIFT_FILE, config.INPUT_STAFF_FILE)
        
        # Execute NSGA-II core optimization algorithm
        print(f"[wrapper] shift_df columns: {list(shift_df.columns)}")
        print(f"[wrapper] staff_df columns: {list(staff_df.columns)}")
        best_assignments, flattened_slots = run_nsga2_scheduler(shift_df, staff_df)
        
        # Export the final optimal schedule to the output Excel file
        export_results(best_assignments, flattened_slots, staff_df, config.OUTPUT_SCHEDULE_FILE)

        # Run benchmark scoring on exported schedule → feed dashboard distribution chart
        bench_penalties = None
        bench_total = None
        bench_hard = None
        bench_soft = None
        try:
            benchmark_root = os.path.normpath(os.path.join(backend_root, '..', 'benchmark-iap-main'))
            if benchmark_root not in sys.path:
                sys.path.insert(0, benchmark_root)
            from benchmark import benchmark_metrics, apply_weight_overrides

            apply_weight_overrides(ui_config)
            bench_result = benchmark_metrics(
                staff_path=config.INPUT_STAFF_FILE,
                shift_path=config.INPUT_SHIFT_FILE,
                schedule_path=config.OUTPUT_SCHEDULE_FILE,
                weight_overrides=ui_config,
            )
            bench_penalties = bench_result.get('penalties')
            bench_total = bench_result.get('total_penalty')
            bench_hard = bench_result.get('hard')
            bench_soft = bench_result.get('soft')
            print(f"[wrapper] Benchmark total_penalty={bench_total}")
        except Exception as bench_err:
            print(f"[wrapper] Benchmark scoring skipped: {bench_err}")
            import traceback
            traceback.print_exc()

        # #region agent log
        try:
            _log_path = os.path.normpath(os.path.join(backend_root, '..', 'debug-529a9e.log'))
            with open(_log_path, 'a', encoding='utf-8') as _lf:
                _lf.write(json.dumps({
                    'sessionId': '529a9e', 'hypothesisId': 'B', 'location': 'backend_wrapper.py:benchmark',
                    'message': 'benchmark after export',
                    'data': {
                        'hasPenalties': bench_penalties is not None,
                        'totalPenalty': bench_total,
                        'penaltyKeys': list(bench_penalties.keys()) if bench_penalties else [],
                    },
                    'timestamp': int(__import__('time').time() * 1000),
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion

        # 🌟 ĐÓNG GÓI JSON SỬ DỤNG TÊN CỘT ĐỒNG BỘ GỌN GÀNG ĐỂ TRẢ VỀ CHO FRONTEND
        staff_ids = staff_df['Mã cán bộ'].astype(str).tolist()
        
        if pd.api.types.is_datetime64_any_dtype(flattened_slots['Ngày']):
            date_strings = flattened_slots['Ngày'].dt.strftime('%d/%m/%Y').astype(str).tolist()
        else:
            date_strings = flattened_slots['Ngày'].astype(str).tolist()
            
        ca_strings = flattened_slots['Ca thi'].astype(str).tolist()
        cs_strings = flattened_slots['Cơ sở'].astype(str).tolist()

        assignment_map = defaultdict(list)
        for slot_index, staff_index in enumerate(best_assignments):
            # Tái tạo chính xác chuỗi kết hợp truyền thống làm ID ca thi đẩy sang kết quả JSON
            full_shift_string = f"{date_strings[slot_index]} - {ca_strings[slot_index]} ({cs_strings[slot_index]})"
            assignment_map[full_shift_string].append(str(staff_ids[staff_index]))

        avg_shifts = len(best_assignments) / max(len(staff_ids), 1)
        metrics_payload = {
            'totalShifts': len(assignment_map),
            'totalAssignments': int(len(best_assignments)),
            'totalStaff': int(len(staff_ids)),
            'avg_shifts_per_staff': round(avg_shifts, 2),
        }
        if bench_penalties is not None:
            metrics_payload['penalties'] = bench_penalties
            metrics_payload['totalPenalty'] = round(float(bench_total or 0), 2)
            if bench_hard is not None:
                metrics_payload['hard'] = bench_hard
            if bench_soft is not None:
                metrics_payload['soft'] = bench_soft

        output_data = {
            'success': True,
            'algorithm': 'NSGA-II',
            'assignments': [
                {'shiftId': shift_id, 'staffIds': staff_list, 'staffNames': staff_list}
                for shift_id, staff_list in assignment_map.items()
            ],
            'metrics': metrics_payload,
        }

        # 🌟 XUẤT PHÁT PAYLOAD DỮ LIỆU SẠCH 100% VÀO STDOUT GỐC ĐỂ NODE.JS ĐỌC
        json_payload = json.dumps(output_data, ensure_ascii=False)
        original_stdout.write(json_payload + "\n")
        original_stdout.flush()

        print("\n[WRAPPER] PROCESS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[WRAPPER] Critical error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
    