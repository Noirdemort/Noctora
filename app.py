from flask import Flask, render_template, request, redirect, session
from flask_caching import Cache
from werkzeug.utils import secure_filename
import random
import string
import os
import re
import pymongo
from hashlib import sha512
from OpenSSL import SSL
context = SSL.Context(SSL.TLSv1_2_METHOD)
context.use_privatekey_file('key.pem')
context.use_certificate_file('cert.pem')
# from flask_uploads import UploadSet, IMAGES, configure_uploads


app = Flask(__name__)
app.secret_key = os.urandom(24)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config["IMAGE_UPLOADS"] = "./static/images/"
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ['.png', '.jpg', '.jpeg']
ALLOWED_EXTENSIONS = set(['.png', '.jpg', '.jpeg'])


myclient = pymongo.MongoClient(
    "mongodb+srv://darkOwl:wXsAw8goWFZn6w8G@noctora-xvqmy.mongodb.net/test?retryWrites=true&w=majority")
mydb = myclient["Noctora"]
clients = mydb['clients']
transactions = mydb['transactions']
tid = mydb['tid']


def gen_hash(string, salt):
    return sha512((salt+string).encode()).hexdigest()


def salt():
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(50))


def checkFields(form, conditions):
    for con in conditions:
        if not con in form:
            return False
    return True


client_list = []


@app.before_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


@app.route('/', methods=["GET", "POST"])
def login():
    global client_list
    if request.method == "GET":
        if not client_list:
            clientele = list(clients.find().limit(10))
        else:
            clientele = client_list
        if 'username' in session:
            return render_template('index.html', clients=clientele)
        return render_template('login.html')
    else:
        data = dict(request.form)
        if not checkFields(data, ['username', 'password']):
            return "Insufficient Data!"
        print(data['password'])
        if data['username'] == 'lkgfbd@gmail.com' and gen_hash(data['password'], '') == gen_hash('lakshmi9&', ''):
            session['username'] = "lkgfbd@gmail.com"
            if not client_list:
                clientele = list(clients.find().limit(10))
            else:
                clientele = client_list
            return render_template('index.html', clients=clientele)
        else:
            return "<h1> Invalid Credentials !! </h1>"


@app.route('/search', methods=['POST'])
def search_client():
    if 'username' not in session:
        return redirect('/', code=403)

    if not checkFields(dict(request.form), ['search']):
        return "Insufficient Data!"

    keyword = dict(request.form)['search']
    keyword = keyword.lower()
    search_expr = re.compile(f".*{keyword}.*", re.I)
    search_request = {
        '$or': [
            {'file': {'$regex': search_expr}},
            {'name': {'$regex': search_expr}},
            {'pan': {'$regex': search_expr}},
            {'remarks': {'$regex': search_expr}}
        ]
    }

    global client_list
    client_list = list(clients.find(search_request))
    return redirect('/')


@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if 'username' not in session:
        return redirect('/', code=403)
    if request.method == 'GET':
        return render_template('client.html', title="Add Client", path="/add", file="", pan="", name="", remarks="", value="Add Client")
    else:
        data = dict(request.form)

        if not checkFields(data, ['file', 'name', 'pan']):
            return "Insufficient fields!"

        for field in data:
            data[field] = data[field].lower()
        if 'remarks' not in data:
            data['remarks'] = ""
        pattern = re.compile("^[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}$")

        if not bool(pattern.match(data['pan'])):
            return 'Invalid PAN format!!'

        client = {'file': data['file'], 'name': data['name'],
                  'pan': data['pan'], 'remarks': data['remarks']}

        if request.files:
            image = request.files["image"]
            extension = os.path.splitext(image.filename)[1]

            if image and extension in ALLOWED_EXTENSIONS:
                f_name = secure_filename(str(client['pan']) + extension)
                image.save(os.path.join(app.config['IMAGE_UPLOADS'], f_name))
                client['image'] = f_name
            else:
                return '<h1> Invalid image format. Go back and try again </h1>'

        clients.insert_one(client)

        return redirect('/')


