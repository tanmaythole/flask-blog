from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime, timedelta
from flask_mail import Mail
import json
import math

with open('config.json', 'r') as c:
    parameters = json.load(c)["parameters"]


app = Flask(__name__)
if parameters["local_server"]==True:
    app.config["SQLALCHEMY_DATABASE_URI"] = parameters["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = parameters["prod_uri"]
db = SQLAlchemy(app)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.secret_key = 'super-secret-key'

app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = parameters['gmail_id'],
    MAIL_PASSWORD = parameters['gmail_password']
)
mail = Mail(app)

class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    msg_status = db.Column(db.String(13), nullable=False)
    reply = db.Column(db.String(500))
    date = db.Column(db.String(120))

class Blogs(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    blogpost_title = db.Column(db.String(80), nullable=False)
    blogpost_slug = db.Column(db.String(120), unique=True, nullable=False)
    blogpost_content = db.Column(db.String(500), nullable=False)
    blogpost_img = db.Column(db.String(120), unique=True, nullable=False)
    blog_cat_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(500), nullable=False)
    date = db.Column(db.String(120))



@app.route('/')
def home():
    blog = Blogs.query.filter_by().all()
    last = math.ceil(len(blog)/parameters['no_of_posts_per_page'])
    number = request.args.get('number')
    if not str(number).isnumeric():
        number = 1
    number = int(number)
    blog = blog[(number-1)*parameters['no_of_posts_per_page'] : ((number-1)*parameters['no_of_posts_per_page']) + parameters['no_of_posts_per_page'] ]

    if number==1:
        prev = '#'
        next = '/?number='+str(number+1)
    elif number==last:
        prev = '/?number='+str(number-1)
        next = '#'
    else:
        prev = '/?number='+str(number-1)
        next = '/?number='+str(number+1)

    
    # [:parameters['no_of_posts_per_page']]
    return render_template('index.html', params= parameters, blogs=blog, prev=prev, next=next)


@app.route('/about')
def about():
    return render_template('about.html', params= parameters)


@app.route('/blogpost/<string:slug>', methods=['GET'])
def blogpost(slug):
    post = Blogs.query.filter_by(blogpost_slug=slug).first()
    return render_template('blogpost.html', params= parameters, post=post)



@app.route('/contact', methods = ['GET', 'POST'])
def contact():
    if request.method=='POST':
        name = request.form.get('name')
        email = request.form.get('email')
        sub = request.form.get('subject')
        msg = request.form.get('message')

        entry = Contact(name=name, email=email, subject=sub, message=msg, msg_status='new', date=datetime.now())
        db.session.add(entry)
        db.session.commit()

        mail.send_message(
            "New Message From Blog",
            sender=email,
            recipients=[parameters['gmail_id']],
            body= "Name : "+name+"\nEmail : "+email+"\nSubject : "+sub+"\nMessage : "+msg+"."
        )

    return render_template('contact.html', params= parameters)


# Admin Section
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    blog = Blogs.query.count()
    messages = Contact.query.count()
    if('admin' in session and session['admin']==parameters['admin_username']):
        return render_template('admin/index.html',no_of_blog=blog, no_of_msgs=messages)

    if request.method=='POST':
        uname = request.form.get('username')
        passw = request.form.get('password')
        if parameters['admin_username']==uname and parameters['admin_password']==passw:
            session['admin']=uname
            return render_template('admin/index.html',no_of_blog=blog, no_of_msgs=messages)
        else:
           return redirect('/admin/login') 
    return redirect('/admin/login')

@app.route('/admin/login')
def adminlogin():
    if('admin' in session and session['admin']==parameters['admin_username']):
        return redirect('/admin')
    return render_template('admin/login.html',params=parameters)

@app.route('/admin/category')
def category():
    if('admin' in session and session['admin']==parameters['admin_username']):
        return render_template('admin/category.html')

    return redirect('/admin/login')

@app.route('/admin/blogs')
def blogs():
    if('admin' in session and session['admin']==parameters['admin_username']):
        blog = Blogs.query.filter_by().order_by(desc(Blogs.date)).all()
        return render_template('admin/blogs.html',blog=blog)

    return redirect('/admin/login')

@app.route('/admin/edit/<string:sno>', methods=['GET', 'POST'])
def addblog(sno):
    if('admin' in session and session['admin']==parameters['admin_username']):
        if request.method=='POST':
            blogTitle = request.form.get('blogTitle')
            blogSlug = request.form.get('blogSlug')
            blogContent = request.form.get('blogContent')
            status = request.form.get('status')
            date = datetime.now()

            if sno==0:
                addblogs = Blogs(blogpost_title=blogTitle, blogpost_slug=blogSlug, blogpost_content=blogContent,blogpost_img='images/slider-1.jpg', blog_cat_id=0, status=status, date=date)
                db.session.add(addblogs)
                db.session.commit()
            else:
                blog = Blogs.query.filter_by(sno=sno).first()
                blog.blogpost_title = blogTitle
                blog.blogpost_slug = blogSlug
                blog.blogpost_content = blogContent
                blog.status = status
                db.session.commit()
                return redirect("/admin/edit/"+sno)
        
        blog = Blogs.query.filter_by(sno=sno).first()
        return render_template('admin/add-blog.html', blog=blog)

    return redirect('/admin/login')

@app.route('/admin/messages')
def messages():
    if('admin' in session and session['admin']==parameters['admin_username']):
        new_messages = Contact.query.filter_by(msg_status='new').order_by(desc(Contact.date)).all()
        old_messages = Contact.query.filter_by(msg_status='replied').filter(Contact.date >= (datetime.now() - timedelta(days = 30))).order_by(desc(Contact.date)).all()
        return render_template('admin/messages.html', new_messages=new_messages, old_messages=old_messages)

    return redirect('/admin/login')

@app.route('/admin/replymsg', methods=['GET', 'POST'])
def replymsg():
    if('admin' in session and session['admin']==parameters['admin_username']):
        if request.method=='POST':
            sno = request.form.get('user_id')
            email = request.form.get('email')
            subject = request.form.get('subject')
            reply = request.form.get('reply')

            contact = Contact.query.filter_by(sno=sno).first()
            contact.msg_status = 'replied'
            contact.reply = reply
            db.session.commit()
            mail.send_message("Reply From Coding Gem", sender=parameters['gmail_id'], recipients=[email], body=reply)
            return redirect('/admin/messages')
        
        # else:
        #     return redirect('/admin/messages')
    return render_template('/admin')


@app.route('/signout')
def signout():
    if('admin' in session and session['admin']==parameters['admin_username']):
        session.clear()
    return redirect('/admin')

@app.route('/admin/deleteblog/<int:sno>')
def deleteblog(sno):
    blog = Blogs.query.filter_by(sno=sno).first()
    db.session.delete(blog)
    db.session.commit()
    return redirect('/admin/blogs')

@app.route('/admin/deletemsg/<int:sno>')
def deletemsg(sno):
    msg = Contact.query.filter_by(sno=sno).first()
    db.session.delete(msg)
    db.session.commit()
    return redirect('/admin/messages')


app.run(debug=True,port=8000)
