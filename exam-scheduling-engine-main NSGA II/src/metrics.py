"""
metrics.py
=========
Tập trung các hàm tính toán metric/benchmark để dễ dàng kết nối với dashboard.
"""

import numpy as np
import pandas as pd

# Hàm ví dụ: tính điểm phạt mềm (spenalty) từ kết quả benchmark

def calculate_spenalty(soft_results):
    """
    Chuyển đổi kết quả benchmark soft constraint thành bảng spenalty cho dashboard.
    soft_results: dict {constraint_name: {'score': float, 'details': ...}}
    Return: DataFrame với các cột ['Constraint', 'Penalty']
    """
    data = [
        {'Constraint': k, 'Penalty': v['score']} for k, v in soft_results.items()
    ]
    return pd.DataFrame(data)

# Có thể bổ sung thêm các hàm tính metric khác tại đây
