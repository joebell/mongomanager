# mongomanager.database.py
import mongoengine as me
from flask_mongoengine import MongoEngine 
from flask_mongoengine.wtf import model_form
from pymongo.errors import DuplicateKeyError
from mongoengine import NotUniqueError
from datetime import datetime
import os
import hashlib

eng = MongoEngine()

class TrackedAssignment(me.Document):
    addedby = me.ReferenceField('User', required=True)
    addeddate = me.DateTimeField(required=True, default=datetime.now)
    iscurrent = me.BooleanField(required=True, default=True)
    removedby = me.ReferenceField('User', required=False)
    removeddate = me.DateTimeField(required=False)
    modifieddate = me.DateTimeField(required=True, default=datetime.now)
    meta = {'allow_inheritance': True,
            'abstract': True}
    def update(self, *args, **kwargs):
        result = super(TrackedAssignment, self).update(
                modifieddate=datetime.now(), *args, **kwargs)
        return result


class RoleAssignment(TrackedAssignment):
    role = me.StringField(required=True)
    user = me.ReferenceField('User', required=True)

class User(TrackedAssignment):
    username     = me.StringField(required=True, unique=True)
    firstname    = me.StringField(required=True)
    lastname     = me.StringField(required=True)
    email        = me.StringField(required=True)
    passwordhash = me.StringField(required=True)
    roleassignments = me.ListField(me.ReferenceField(RoleAssignment), 
                    required=False, default=[])

class File(TrackedAssignment):
    filetype   = me.StringField(required=True, default='')
    hashstring = me.StringField(required=True, default='')
    basepath   = me.StringField(required=True, default='')
    filepath   = me.StringField(required=True, default='')
    filename   = me.StringField(required=True, default='')


    def getpath(self):
        fullpath = os.path.join(self.basepath,
                                self.hashstring[0:2],
                                self.hashstring[2:4],
                                self.hashstring[4:6])
        return fullpath
    
    def getfilename(self):
        return self.hashstring[6:]

    def write(self, data):
        dataHash = hashlib.sha256(data)
        try:
            while True:
                self.hashstring=dataHash.hexdigest()
                self.filepath = self.getpath()
                if not os.path.exists(self.filepath):
                    os.makedirs(self.filepath)
                self.filename = self.getfilename()
                fullfilename = os.path.join(self.filepath, 
                                            self.filename)
                print(fullfilename)
                # If the filename exists already
                if os.path.exists(fullfilename):
                    with open(fullfilename,'rb') as f:
                        existingData = f.read()
                    # If it's the same file, keep the hashstring
                    if data == existingData:
                        print('File duplicate found, ' +
                              'linking to duplicate.')
                        self.iscurrent = True
                        self.save()
                        return True
                    # If it's not identical increment the hash and try again
                    else:
                        print('File hash collision, incrementing hash')
                        dataHash.update('1'.encode('utf-8'))
                # If we haven't already stored a file with that hash, 
                # save it.
                else:
                    print('Writing new file.')
                    with open(fullfilename,'wb+') as f:
                        f.write(data)
                    self.iscurrent = True
                    self.save()
                    return True
        except:         
            print(traceback.print_exc())

    def read(self):
        try:
            fullpath = self.getpath()
            filename = os.path.join(fullpath, self.getfilename())
            with open(filename,'rb') as f:
                data = f.read()
            return data
        except:     
            print(traceback.print_exc())


