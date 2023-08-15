#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('/home/pablo/Spymovil/dbase/sms.db')


with open('create_sqlite_db.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

#cur.execute("INSERT INTO posts (title, content) VALUES (?, ?)",
#            ('First Post', 'Content for the first post')
#            )

#cur.execute("INSERT INTO posts (title, content) VALUES (?, ?)",
#            ('Second Post', 'Content for the second post')
#            )

connection.commit()
connection.close()
