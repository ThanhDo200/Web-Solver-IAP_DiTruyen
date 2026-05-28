import pandas as pd
import sys

import pandas as pd
import sys

def load_data(shift_file, staff_file):
    try:
        # DEBUG: Đếm dòng trong file gốc trước khi đọc
        print(f"\n[DEBUG LOADER] File source check:")
        print(f"  Shift file: {shift_file}")
        with open(shift_file, 'r', encoding='utf-8-sig') as f:
            original_shift_lines = len(f.readlines())
        print(f"  → Original shift file lines: {original_shift_lines}")
        
        print(f"  Staff file: {staff_file}")
        with open(staff_file, 'r', encoding='utf-8-sig') as f:
            original_staff_lines = len(f.readlines())
        print(f"  → Original staff file lines: {original_staff_lines}")
        
        # 1. Đọc file CSV
        shift_df = pd.read_csv(shift_file, encoding='utf-8-sig')
        staff_df = pd.read_csv(staff_file, encoding='utf-8-sig')

        # 2. Xử lý tên cột: Xóa khoảng trắng và Đổi tên cột
        # Xóa khoảng trắng thừa ở tiêu đề (ví dụ: "Mã cán bộ " -> "Mã cán bộ")
        shift_df.columns = [str(c).strip() for c in shift_df.columns]
        staff_df.columns = [str(c).strip() for c in staff_df.columns]

        # Đổi tên từ tên cũ sang "Mã cán bộ" để khớp với logic backend
        staff_df = staff_df.rename(columns={
            'MS của CÁN BỘ COI THI': 'Mã cán bộ',
            'MSCB': 'Mã cán bộ'
        })
        
        # Đổi tên MS Ca thi thành Mã ca thi (nếu cần đồng bộ)
        shift_df = shift_df.rename(columns={
            'MS Ca thi': 'Mã ca thi'
        })

        # DEBUG: So sánh sau khi đọc
        print(f"  → After read_csv:")
        print(f"    shift_df rows: {len(shift_df)} (lost {original_shift_lines - 1 - len(shift_df)} rows)")
        print(f"    staff_df rows: {len(staff_df)} (lost {original_staff_lines - 1 - len(staff_df)} rows)")

        # 3. Chuẩn hóa chuỗi dữ liệu bên trong các ô
        for df in [shift_df, staff_df]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()

        # 4. Đảm bảo kiểu dữ liệu cần thiết cho việc tính toán
        if 'Số lượng cán bộ cần thiết' in shift_df.columns:
            shift_df['Số lượng cán bộ cần thiết'] = (
                pd.to_numeric(shift_df['Số lượng cán bộ cần thiết'], errors='coerce')
                .fillna(1)
                .astype(int)
            )
            
        if 'Mã ca thi' in shift_df.columns:
            shift_df['Mã ca thi'] = shift_df['Mã ca thi'].astype(str)

        # 5. Kiểm tra tính toàn vẹn (Cập nhật tên cột mới vào danh sách kiểm tra)
        required_shift_cols = ['Mã ca thi', 'Ca thi', 'Thứ', 'Ngày', 'Cơ sở', 'Số lượng cán bộ cần thiết']
        required_staff_cols = ['Mã cán bộ', 'Tuổi']
        
        for col in required_shift_cols:
            if col not in shift_df.columns:
                print(f"[WARNING] Thieu cot '{col}' trong file ca thi CSV.")
                
        for col in required_staff_cols:
            if col not in staff_df.columns:
                print(f"[WARNING] Thieu cot '{col}' trong file can bo CSV.")

        print(f"[INFO] Data loaded successfully: {len(shift_df)} shifts, {len(staff_df)} staff members.")
        return shift_df, staff_df

    except FileNotFoundError as e:
        print(f"[ERROR] Khong tim thay file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Loi khi doc file CSV: {e}")
        sys.exit(1)