@app.route('/edit/<client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'username' not in session:
        return redirect('/')

    if request.method == 'GET':
        client = clients.find_one({"pan": client_id})
        if client is None:
            return "<h1>No Such Client</h1>"
        return render_template('client.html', title="Update Client Details", path="/edit/{}".format(client_id), file=client['file'], name=client['name'], pan=client['pan'], remarks=client['remarks'], value="Update Details")
    else:

        data = dict(request.form)
        if not checkFields(data, ['file', 'name', 'pan']):
            return "Insufficient fields!"

        for field in data:
            data[field] = data[field].lower()

        if 'remarks' not in data:
            data['remarks'] = ''

        pattern = re.compile("^[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}$")

        if not bool(pattern.match(data['pan'])):
            return 'Invalid PAN format!!'

        client = {'file': data['file'], 'name': data['name'],
                  'pan': data['pan'], 'remarks': data['remarks']}

        if request.files:
            image = request.files["image"]
            extension = os.path.splitext(image.filename)[1]

            if image and extension in ALLOWED_EXTENSIONS:
                f_name = secure_filename(str(client['pan']) + extension)
                image.save(os.path.join(app.config['IMAGE_UPLOADS'], f_name))
                client['image'] = f_name
            else:
                return '<h1> Invalid image format. Go back and try again </h1>'

        clients.update_one({"pan": client_id}, {'$set': client})

        return redirect('/profile/{}'.format(client['pan']))


@app.route('/delete/<client_id>', methods=['POST'])
def delete_client(client_id):
    if 'username' not in session:
        return redirect('/')
    clients.delete_one({"pan": client_id})
    return redirect('/')


@app.route('/profile/<client_id>', methods=['GET'])
def show_profile(client_id):
    if 'username' not in session:
        return redirect('/')
    client = clients.find_one({"pan": client_id})
    if client:
        records = list(transactions.find({"client_id": client_id}))
        return render_template('profile.html', client=client, transactions=records)
    else:
        return "No Such Profile"


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' not in session:
        return redirect('/')
    data = dict(request.form)
    required_fields = ['asmtyr', 'filing_date', 'return_income', 'tax',
                       'total_charges', 'fee_granted', 'last_transaction_date', 'subject', 'client_id']
    if not checkFields(data, required_fields):
        return "<h1> Insufficient fields! </h1>"
    info = {}
    for field in required_fields:
        info[field] = data[field]
    t_id = salt()
    get_tid = tid.find_one({"id": t_id})
    while get_tid:
        t_id = salt()
        get_tid = tid.find_one({"id": t_id})
    info['id'] = t_id
    tid.insert_one({"id": t_id})
    transactions.insert_one(info)
    return redirect('/profile/{}'.format(data['client_id']))


@app.route('/edit_transaction', methods=['POST'])
def edit_transaction():
    if 'username' not in session:
        return redirect('/')
    data = dict(request.form)
    required_fields = ['id', 'asmtyr', 'filing_date', 'return_income', 'tax',
                       'total_charges', 'fee_granted', 'last_transaction_date', 'subject', 'client_id']
    if not checkFields(data, required_fields):
        return "<h1> Insufficient fields! </h1>"
    info = {}
    for field in required_fields:
        info[field] = data[field]
    transactions.update_one({"id": data['id']}, {'$set': info})
    return redirect('/profile/{}'.format(data['client_id']))


@app.route('/delete_transaction', methods=['POST'])
def delete_transaction():
    if 'username' not in session:
        return redirect('/')
    if not checkFields(dict(request.form), ['id']):
        return "Insufficient Data!"
    transaction_id = dict(request.form)['id']
    transaction = transactions.find_one({"id": transaction_id})
    if transaction:
        transactions.delete_one({"id": transaction_id})
        return redirect('/profile/{}'.format(transaction['client_id']))
    return "No such transaction"


@app.route('/revenue', methods=['GET'])
def revenue():
    return "Not Implemented Yet! Coming Soon..."


@app.route('/logout', methods=['GET'])
def logout():
    if 'username' in session:
        del session['username']
    return redirect('/')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port,
            ssl_context=('cert.pem', 'key.pem'))
