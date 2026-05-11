import smtplib
import ssl
import pystache
import html
from email.mime.text import MIMEText
import email.utils
from srht.config import _cfg, _cfgi


def send_reset(user):
    if _cfg("smtphost") == "":
        return
    context = ssl.create_default_context()
    smtp = smtplib.SMTP(_cfg("smtphost"), _cfgi("smtpport"))
    smtp.starttls(context=context)
    smtp.ehlo()
    smtp.login(_cfg("smtpuser"), _cfg("smtppassword"))
    with open("emails/reset") as f:
        message = MIMEText(
            html.unescape(
                pystache.render(
                    f.read(),
                    {
                        "user": user,
                        "domain": _cfg("domain"),
                        "protocol": _cfg("protocol"),
                        "confirmation": user.passwordReset,
                    },
                )
            )
        )
    message["X-MC-Important"] = "true"
    message["X-MC-PreserveRecipients"] = "false"
    message["Subject"] = "Reset your %s password" % _cfg("domain")
    message["From"] = _cfg("smtpfrom")
    message["To"] = user.email
    message["Date"] = email.utils.formatdate(localtime=True)
    message["Message-ID"] = email.utils.make_msgid(user.username, _cfg("domain"))
    smtp.sendmail(_cfg("smtpfrom"), [user.email], message.as_string())
    smtp.quit()
