"""账本一致性校验 CLI。运行：python tools/verify_ledger.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pet_system.services.ledger import verify
from pet_system.db import fetch_all


def main():
    children = fetch_all("SELECT id, name FROM child ORDER BY id")
    all_ok = True
    for c in children:
        r = verify(c["id"])
        status = "✓ 一致" if r["ok"] else "✗ 不一致"
        print(f"[{status}] {c['name']} (id={c['id']})")
        for p in r["problems"]:
            print("   -", p)
            all_ok = False
    print("\n总体：", "全部通过" if all_ok else "发现问题，请检查")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
