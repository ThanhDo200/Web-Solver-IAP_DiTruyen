import os

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN VÀ TÊN FILE DỮ LIỆU
# ==========================================
# Khai báo đường dẫn tương đối đến thư mục data
DATA_DIR = "data"

# Khai báo tên các file Excel đầu vào
FILE_CAN_BO = "can_bo.xlsx"
FILE_CA_THI = "ca_thi.xlsx"
FILE_LICH_TRUC = "Ket_Qua_Xep_Lich.xlsx"

# Tạo đường dẫn tuyệt đối (an toàn hơn khi chạy code từ các thư mục khác nhau)
PATH_CAN_BO = os.path.join(DATA_DIR, "exam-scheduling-engine-main NSGA II", FILE_CAN_BO)
PATH_CA_THI = os.path.join(DATA_DIR, "exam-scheduling-engine-main NSGA II", FILE_CA_THI)
PATH_LICH_TRUC = os.path.join(DATA_DIR, "exam-scheduling-engine-main NSGA II", FILE_LICH_TRUC)

# ==========================================
# CẤU HÌNH TRỌNG SỐ ĐIỂM PHẠT (PENALTIES)
# ==========================================
# Trọng số càng cao thể hiện tiêu chí càng quan trọng. 
# Lịch trình tốt là lịch trình có tổng điểm phạt càng thấp.

WEIGHT_FAIRNESS = 8                 # Phạt nếu số ca trực chênh lệch so với mức trung bình
WEIGHT_DISTANCE = 0.1             # Phạt dựa trên tổng khoảng cách di chuyển
WEIGHT_DISTANCE_FAIRNESS = 0.5     # Phạt nếu khoảng cách di chuyển không công bằng giữa các cán bộ
WEIGHT_SAME_DAY_DIFF_FACILITY = 6   # Phạt nếu gác >2 ca/ngày mà phải di chuyển 2 cơ sở khác nhau
WEIGHT_MIN_SHIFT = 5                # Phạt nếu có cán bộ không được gác ca nào (số ca = 0)
WEIGHT_AGE_PRIORITY = 3             # Phạt nếu xếp nhiều ca cho người lớn tuổi (>45 tuổi)
WEIGHT_PARTNER_DIVERSITY = 0.2        # Phạt nếu 2 người gác chung với nhau quá nhiều lần
WEIGHT_CONSECUTIVE_SHIFTS = 4        # Phạt nếu có cán bộ gác nhiều ca liên tiếp trong cùng một ngày
# ==========================================
# CÁC HẰNG SỐ LOGIC KHÁC (Tùy chọn)
# ==========================================
AGE_THRESHOLD = 45                  # Ngưỡng tuổi để tính ưu tiên
MAX_PARTNER_REPETITION = 2          # Số lần tối đa 2 người được gác chung trước khi bị phạt