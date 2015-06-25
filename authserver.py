#!/usr/bin/env python3

import bcrypt
import asyncore
from secure_smtpd import SMTPServer, FakeCredentialValidator
from srht.objects import User

class UserValidator(object):
    def validate(self, username, password):
        user = User.query.filter(User.username == username).first()
        if not user:
            print("Authentication failed for {}, unknown user".format(user))
            return False
        success = bcrypt.checkpw(password, user.password)
        if not success:
            print("Authentication failed for {}, bad password".format(user))
        else:
            print("Authentication successful for {}".format(user))
        return success


SMTPServer(
    ('0.0.0.0', 4650),
    None,
    require_authentication=True,
    ssl=False,
    credential_validator=FakeCredentialValidator(),
).run()
