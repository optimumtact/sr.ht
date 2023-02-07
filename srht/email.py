import smtplib
import pystache
import os
import html.parser
from email.mime.text import MIMEText
import email.utils
from werkzeug.utils import secure_filename
from flask import url_for

from srht.database import db
from srht.objects import User
from srht.config import _cfg, _cfgi

def send_request_notification(user):
    if _cfg("smtphost") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtphost"), _cfgi("smtpport"))
    smtp.ehlo()
    smtp.starttls()
    smtp.login(_cfg("smtpuser"), _cfg("smtppassword"))
    with open("emails/new_request") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(
            pystache.render(f.read(), {
                'user': user,
                "domain": _cfg("domain"),
                "protocol": _cfg("protocol")
            })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "New %s account request" % _cfg("domain")
    message['From'] = _cfg("smtpfrom")
    message['To'] = _cfg("owner_email")

    message["Date"] = email.utils.formatdate(localtime=True)
    message['Message-ID'] = email.utils.make_msgid(user.username, _cfg("domain"))
    smtp.sendmail(_cfg("smtpfrom"), [ _cfg("owner_email") ],
            message.as_string())
    smtp.quit()

def send_invite(user):
    if _cfg("smtphost") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtphost"), _cfgi("smtpport"))
    smtp.ehlo()
    smtp.starttls()
    smtp.login(_cfg("smtpuser"), _cfg("smtppassword"))
    with open("emails/invite") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(\
            pystache.render(f.read(), {
                'user': user,
                "domain": _cfg("domain"),
                "protocol": _cfg("protocol")
            })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "Your %s account is approved" % _cfg("domain")
    message['From'] = _cfg("smtpfrom")
    message['To'] = user.email
    message["Date"] = email.utils.formatdate(localtime=True)
    message['Message-ID'] = email.utils.make_msgid(user.username, _cfg("domain"))
    smtp.sendmail(_cfg("smtpfrom"), [ user.email ], message.as_string())
    smtp.quit()

def send_rejection(user):
    if _cfg("smtphost") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtphost"), _cfgi("smtpport"))
    smtp.starttls()
    smtp.ehlo()
    smtp.login(_cfg("smtpuser"), _cfg("smtppassword"))
    with open("emails/reject") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(
            pystache.render(f.read(), {
                'user': user,
                "domain": _cfg("domain"),
                "protocol": _cfg("protocol")
            })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "Your %s account has been rejected" % _cfg("domain")
    message['From'] = _cfg("smtpfrom")
    message['To'] = user.email
    message["Date"] = email.utils.formatdate(localtime=True)
    message['Message-ID'] = email.utils.make_msgid(user.username, _cfg("domain"))
    smtp.sendmail(_cfg("smtpfrom"), [ user.email ], message.as_string())
    smtp.quit()

def send_reset(user):
    if _cfg("smtphost") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtphost"), _cfgi("smtpport"))
    smtp.starttls()
    smtp.ehlo()
    smtp.login(_cfg("smtpuser"), _cfg("smtppassword"))
    with open("emails/reset") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(\
            pystache.render(f.read(), {
                'user': user,
                "domain": _cfg("domain"),
                "protocol": _cfg("protocol"),
                'confirmation': user.passwordReset
            })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "Reset your %s password" % _cfg("domain")
    message['From'] = _cfg("smtpfrom")
    message['To'] = user.email
    message["Date"] = email.utils.formatdate(localtime=True)
    message['Message-ID'] = email.utils.make_msgid(user.username, _cfg("domain"))
    smtp.sendmail(_cfg("smtpfrom"), [ user.email ], message.as_string())
    smtp.quit()
