
import sys
import os

# HƯỚNG DẪN: Để lấy bảng spenalty cho dashboard, hãy sử dụng hàm calculate_spenalty từ metrics.py trong engine.
# from exam-scheduling-engine-main NSGA II.src.metrics import calculate_spenalty
# df_spenalty = calculate_spenalty(soft_results)


def check_dependencies():
    missing = []
    try:
        import pandas  # noqa: F401
    except ImportError:
        missing.append('pandas')
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        missing.append('openpyxl')
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append('numpy')
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        missing.append('matplotlib')
    try:
        import seaborn  # noqa: F401
    except ImportError:
        missing.append('seaborn')

    if missing:
        print('\nMissing required Python packages: ' + ', '.join(missing) + '\n')
        print('Install them into your environment, for example:')
        print('  python -m pip install ' + ' '.join(missing))
        print('\nOr create and activate a virtual environment and then run:')
        print('  python -m venv .venv')
        print('  .\\.venv\\Scripts\\Activate.ps1    # PowerShell')
        print('  .\\.venv\\bin\\Activate.ps1        # Nếu venv tạo ra bin/ thay vì Scripts/')
        print('  python -m pip install -r requirements.txt')
        sys.exit(1)


# ensure deps before importing project modules that rely on them
check_dependencies()

import pandas as pd

from data_loader import load_data
from hard_constraints import evaluate_hard_constraints
from soft_constraints import evaluate_soft_constraints
from excel_exporter import export_to_excel
from evaluate_and_plot import run_evaluation_pipeline

