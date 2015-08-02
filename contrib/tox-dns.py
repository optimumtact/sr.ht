#!/usr/bin/env python3

from pytoxns import make_server
from srht.objects import User
import os
import sys
import pwd
import grp

def lookup(name):
    parts = name.split("@")
    u = User.query.filter(User.username.ilike(parts[0])).first()
    if not u:
        return None
    return u.tox_id

server, pubkey = make_server(lookup, "sr.ht")
print(pubkey)

suid = "service:nogroup"

if os.getuid() == 0:
    if ":" not in suid:
        user = suid
        group = None
    else:
        user, group = suid.split(":", 1)
    uid = pwd.getpwnam(user).pw_uid
    if group:
        gid = grp.getgrnam(group).gr_gid
    else:
        gid = pwd.getpwnam(user).pw_gid
    os.setgid(gid)
    os.setuid(uid)
else:
    print("error: we're not root. Exiting.")
    sys.exit()

server.start()
