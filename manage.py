#!bin/python3
from srht.database import db
from srht.objects import User
from datetime import datetime
from docopt import docopt
#Functions driving behaviour

def remove_admin(arguments):
    u = User.query.filter(User.username == arguments['<name>']).first()
    if(u):
        u.admin = False # remove admin
        db.commit()
    else:
        print('Not a valid user')

def make_admin(arguments):
    u = User.query.filter(User.username == arguments['<name>']).first()
    if(u):
        u.admin = True # make admin
        db.commit()
    else:
        print('Not a valid user')

def list_admin(arguments):
    users = User.query.filter(User.admin == True)
    for u in users:
        print(u.username)

def approve_user(arguments):
    u = User.query.filter(User.username == arguments['<name>']).first()
    if(u):
        u.approved = True # approve user
        u.approvalDate = datetime.now()
        db.commit()
    else:
        print('Not a valid user')


interface = """
Command line admin interface
Usage:
    manage admin promote <name>
    manage admin demote <name>
    manage admin list
    manage user approve <name>

Options:
    -h --help Show this screen.
"""
if __name__ == '__main__':
    arguments = docopt(interface, version='make admin 0.1')
    if(arguments['admin'] and arguments['promote']):
        make_admin(arguments)
    elif(arguments['admin'] and arguments['demote']):
        remove_admin(arguments)
    elif(arguments['admin'] and arguments['list']):
        list_admin(arguments)
    elif(arguments['user'] and arguments['approve']):
        remove_admin(arguments)
