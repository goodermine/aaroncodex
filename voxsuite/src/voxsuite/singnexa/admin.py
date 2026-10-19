"""Manage Singnexa beta accounts from the server shell.

    singnexa-admin create-user aaron --name "Aaron" --admin
    singnexa-admin create-user jess --name "Jess"        # prints a one-time password
    singnexa-admin reset-password jess
    singnexa-admin disable jess | enable jess
    singnexa-admin list-users

Uses the same database the web app uses (--data, or $SINGNEXA_DATA). New users
and resets get a one-time password that must be changed at first sign-in.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .store import Store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="singnexa-admin", description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=os.environ.get("SINGNEXA_DATA", "./_singnexa"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-user")
    c.add_argument("username")
    c.add_argument("--name", default="")
    c.add_argument("--admin", action="store_true")
    for name in ("reset-password", "disable", "enable"):
        sub.add_parser(name).add_argument("username")
    sub.add_parser("list-users")
    args = ap.parse_args(argv)

    store = Store(Path(args.data) / "singnexa.db")
    if args.cmd == "create-user":
        try:
            user, temp = store.create_user(args.username, args.name, is_admin=args.admin)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"created {user['username']}{' (admin)' if user['is_admin'] else ''}")
        print(f"one-time password: {temp}")
        print("They must choose their own password at first sign-in.")
        return 0
    if args.cmd == "list-users":
        for u in store.list_users():
            flags = [f for f, on in (("admin", u["is_admin"]), ("disabled", u["disabled"]),
                                     ("must-change-password", u["must_change_password"])) if on]
            print(f"{u['id']:>4}  {u['username']:<24} {u['display_name']:<24} jobs={u['jobs']:<4} {' '.join(flags)}")
        return 0
    user = store.user_by_username(args.username)
    if not user:
        print(f"error: no user {args.username!r}", file=sys.stderr)
        return 1
    if args.cmd == "reset-password":
        print(f"one-time password for {user['username']}: {store.reset_password(user['id'])}")
    else:
        store.set_disabled(user["id"], args.cmd == "disable")
        print(f"{user['username']} {args.cmd}d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
