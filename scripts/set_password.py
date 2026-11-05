"""Đặt tài khoản đăng nhập cho Smart Attendance.

Cách dùng (trong thư mục dự án):
    python scripts/set_password.py

Script hỏi tên đăng nhập và mật khẩu, rồi ghi chuỗi băm vào .streamlit/secrets.toml
(tệp này KHÔNG được đưa lên GitHub). Với Streamlit Cloud: chép 3 dòng [auth] in ra
màn hình vào mục Settings → Secrets của app.
"""

import getpass
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth import hash_password  # noqa: E402

SECRETS = ROOT / ".streamlit" / "secrets.toml"


def main():
    username = input("Tên đăng nhập [admin]: ").strip() or "admin"
    password = getpass.getpass("Mật khẩu mới: ")
    if len(password) < 4:
        sys.exit("Mật khẩu quá ngắn.")
    if getpass.getpass("Nhập lại mật khẩu: ") != password:
        sys.exit("Hai lần nhập không khớp.")
    block = f'[auth]\nusername = "{username}"\npassword_hash = "{hash_password(password)}"\n'

    SECRETS.parent.mkdir(exist_ok=True)
    text = SECRETS.read_text(encoding="utf-8") if SECRETS.exists() else ""
    text = re.sub(r"\[auth\][^\[]*", "", text).strip()
    SECRETS.write_text((text + "\n\n" if text else "") + block, encoding="utf-8")
    print(f"Đã ghi {SECRETS}")
    print("\nNội dung cho Streamlit Cloud (Settings → Secrets):\n")
    print(block)


if __name__ == "__main__":
    main()
