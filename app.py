from turtle import update
from flask import Flask, render_template, request, redirect, session, url_for
from flask_bootstrap import Bootstrap5
from flask_mongoengine import MongoEngine
from flask_mongoengine.wtf import model_form
from flask_paginate import Pagination, get_page_parameter
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import bcrypt

app = Flask(__name__)
bootstrap = Bootstrap5(app)
db = MongoEngine()

app.config['MONGO_DBNAME'] = 'test2'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/test2'
mongo = PyMongo(app)

app.config['MONGODB_SETTINGS'] = {
    'host': 'mongodb://localhost/test2'
}
app.config['SECRET_KEY'] = 'inikuncirahasiasaya'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Kategori(db.DynamicDocument):
    namaKategori = db.StringField()
    kategori = db.StringField()
    meta = {'collection': 'category'}
    pass


class Dokumen(db.Document):
    judul = db.StringField(required=True)
    penulis = db.StringField(required=True)
    tanggal = db.DateField(required=True)
    tags = db.StringField(required=True)
    description = db.StringField(required=True)
    kategori = db.StringField(required=True,
                              choices=[(a.namaKategori, a.kategori) for a in Kategori.objects()])
    jumlahBaca = db.IntField(default=0)
    meta = {'collection': 'news'}


class JumlahBaca(db.Document):
    jumlahBaca = db.IntField(default=0)
    meta = {'collection': 'news'}


class Users(UserMixin, db.Document):
    username = db.StringField()
    email = db.StringField()
    password = db.StringField()
    meta = {'collection': 'users'}


@login_manager.user_loader
def load_user(id):
    return Users.objects(id=id).first()


DokumenForm = model_form(Dokumen, field_args={'judul': {'label': 'Judul Berita'}, 'penulis': {'label': 'Penulis'}, 'tanggal': {
                         'label': 'Tanggal Tulisan'}, 'description': {'label': 'Deskripsi'}, 'kategori': {'label': 'Kategori Berita'}, 'tags': {'label': 'Tags'}})


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    news = mongo.db.news
    # Popular
    popular = Dokumen.objects.order_by('-jumlahBaca').limit(5)
    # Kategori
    kategori = Kategori.objects.order_by('namaKategori').limit(5)
    # Tags
    # tags = news.aggregate([{"$group": {"_id": "$tags"}}, {"$sort": {"_id": 1}}])
    tags = news.aggregate([{"$group": {"_id": "$tags", "myCount": {"$sum": 1}}},
                          {"$sort": {"myCount": -1}}, {"$limit": 10}])
    # Date
    tahun = Dokumen.objects().aggregate([{"$group": {"_id": {"$year": "$tanggal"}}},
                                         {"$project": {"tahun": "$_id"}}, {"$sort": {"tahun": 1}}])
    # pagination
    try:
        halaman = request.args.get('halaman')
        halaman = int(halaman)
    except:
        halaman = 1

    per_page = 4
    data = Dokumen.objects().paginate(halaman, per_page).items
    jdata = len(Dokumen.objects)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    pagination = Pagination(
        page=page, total=jdata, record_name='data', format_total=True, format_number=True)
    return render_template('home.html', data=data, halaman=halaman, jdata=jdata, pagination=pagination, kategori=kategori, popular=popular, tag=tags, tahun=tahun)


# Tulis Berita (Admin)


@app.route('/formData', methods=['GET', 'POST'])
@login_required
def formData():
    form = DokumenForm()
    if request.method == 'POST':
        data = form.data
        del data['csrf_token']
        simpan = Dokumen(**data).save()
        return redirect(url_for('home'))
    return render_template('form.html', form=form)


# Detail Berita


@app.route('/post/<id>')
def post(id):
    news = mongo.db.news
    # Popular
    popular = Dokumen.objects.order_by('-jumlahBaca').limit(5)
    # Kategori
    kategori = Kategori.objects.order_by('namaKategori').limit(5)
    # Tags
    # tags = news.aggregate([{"$group": {"_id": "$tags"}}, {"$sort": {"_id": 1}}])
    tags = news.aggregate([{"$group": {"_id": "$tags", "myCount": {"$sum": 1}}},
                          {"$sort": {"myCount": -1}}, {"$limit": 10}])
    data = Dokumen.objects(id=id).first()
    jumlahBacaNew = data["jumlahBaca"]+1
    update = news.update_one(
        {"_id": ObjectId(id)}, {"$set": {"jumlahBaca": jumlahBacaNew}})
    return render_template('post.html', data=data, popular=popular, kategori=kategori, tags=tags)

# Halaman Admin


@app.route('/admin')
@login_required
def admin():
    # login
    data = Dokumen.objects()
    if 'username' in session:
        return render_template('admin.html', data=data), session['username']
    return render_template('admin.html', data=data)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated == True:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        check_user = Users.objects(email=request.form['email']).first()
        if check_user:
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), check_user['password'].encode('utf-8')) == check_user['password'].encode('utf-8'):
                session['username'] = check_user['username']
                login_user(check_user)
                return redirect(url_for('admin'))
        return 'Invalid email/password combination'
    return render_template('login.html')


