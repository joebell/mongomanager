# monogomanager.py
#
# Blueprint for password protected Mongo collections, 
# with registration and login
#
import os, glob, sys, json, time, bson, random
from functools import wraps
from os import environ as env
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError
from mongoengine import NotUniqueError
from flask import Flask, jsonify, redirect, request, make_response
from flask import render_template, Blueprint
from flask import session, url_for, flash, Response, abort
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

# Register as a blueprint
mongomanager = Blueprint('mongomanager', __name__,
                         template_folder='templates')

# MongoDB and forms
import database as db # Import the application's database, 
                      # which should import mongomanager.database itself.
import mongomanager.forms as forms

# Make user info available in all templates
@mongomanager.app_context_processor
def inject_user():
    if 'userid' in session:
        user = db.User.objects(id=session['userid']).first()
    else:
        user = dict()
        user['username'] = 'none'
        user['firstname'] = 'Not logged in'
        user['lastname'] = ''
    return dict(user=user)

# Decorator for routes that require authentication,
# but not permissions. Stores the request path with 
# the session variable to redirect the user on callback.
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'userid' not in session:
            session['requestpath'] = request.path
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# Decorator for routes that require authorization for
# a specific role. The 'admin' role allows all access.
def requires_perm(requiredRole):
    def permission(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'userid' not in session:
                session['requestpath'] = request.path
                return redirect('/login')
            user = db.User.objects(id=session['userid']).first()
            validRoles = [roleAssignment.role for roleAssignment 
                          in user.roleassignments if 
                          roleAssignment.iscurrent]
            if ((requiredRole not in validRoles) and 
                    ('admin' not in validRoles)):
                session['requestpath'] = request.path
                return redirect('/nopermission')
            return f(*args, **kwargs)
        return decorated
    return permission

# Landing page for users that authenticate but have no permission
@mongomanager.route('/nopermission')
@requires_auth
def nopermission():
    reqpath = session['requestpath']
    return render_template('nopermission.html',reqpath=reqpath)


# Login route
@mongomanager.route('/login', methods=['GET','POST'])
def login():
    # If the user didn't previously request a page, redirect to root
    if 'requestpath' not in session:
        session['requestpath'] = '/' 

    form = forms.LoginForm()
    if request.method == 'POST' and form.validate():
        existing_user = db.User.objects(username=form.username.data, 
                                        iscurrent=True).first()
        hashpass = generate_password_hash(form.password.data, 
                                          method='sha256')
        if existing_user is None:
            form.username.errors.append('User not found.')
        elif check_password_hash(existing_user.passwordhash, 
                                 form.password.data): 
            session['userid'] = str(existing_user.id)
            return redirect(session['requestpath'])
        else:
            form.password.errors.append('Incorrect password.')
    
    return render_template('login.html', form=form)


# Route for logout
@mongomanager.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Register route
@mongomanager.route('/register', methods=['GET','POST'])
def register():
    form = forms.RegistrationForm()
    if request.method == 'POST' and form.validate():
        existing_user = db.User.objects(username=form.username.data).first()
        if existing_user is None:
            # Create the new user, stored with hashed passwords
            hashpass = generate_password_hash(form.password.data, 
                                              method='sha256')
            newUser = db.User(addedby='self',
                           username=form.username.data,
                           firstname=form.firstname.data,
                           lastname=form.lastname.data,
                           email=form.email.data,
                           passwordhash=hashpass,
                           roleassignments=[])
            newUser.save()
            newUser.update(addedby=newUser)
            # If it's the first user, assign them to the admin role
            if (len(db.User.objects()) == 1): 
                newRole = db.RoleAssignment(role='admin',
                            user=newUser,
                            addedby=newUser,
                            addeddate = datetime.utcnow(),
                            iscurrent = True)
                newRole.save()
                newUser.update(push__roleassignments=newRole)
            return redirect('/login')
        else:
            form.username.errors.append('User already exists')
    return render_template('register.html', form=form)

# Given a path and filename, find a link to the showfile page
@requires_perm('admin')
def link_to_file(filepath, filename):
    if os.path.isfile(os.path.join(filepath, filename)):
        item = db.File.objects(filepath=filepath, filename=filename).first()
        if item is not None:
            linkURL = url_for('mongomanager.showfile', 
                              id=str(item.id))
            link = '<a href="'+linkURL+'">'+str(item.filename)+'</a>'
        else:
            link = str(filename) + ' [Not indexed]'
    else:
        linkURL = url_for('mongomanager.render_directory',
                          path=os.path.join(filepath, filename))
        link = "<a href='"+linkURL+"'>"+str(filename)+"</a>"
    return link
mongomanager.add_app_template_global(link_to_file)

# Construct a link to the parent directory
@requires_perm('admin')
def link_to_parent_dir(path):
    parentpath = os.path.abspath(os.path.join(path,'..'))
    link = ("<a href='" + url_for('mongomanager.render_directory',
                                  path=parentpath) + "'>../</a>")
    return link
mongomanager.add_app_template_global(link_to_parent_dir)

@mongomanager.route('/dir/<path:path>')
@requires_perm('admin')
def render_directory(path):
    path = '/' + path # Add the full root slash on
    # if os.path.realpath(path).startswith(SAFEPATH):
    if True:
        pathItems = os.listdir(path)
        return render_template('showdir.html', 
                               path=path, 
                               pathItems=pathItems)
    else:
        session['requestpath'] = request.path
        return redirect('/nopermission')

# Utility function for rendering reference fields as links
@requires_perm('admin')
def render_item(itemkey, item, parent):
    try:
        parentclass = parent.__class__.__name__
        # If the item is a File object, catch it and render a link to 
        # the file viewing page
        if (itemkey == 'filename'):
            linkURL = url_for('mongomanager.showfile', id=str(parent.id))
            link = "<a href='"+linkURL+"'>"+str(item)+"</a>"
            return link
        elif (itemkey == 'filepath'):
            linkURL = url_for('mongomanager.render_directory',
                              path=str(item)[1:])
            link = "<a href='"+linkURL+"'>"+str(item)+"</a>"
            return link
        # If the item is a reference object with fields, link to the 
        # reference page
        elif hasattr(item,'_fields'):
            linkURL = url_for('mongomanager.object', 
                              className=item.__class__.__name__, 
                              id=str(item.id))
            if 'name' in item._fields.keys():
                linkText = item.name
            elif 'username' in item._fields.keys():
                linkText = item.username
            elif 'role' in item._fields.keys():
                linkText = item.role
            else:
                linkText = "&lt;"+item.__class__.__name__+"&gt;"
            link = "<a href='"+linkURL+"'>"+linkText+"</a>"
            return link
        # If the item is an ObjectId, link to its reference page
        elif item.__class__ is bson.objectid.ObjectId:
            linkURL = url_for('mongomanager.object', 
                              className=parentclass, 
                              id=str(item))
            link = "<a href='"+linkURL+"'>"+str(item)+"</a>"
            return link
        # If the item is a list, render each item in the list recursively
        elif item.__class__ is db.me.base.datastructures.BaseList:
            text = '['
            for subitem in item:
                text += render_item(None, subitem, item)
                text += ', '
            if len(item) > 0:
                text = text[:-2] # Remove the last comma
            text += ']'
            return text
        # If the item is a datetime, display in correct timezone
        elif item.__class__ is datetime:
            return str(item)
        # Otherwise, try to dump to a string
        else:
            return str(item)
    except:
        return sys.exc_info()
        return 'error in render_item'
# Add the route to the global namespace 
mongomanager.add_app_template_global(render_item)

# Displays a page showing a file resource
@mongomanager.route('/showfile/<id>')
@requires_perm('admin')
def showfile(id):
    fileObj = db.File.objects(id=id).first()
    stem, ext = os.path.splitext(fileObj.filetype)
    if ext == '.json':
        with open(os.path.join(fileObj.getpath(),
                               fileObj.getfilename()),'r') as f:
            jsonData = json.load(f)
        prettyData = json.dumps(jsonData, indent = 4, sort_keys=True)
        return render_template('showjson.html', 
                               fileObj=fileObj, jsonData=prettyData)
    elif ext == '.png':
        return render_template('showpng.html', fileObj=fileObj)
    else:
        # return 'implementation in progress'
        return getfile(id=id)


@mongomanager.route('/getfile/<id>')
@requires_perm('admin')
def getfile(id):
    fileObj = db.File.objects(id=id).first()
    download_name=fileObj.getfilename() + '.' + fileObj.filetype
    return send_from_directory(fileObj.getpath(), 
                             fileObj.getfilename(), 
                             as_attachment=True, 
                             attachment_filename=download_name)


# Utility route to list all the database collections
@mongomanager.route('/collections')
@requires_perm('admin')
def collections():
    classList = []
    for item in db.__dict__.keys():
        if hasattr(getattr(db,item),'_collection'):
            classList.append(getattr(db,item).__name__)
    return render_template('collections.html', classList=classList)   

# Utility route to inspect an object
@mongomanager.route('/collection/<className>/<id>')
@requires_perm('admin')
def object(className, id):
    try:
        classObj = getattr(db, className)
        anObject = classObj.objects(id=id).first()
        return render_template('object.html', anObject=anObject)
    except:
        return abort(404)

# Utility route to inspect and edit a single collection
mongomanager.app_template_global(getattr)
@mongomanager.route('/collection/<className>', methods=['GET','POST'])
@requires_perm('admin')
def collection(className):
    classObj = getattr(db, className)
    form = forms.ItemForm()
    if 'name' in classObj._fields.keys():
        itemList = classObj.objects().order_by('-iscurrent', '+name')
        form.remitem.choices = [(str(item.id),item.name) for item 
                                     in itemList if item.iscurrent]
    else:
        itemList = classObj.objects().order_by('-iscurrent', '+addeddate')
        form.remitem.choices = [(str(item.id),str(item.id)) for item 
                                     in itemList if item.iscurrent]
    form.remitem.choices.insert(0,(' ',' '))
    if request.method == 'POST' and form.validate():
        current_user = db.User.objects(id=session['userid']).first()
        if len(form.additem.data) > 0:
            try:
                newItem = classObj(name=form.additem.data,
                                addedby = current_user,
                                addeddate = datetime.utcnow(),
                                iscurrent = True)
                newItem.save()
                flash('Added item: ' + newItem.name)
                return redirect(url_for('collection', className=className))
            except:
                form.additem.errors.append('Unable to add item.')
        if form.remitem.data != ' ':
            try:
                item = classObj.objects(iscurrent=True, 
                                        id=form.remitem.data).first()
                item.update(iscurrent=False,
                        removedby=current_user,
                        removeddate=datetime.utcnow())
                item.save()
                if 'name' in classObj._fields.keys():
                    flash('Removed item: ' + item.name)
                else:
                    flash('Removed item: ' + str(item.id))
                return redirect(url_for('collection', className=className))
            except:
                form.remitem.errors.append('Item not found.')
    return render_template('collection.html',
                           form=form, itemList=itemList, 
                           classObj=classObj, className=className)

# Route for viewing and editing user roles.
@mongomanager.route('/roles', methods=['GET','POST'])
@requires_perm('admin')
def roles():
    form = forms.RoleForm()
    if request.method == 'POST' and form.validate():
        current_user = db.User.objects(id=session['userid']).first()
        existing_user = db.User.objects(username=form.username.data).first()
        if existing_user is None:
            form.username.errors.append('User does not exist.')
        else:
            existingRoles = existing_user.roleassignments
            addRole = form.addrole.data
            remRole = form.remrole.data
            if len(addRole) > 0:
                newRole = db.RoleAssignment(role=addRole,
                            user = existing_user,
                            addedby = current_user,
                            addeddate = datetime.utcnow(),
                            iscurrent = True)
                newRole.save()
                existing_user.update(
                        roleassignments=existingRoles.append(newRole))
                existing_user.save()
                flash('Added role: ' + addRole + 
                      ' for user: ' + existing_user.username)
            if len(remRole) > 0:
                existingRoles = db.RoleAssignment.objects(
                                    user=existing_user,
                                    role=remRole,iscurrent=True)
                if len(existingRoles) == 0:
                    form.remrole.errors.append(
                            'Role does not exist for this user.')
                for roleAssignment in existingRoles:
                    roleAssignment.update(iscurrent=False,
                                          removedby=current_user,
                                          removeddate=datetime.utcnow())
                    roleAssignment.save()
                    flash('Removed: ' + remRole + 
                          ' for: ' + existing_user.username)
    roledata = [[user.username, [roleAssign.role for roleAssign 
                 in user.roleassignments if roleAssign.iscurrent]] 
                 for user in db.User.objects(iscurrent=True)]
    return render_template('roles.html',form=form, roledata=roledata)

