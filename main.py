from flask import Flask, render_template, jsonify, request, url_for, redirect, flash, abort
from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_sqlalchemy import SQLAlchemy
from distutils.util import strtobool
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from functools import wraps
from flask_ckeditor import CKEditorField
from flask_bootstrap import Bootstrap5
import os
import secrets


app  = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy()
Bootstrap5(app)
db.init_app(app)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
secret_key = secrets.token_hex(16)
app.secret_key = secret_key

login_manager = LoginManager()

login_manager.init_app(app)


class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    coffee_price = db.Column(db.String(250), nullable=False)
    comments = db.relationship('Comment', backref='cafe')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    comments = db.relationship('Comment', backref='user')

   


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)


class CommentForm(FlaskForm):
    comments = CKEditorField('Your Experience', render_kw={'class': 'ckeditor'})
    submit = SubmitField('Post')
    

    
    

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def login_required(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_func


@app.route("/")
def home():
    results = db.session.execute(db.select(Cafe).order_by(Cafe.name))
    cafes = results.scalars().all()
    return render_template("index.html", cafes=cafes)



@app.route("/cafe/<cafe_id>", methods=['POST', 'GET'])
def view_cafe(cafe_id):
    form = CommentForm()
    cafe = db.get_or_404(Cafe, cafe_id)
    if form.validate_on_submit():
        new_comment = Comment(
            text = form.comments.data,
            user_id = current_user.id,
            cafe_id = cafe_id
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("cafe.html", cafe=cafe, form=form)


@app.route("/register",  methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        result = db.session.execute(db.select(User).where(User.email==email))
        user = result.scalar()
        if not user:
            password = generate_password_hash(password, salt_length=10)
            new_user = User(
                email = email,
                password = password
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
        else:
            flash("Email already Exists! ")
            
    return render_template("register.html")

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        result = db.session.execute(db.select(User).where(User.email==email))
        user = result.scalar()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash ("Incorrect Password!")
        else:
            flash ("User not Found!")
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/add_cafe", methods=["POST", "GET"])
@login_required
def add_cafe():
    if request.method == "POST":
        try:
            new_cafe = Cafe(
                name=request.form["cafeName"],
                map_url=request.form["mapUrl"],
                img_url=request.form["imgUrl"],
                location=request.form["location"],
                has_sockets=bool(strtobool(request.form["hasSockets"])),
                has_toilet=bool(strtobool(request.form["hasToilet"])),
                has_wifi=bool(strtobool(request.form["hasWifi"])),
                can_take_calls=bool(strtobool(request.form["canTakeCalls"])),
                seats=int(request.form["seats"]),
                coffee_price=float(request.form["coffeePrice"])
            )
            db.session.add(new_cafe)
            db.session.commit()
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback() 
            print(f"Error adding cafe to database: {e}")
            return render_template("error.html", error_message="Error adding cafe to database")

    return render_template("add_cafe.html")


@app.route("/delete/<cafe_id>")
@login_required
def delete_cafe(cafe_id):
    cafe = db.session.get(Cafe, cafe_id)
    if cafe:
        comments = Comment.query.filter_by(cafe_id=cafe.id).all()
        for comment in comments:
            db.session.delete(comment)
        db.session.delete(cafe)
        db.session.commit()
        return redirect(url_for('home'))
    else:
        return render_template("error.html", error_message=f"No Cafe with id {cafe_id} found!")


@app.route("/about-me")
def about_me():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