@ app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        existing_user = Users.objects(email=request.form['email']).first()
        if existing_user is None:
            hashpass = bcrypt.hashpw(
                request.form['password'].encode('utf-8'), bcrypt.gensalt())
            hey = Users(
                username=request.form['username'], email=request.form['email'], password=hashpass).save()
            session['username'] = request.form['username']
            login_user(hey)
            return redirect(url_for('admin'))
        return 'That email already exists!'
    return render_template('register.html')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Hapus Berita (Admin)


@ app.route('/deleteNews/<id>')
@login_required
def deleteNews(id):
    data = Dokumen.objects(id=id).delete()
    return redirect(url_for('admin'))


# Edit Berita (Admin)


@ app.route('/formEdit/<id>', methods=['GET', 'POST'])
@login_required
def editNews(id):
    data = Dokumen.objects(id=id).first()
    form = DokumenForm(obj=data)
    if request.method == 'POST':
        data = form.data
        del data['csrf_token']
        update = Dokumen.objects(id=id).update(**data)
        return redirect(url_for('admin'))
    return render_template('formEdit.html', form=form)

# Filter by Category


@app.route('/category/<kategori>')
@app.route('/category/<kategori>/<awal>')
def kategori(kategori, awal=0):
    news = mongo.db.news
    # Popular
    popular = Dokumen.objects.order_by('-jumlahBaca').limit(5)
    # Kategori
    filter_kategori = Kategori.objects.order_by('namaKategori').limit(5)
    # Tags
    # tags = news.aggregate([{"$group": {"_id": "$tags"}}, {"$sort": {"_id": 1}}])
    tags = news.aggregate([{"$group": {"_id": "$tags", "myCount": {"$sum": 1}}},
                          {"$sort": {"myCount": -1}}, {"$limit": 10}])
    # pagination
    awal = int(awal)
    data = Dokumen.objects(kategori=kategori).skip(awal).limit(4)
    kategori_data = news.find_one({'kategori': kategori})
    jdata = len(Dokumen.objects(kategori=kategori))
    return render_template('category.html', data=data, filter_kategori=filter_kategori, popular=popular, awal=awal, jdata=jdata, kategori_data=kategori_data, tag=tags)


# Filter by Tags
@app.route('/tags/<tag>')
@app.route('/tags/<tag>/<awal>')
def tags(tag, awal=0):
    news = mongo.db.news
    # Popular
    popular = Dokumen.objects.order_by('-jumlahBaca').limit(5)
    # Kategori
    filter_kategori = Kategori.objects.order_by('namaKategori').limit(5)
    # Tags
    tags = news.aggregate([{"$group": {"_id": "$tags", "myCount": {"$sum": 1}}},
                          {"$sort": {"myCount": -1}}, {"$limit": 10}])
    # pagination
    awal = int(awal)
    data = Dokumen.objects(tags=tag).skip(awal).limit(4)
    tags_data = news.find_one({'tags': tag})
    jdata = len(Dokumen.objects(tags=tag))
    return render_template('tags.html', data=data, filter_kategori=filter_kategori, popular=popular, awal=awal, jdata=jdata, tags_data=tags_data, tag=tags)

# Filter by date


@app.route('/date/<tahun>/<bulan>')
@app.route('/date/<tahun>/<bulan>/<awal>')
def date(tahun, bulan, awal=0):
    news = mongo.db.news
    # Popular
    popular = Dokumen.objects.order_by('-jumlahBaca').limit(5)
    # Kategori
    filter_kategori = Kategori.objects.order_by('namaKategori').limit(5)
    # Tags
    tags = news.aggregate([{"$group": {"_id": "$tags", "myCount": {"$sum": 1}}},
                          {"$sort": {"myCount": -1}}, {"$limit": 10}])
    # Date
    tanggal1 = "%s-%s-01" % (tahun, str(int(bulan)+1).zfill(2))
    tanggal2 = "%s-%s-01" % (tahun, str(int(bulan)).zfill(2))
    tahun = Dokumen.objects().aggregate([{"$project": {"tahun_buat": {
        "$year": "$tanggal"}, "bulan_buat": {"$month": "$tanggal"}}}])
    # Pagination
    awal = int(awal)
    data = Dokumen.objects(tanggal__gte=tanggal2,
                           tanggal__lt=tanggal1).order_by('-tanggal').skip(awal).limit(4)
    tahun_data = news.find_one({'tanggal': tanggal2[:4]})
    bulan_data = news.find_one({'tanggal': tanggal2[5:7]})
    print(tanggal2[5:7])
    jdata = len(Dokumen.objects(tanggal__gte=tanggal2,
                tanggal__lt=tanggal1).order_by('-tanggal'))
    return render_template('date.html', data=data, filter_kategori=filter_kategori, popular=popular, awal=awal, jdata=jdata, tahun=tahun, bulan=bulan, tag=tags, tahun_data=tahun_data, bulan_data=bulan_data, tanggal2=tanggal2)

# about


@ app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
