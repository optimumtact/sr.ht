import bcrypt
import asyncore
from secure_smtpd import SMTPServer, FakeCredentialValidator
from srht.objects import User

class UserValidator(object):
    def validate(self, username, password):
        user = User.query.filter(User.username == username).first()
        if not user:
            return False
        return bcrypt.checkpw(password, user.password)


SMTPServer(
    ('0.0.0.0', 4650),
    None,
    require_authentication=True,
    ssl=False,
    credential_validator=FakeCredentialValidator(),
)
asyncore.loop()
