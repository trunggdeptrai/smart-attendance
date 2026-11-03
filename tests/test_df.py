import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import get_employee_dataframe
from db.attendance_repo import get_today_attendance_dataframe, get_attendance_history_dataframe

print("Testing dataframes...")
try:
    df1 = get_employee_dataframe()
    print(f"Employee DF: {df1.shape}")
    df2 = get_today_attendance_dataframe()
    print(f"Today DF: {df2.shape}")
    df3 = get_attendance_history_dataframe()
    print(f"History DF: {df3.shape}")
    print("All dataframe tests passed!")
except Exception as e:
    import traceback
    traceback.print_exc()
