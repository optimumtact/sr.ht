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

def create_user(arguments):
    u = User(arguments['<name>'], arguments['<email>'], arguments['<password>']);
    if(u):
        u.approved = True # approve user
        u.approvalDate = datetime.now()
        db.add(u)
        db.commit()
        print('User created')
    else:
        print('Couldn\'t create the uer')

def reset_password(arguments):
    u = User.query.filter(User.username == arguments['<name>']).first()
    if(u):
        password = arguments['<password>']
        if len(password) < 5 or len(password) > 256:
            print('Password must be between 5 and 256 characters.')
            return
        u.set_password(password)  
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
    manage user create <name> <password> <email>
    manage user reset_password <name> <password>

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
        approve_user(arguments)
    elif(arguments['user'] and arguments['create']):
        create_user(arguments)
    elif(arguments['user'] and arguments['reset_password']):
        reset_password(arguments)
