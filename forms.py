# forms.py
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SelectField, HiddenField
from wtforms import validators

Alphanumeric = validators.Regexp(r'^[\w]+$', 
        message='Alphanumeric characters only.')

class RegistrationForm(FlaskForm):
    username = StringField('User name', [Alphanumeric, 
                            validators.InputRequired()])
    firstname = StringField('First name',[validators.InputRequired()])
    lastname = StringField('Last name',[validators.InputRequired()])
    email = StringField('Email', [validators.InputRequired(), 
                        validators.Email()])
    password = PasswordField('Password',
        [validators.InputRequired(),
         validators.Length(min=7, 
             message='Password must be >= 7 characters'),
         validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm Password', 
                            [validators.InputRequired()])

class LoginForm(FlaskForm):
    username = StringField('Username:', [validators.InputRequired()])
    password = PasswordField('Password:', [validators.InputRequired()])

class RoleForm(FlaskForm):
    username = StringField('Username:', [validators.InputRequired()])
    addrole = StringField('Role to add:', 
                          [Alphanumeric, 
                           validators.Optional(strip_whitespace=False)])
    remrole = StringField('Role to remove:', 
                          [Alphanumeric, 
                           validators.Optional(strip_whitespace=False)])

class ItemForm(FlaskForm):
    additem = StringField('Item to add:')
    remitem = SelectField('Item to remove:')

