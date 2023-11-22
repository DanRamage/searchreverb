from flask_security import RoleMixin, UserMixin

from app import db

# Define models


class Roles_Users(db.Model):
    __tablename__ = "roles_users"
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"), primary_key=True)
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"), primary_key=True)


"""
Roles_Users = db.Table(
    'roles_users',
    db.Model.metadata,
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)
"""


class Role(db.Model, RoleMixin):
    __tablename__ = "role"
    id = db.Column(db.Integer(), primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


# Create user model.
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))
    last_login_date = db.Column(db.String(32))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    zipcode = db.Column(db.String(10))
    city = db.Column(db.String(255))
    state = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    active = db.Column(db.Boolean())
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.Text)
    """
    roles = db.relationship('Role',
                            secondary=Roles_Users,
                            backref=db.backref('user', lazy='dynamic'))

    """
    roles = db.relationship(
        Role,
        secondary="roles_users",
        primaryjoin=(Roles_Users.user_id == id),
        backref="user",
    )
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)

    #    roles = db.relationship('Role',
    #                            secondary=roles_users,
    #                            backref=db.backref('user', lazy='dynamic'))

    def set_encrypted_password(self, password):
        self.password = password

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def is_admin_user(self):
        for role in self.roles:
            if role.name == "admin":
                return True
        return False

    # Required for administrative interface
    def __unicode__(self):
        return self.login
