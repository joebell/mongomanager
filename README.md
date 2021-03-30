# MongoManager

A Flask blueprint for building a basic website with MongoDB. Provides decorators for role-based authentication, and routes for inspection of database elements. 

## Features:
```
    @mm.requires_auth       - Decorator to ensure authentication
    @mm.requires_perm(role) - Decorator to ensure permission

    Injects the logged in User object into the app context so templates can access it as {{ user }}.

    Routes (all require an 'admin' role):
        /nopermission
        /login
        /logout
        /register - The first user to register is assigned as 'admin'
        /roles - View and edit user roles. 
        /dir/<path:path> - List directory contents
        /showfile/<id> - Displays the contents of a file. 
            (Only filetype='.json' or '.png' are implemented now.)
        /getfile/<id> - Returns the file.
        /collections - Lists all collections.
        /collection/<className> - Lists all Documents in the collection.
        /collection/<className>/<id> - Displays a Document.


    Utilities:
        link_to_file(path, filename) - Returns a link to a file.
        link_to_parent_dir(path) - Returns a link to the parent directory.
        render_item(key, item, parent) - Renders a field of a Document.
```

## Usage:

Clone the repo into your Flask project:
```
/var/www/mysite
    - myapp.py
    - database.py
    /mongomanager
        - __init__.py
        - mongomanager.py
        - database.py
        /templates
            - base.html
            - etc.html
```
MongoManager will import your project's `database.py` so mind the naming.

In `mysite/database.py` import MongoManager's database classes:
```
    # Import mongomanager's database classes:
    from mongomanager.database import *

    # Define your own classes, from MongoManager's if you'd like.
    class MyClass(TrackedAssignment):
        myfield = me.StringField(required=True)

    class VideoFile(File):
        myfield = me.StringField(required=True)
```

In `mysite/myapp.py` import MongoManager and register the blueprint:
```
    from mongomanager import mongomanager as mm
    import database as db

    app.config['MONGODB_SETTINGS'] = {'db': 'mydbname'}
    db.eng.init_app(app)

    app.register_blueprint(mm.mongomanager)
```

In `mysite/.env` set `SAFEPATH` to permit directory browsing:
```
    SAFEPATH=/var/www/mysite
```