class TerminalColor:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def main():
    print(f"{TerminalColor.BOLD}{TerminalColor.HEADER}")
    print("="*65)
    print("   HỆ THỐNG BENCHMARK LỊCH TRỰC COI THI (INTELLIGENT SCORING)")
    print("="*65)
    print(f"{TerminalColor.RESET}")

    # Tạo sẵn thư mục output ở thư mục gốc
    os.makedirs("output", exist_ok=True)

    # BƯỚC 1: NẠP DỮ LIỆU
    print(f"{TerminalColor.CYAN}[1/4] Đang nạp và chuẩn hóa dữ liệu...{TerminalColor.RESET}")
    try:
        df_can_bo, df_ca_thi, df_lich_truc = load_data()
    except Exception as e:
        print(f"{TerminalColor.RED}✘ Lỗi khi đọc dữ liệu: {e}{TerminalColor.RESET}")
        sys.exit(1)

    # BƯỚC 2: ĐÁNH GIÁ RÀNG BUỘC CỨNG (HARD CONSTRAINTS)
    print(f"\n{TerminalColor.BOLD}{TerminalColor.CYAN}[2/4] Đang kiểm tra Ràng buộc cứng...{TerminalColor.RESET}")
    hard_results = evaluate_hard_constraints(df_lich_truc)
    
    for rb_name, result in hard_results.items():
        if result['pass']:
            print(f"{TerminalColor.GREEN}✔ {rb_name}: PASS{TerminalColor.RESET}")
        else:
            print(f"{TerminalColor.RED}✘ {rb_name}: FAIL ({result['violations']} vi phạm){TerminalColor.RESET}")
            if isinstance(result['details'], list):
                for detail in result['details']:  
                    print(f"   {TerminalColor.RED}-> {detail}{TerminalColor.RESET}")

    # BƯỚC 3: ĐÁNH GIÁ RÀNG BUỘC MỀM (SOFT CONSTRAINTS)
    print(f"\n{TerminalColor.BOLD}{TerminalColor.CYAN}[3/4] Đang tính điểm phạt Ràng buộc mềm...{TerminalColor.RESET}")
    total_penalty, soft_results = evaluate_soft_constraints(df_can_bo, df_lich_truc)
    
    for rb_name, info in soft_results.items():
        print(f"[-] {rb_name:<30} | {TerminalColor.YELLOW}Phạt: {info['score']:>7.2f} điểm{TerminalColor.RESET} | {info['details']}")

    # BƯỚC 4: TỔNG KẾT VÀ XUẤT EXCEL
    print(f"\n{TerminalColor.BOLD}{TerminalColor.CYAN}[4/4] Đang tổng kết và xuất báo cáo...{TerminalColor.RESET}")
    print(f"{TerminalColor.BOLD}{TerminalColor.HEADER}" + "="*65)
    print(f"🏆 FINAL BENCHMARK SCORE = {total_penalty:.2f}")
    print("="*65 + f"{TerminalColor.RESET}")

    df_flat = df_lich_truc.explode('DS_Can_Bo').rename(columns={'DS_Can_Bo': 'MS_CB'}).dropna(subset=['MS_CB'])
    df_flat_full = pd.merge(df_flat, df_can_bo, on='MS_CB', how='left')
    shift_counts = df_flat_full['MS_CB'].value_counts()
    all_shift_counts = shift_counts.reindex(df_can_bo['MS_CB'], fill_value=0)
    mu = len(df_flat_full) / len(df_can_bo) if len(df_can_bo) > 0 else 0

    try:
        export_to_excel(hard_results, soft_results, total_penalty, df_can_bo, df_lich_truc, all_shift_counts, mu)
    except Exception as e:
        print(f"{TerminalColor.RED}✘ Lỗi khi tạo file Excel: {e}{TerminalColor.RESET}")

    try:
        run_evaluation_pipeline()
    except Exception as e:
        print(f"{TerminalColor.RED}✘ Lỗi khi tạo biểu đồ: {e}{TerminalColor.RESET}")

    # BƯỚC 5: XUẤT FILE LOG TXT - GHI CHI TIẾT TOÀN BỘ SỰ CỐNG CỨNG & MỀM (BẤT KỂ TRỌNG SỐ = 0)
    txt_filename = os.path.join("output", "Benchmark_Log.txt")
    try:
        import itertools
        from collections import Counter

        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write("=========================================================\n")
            f.write("     BÁO CÁO ĐẦY ĐỦ CHI TIẾT VI PHẠM LỊCH TRỰC COI THI    \n")
            f.write("=========================================================\n\n")
            
            f.write(f"=> TỔNG ĐIỂM PHẠT CHUNG (BENCHMARK SCORE): {total_penalty:.2f}\n\n")
            
            f.write("[PHẦN 1] CHI TIẾT VI PHẠM RÀNG BUỘC CỨNG (HARD CONSTRAINTS)\n")
            f.write("-" * 65 + "\n")
            for rb_name, result in hard_results.items():
                status = "PASS" if result['pass'] else f"FAIL ({result['violations']} lỗi)"
                f.write(f"📌 {rb_name}: {status}\n")
                if not result['pass'] and isinstance(result['details'], list):
                    for detail in result['details']:
                        f.write(f"   -> {detail}\n")
            
            f.write("\n[PHẦN 2] CHI TIẾT VI PHẠM RÀNG BUỘC MỀM (SOFT CONSTRAINTS)\n")
            f.write("-" * 65 + "\n")
            for rb_name, info in soft_results.items():
                f.write(f"[-] {rb_name:<30} | Phạt: {info['score']:>7.2f} điểm | {info['details']}\n")
                
            f.write("\n>> DANH SÁCH KHẢO SÁT CHI TIẾT TỪNG TRƯỜNG HỢP BỊ TRỪ ĐIỂM MỀM:\n")
            # RB4: Chi tiết phân bổ không đều ca
            f.write(f"\n* [RB4] Mức độ lệch tải công việc (Tiêu chuẩn trung bình μ = {mu:.2f} ca/người):\n")
            for cb_id, count in all_shift_counts.items():
                if count != round(mu, 2):
                    f.write(f"  -> Cán bộ {cb_id}: Trực {count} ca (Chênh lệch: {abs(count - mu):.2f} ca)\n")
            # RB5: Chi tiết bỏ sót người
            f.write("\n* [RB5] Cán bộ không được phân công ca nào (0 ca):\n")
            skipped = all_shift_counts[all_shift_counts == 0].index.tolist()
            f.write(f"  -> {', '.join(skipped) if skipped else 'Không có ai bị bỏ sót.'}\n")

            # RB6: Thống kê quãng đường di chuyển thực tế (bất kể bị phạt hay không)
            f.write("\n* [RB6] Chi tiết tổng quãng đường di chuyển của từng cán bộ (km):\n")
            df_flat_full['KC_Tung_Ca'] = df_flat_full.apply(lambda r: r['KC_CS1'] if r['Co_So'] == 'Cơ sở 1' else (r['KC_CS2'] if r['Co_So'] == 'Cơ sở 2' else 0), axis=1)
            staff_dist = df_flat_full.groupby('MS_CB')['KC_Tung_Ca'].sum()
            for cb_id, d in staff_dist.items():
                if d > 0:
                    f.write(f"  -> Cán bộ {cb_id}: Tổng quãng đường đi gác = {d:.2f} km\n")

            # RB8: Chi tiết đổi cơ sở trong cùng một ngày
            f.write("\n* [RB8] Cán bộ trực nhiều ca cùng ngày nhưng phải di chuyển khác cơ sở:\n")
            has_rb8 = False
            
            # Cần sort theo thời gian trước để hiển thị đúng thứ tự di chuyển
            df_sorted_rb8 = df_flat_full.sort_values(by=['MS_CB', 'Ngay_Goc', 'Thoi_diem_bat_dau'])
            
            for (cb, date), group in df_sorted_rb8.groupby(['MS_CB', 'Ngay_Goc']):
                if group['Co_So'].nunique() > 1:
                    # Tạo chuỗi lịch trình trực quan
                    shifts = group.to_dict('records')
                    hanh_trinh = " -->> ".join([f"{s['Co_So']} gác ca {s['MS_CA']}" for s in shifts])
                    
                    # Rút gọn ngày cho dễ nhìn
                    date_str = pd.to_datetime(date).strftime('%d/%m/%Y')
                    
                    f.write(f"  -> Cán bộ {cb} ngày {date_str} di chuyển: {hanh_trinh}\n")
                    has_rb8 = True
                    
            if not has_rb8: f.write("  -> Không có trường hợp vi phạm.\n")
                    
            # RB9: Chi tiết thời gian nghỉ giữa 2 ca sát nút (Trực liên tiếp)
            f.write("\n* [RB9] Chi tiết các ca xếp liên tiếp nhau trong cùng một ngày (Nghỉ ngơi chưa đủ):\n")
            has_rb9 = False

            # Sắp xếp đúng theo cột Thoi_diem_bat_dau được tạo từ data_loader
            df_sorted_rb9 = df_flat_full.sort_values(by=['MS_CB', 'Ngay_Goc', 'Thoi_diem_bat_dau'])
            
            for (cb, date), group in df_sorted_rb9.groupby(['MS_CB', 'Ngay_Goc']):
                if len(group) >= 2:
                    shifts = group.to_dict('records')
                    for i in range(1, len(shifts)):
                        # Lấy hậu tố của MS_CA để biết số thứ tự ca (VD: '20260522_5' -> 5)
                        try:
                            prev_ca_num = int(str(shifts[i-1]['MS_CA']).split('_')[-1])
                            curr_ca_num = int(str(shifts[i]['MS_CA']).split('_')[-1])
                        except ValueError:
                            # Fallback nếu MS_CA không chứa dấu '_'
                            prev_ca_num = shifts[i-1].get('Ca_Thu', 0)
                            curr_ca_num = shifts[i].get('Ca_Thu', 0)
                        
                        # Nếu 2 ca có số thứ tự liền kề nhau (VD: Ca 1 và Ca 2)
                        if (curr_ca_num - prev_ca_num) == 1:
                            time_prev = shifts[i-1]['Thoi_diem_bat_dau']
                            time_curr = shifts[i]['Thoi_diem_bat_dau']
                            
                            str_time_prev = time_prev.strftime('%H:%M') if pd.notna(time_prev) else "N/A"
                            str_time_curr = time_curr.strftime('%H:%M') if pd.notna(time_curr) else "N/A"
                            
                            f.write(f"  -> Cán bộ {cb}: Trực liên tiếp {shifts[i-1]['MS_CA']} (bắt đầu {str_time_prev}) và {shifts[i]['MS_CA']} (bắt đầu {str_time_curr})\n")
                            has_rb9 = True
                            
            if not has_rb9: 
                f.write("  -> Không có trường hợp vi phạm trực 2 ca liên tiếp.\n")

            # RB10: Chi tiết phân bổ quá tải cho người lớn tuổi
            f.write("\n* [RB10] Cán bộ lớn tuổi (>45 tuổi) bị phân phối vượt trần trung bình:\n")
            has_rb10 = False
            for cb_row in df_can_bo.to_dict('records'):
                if cb_row['Tuoi'] > 45:
                    tc = all_shift_counts.get(cb_row['MS_CB'], 0)
                    if tc > mu:
                        f.write(f"  -> Cán bộ {cb_row['MS_CB']} ({cb_row['Tuoi']} tuổi): Trực {tc} ca (Vượt trần {tc - mu:.2f} ca)\n")
                        has_rb10 = True
            if not has_rb10: f.write("  -> Không có trường hợp vi phạm.\n")

            # RB11: Chi tiết cặp đôi trùng lặp đối tác gác thi
            f.write("\n* [RB11] Chi tiết các cặp đôi gác chung với nhau quá nhiều lần (>= 3 lần):\n")
            all_pairs = []
            for ds in df_lich_truc['DS_Can_Bo']:
                if len(ds) >= 2:
                    all_pairs.extend(itertools.combinations(sorted(ds), 2))
            pair_counts = Counter(all_pairs)
            freq_pairs = {p: c for p, c in pair_counts.items() if c >= 3}
            if freq_pairs:
                for pair, count in freq_pairs.items():
                    f.write(f"  -> Cặp ({pair[0]}, {pair[1]}): Gác chung {count} lần\n")
            else: f.write("  -> Không có cặp nào gác chung >= 3 lần.\n")
                

        print(f"{TerminalColor.GREEN}✔ Đã cập nhật và lưu vết vi phạm chi tiết 9/9 luật mềm ra file: {txt_filename}{TerminalColor.RESET}\n")
    except Exception as e:
        print(f"{TerminalColor.RED}✘ Lỗi khi ghi file log TXT: {e}{TerminalColor.RESET}")

