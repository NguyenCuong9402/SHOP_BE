# Table of Contents
1. [Install Dev Env](#Install Dev Env)
2. [Migrate Database](#Migrate Database)

# Install Dev Env

1. install python 3.7
2. pip install -r requirements
3. python server.py `your server running at: http://localhost:5000`
4. message CURD running on uri `http://localhost:5000/admin/message/`


# Deploy
1. push code
2. go to jenkins build code

# Migrations Database
```
Note command line upgrate database
Note link demo : https://flask-migrate.readthedocs.io/en/latest/
 
- cd app folder
- flask db migrate -m "<comment update database>"
- flask db upgrade
```
`cd app && flask db migrate -m "New version here."`

2. if you want to upgrade database

`cd app && flask db upgrade"`