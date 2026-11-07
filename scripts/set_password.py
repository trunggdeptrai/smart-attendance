"""Đặt tài khoản đăng nhập cho Smart Attendance.

Cách dùng (trong thư mục dự án):
    python scripts/set_password.py
    python scripts/set_password.py --username admin --password-env TEN_BIEN
        (không hỏi: đọc mật khẩu từ biến môi trường TEN_BIEN - bộ cài setup/ dùng cách này)

Script hỏi tên đăng nhập và mật khẩu, rồi ghi chuỗi băm vào .streamlit/secrets.toml
(tệp này KHÔNG được đưa lên GitHub). Với Streamlit Cloud: chép 3 dòng [auth] in ra
màn hình vào mục Settings → Secrets của app.
"""

import argparse
import getpass
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.auth import hash_password  # noqa: E402

SECRETS = ROOT / ".streamlit" / "secrets.toml"


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")


def main():
    parser = argparse.ArgumentParser(description="Đặt tài khoản đăng nhập Smart Attendance.")
    parser.add_argument("--username", help="tên đăng nhập (bỏ trống: hỏi, mặc định admin)")
    parser.add_argument("--password-env", metavar="TEN_BIEN",
                        help="đọc mật khẩu từ biến môi trường này thay vì hỏi")
    args = parser.parse_args()

    if args.username is not None:
        username = args.username.strip() or "admin"
    else:
        username = input("Tên đăng nhập [admin]: ").strip() or "admin"
    if not USERNAME_RE.match(username):
        sys.exit("Tên đăng nhập chỉ gồm chữ không dấu, số và các ký tự _ . @ - (tối đa 64 ký tự).")

    if args.password_env:
        password = os.environ.get(args.password_env, "")
        if len(password) < 4:
            sys.exit("Mật khẩu quá ngắn (cần ít nhất 4 ký tự).")
    else:
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
    if not args.password_env:
        print("\nNội dung cho Streamlit Cloud (Settings → Secrets):\n")
        print(block)


if __name__ == "__main__":
    main()
