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
app.secret_key = 'ABCDE10293JSS_DSJHSJHSJD_DHABCJHSB_SKJADNCKSANJK_ASSCNANWDJAK'
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config["IMAGE_UPLOADS"] = "./static/images/"
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ['.png', '.jpg', '.jpeg']
ALLOWED_EXTENSIONS = set(['.png', '.jpg', '.jpeg'])

mongo_url = "mongodb+srv://darkOwl:wXsAw8goWFZn6w8G@noctora-xvqmy.mongodb.net/test?retryWrites=true&w=majority"

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = myclient["Noctora"]
clients = db['clients']
transactions = db['transactions']
fees = db['fees']
subrecs = db['subrecs']
tid = db['tid']
fid = db['fid']
sid = db['sid']


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
        return redirect('/')
    if request.method == 'GET':
        return render_template('client.html', title="Add Client", path="/add", file="", pan="", name="", remarks="", mobile="", value="Add Client")
    else:
        data = dict(request.form)

        if not checkFields(data, ['file', 'name', 'pan']):
            return "Insufficient fields!"

        for field in data:
            data[field] = data[field].lower()
        if 'remarks' not in data:
            data['remarks'] = ""

        if 'phone' not in data:
            data['phone'] = ""

        pattern = re.compile("^[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}$")

        if not bool(pattern.match(data['pan'])):
            return 'Invalid PAN format!!'

        client = {'file': data['file'], 'name': data['name'],
                  'pan': data['pan'], 'remarks': data['remarks'], "phone": data['phone']}

        if request.files:
            image = request.files["image"]
            extension = os.path.splitext(image.filename)[1]

            if image and extension in ALLOWED_EXTENSIONS:
                f_name = secure_filename(str(client['pan']) + extension)
                image.save(os.path.join(app.config['IMAGE_UPLOADS'], f_name))
                client['image'] = f_name

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
        return render_template('client.html', title="Update Client Details", path="/edit/{}".format(client_id), file=client['file'], name=client['name'], pan=client['pan'], remarks=client['remarks'], mobile=client['phone'], value="Update Details")
    else:

        data = dict(request.form)
        if not checkFields(data, ['file', 'name', 'pan']):
            return "Insufficient fields!"

        for field in data:
            data[field] = data[field].lower()

        if 'remarks' not in data:
            data['remarks'] = ''

        if 'phone' not in data:
            data['phone'] = ''
        else:
            if len(data['phone'].strip()) != 10:
                return "Inavlid Phone Number. Please Check phone number again!"

        pattern = re.compile("^[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}$")

        if not bool(pattern.match(data['pan'])):
            return 'Invalid PAN format!!'

        client = {'file': data['file'], 'name': data['name'],
                  'pan': data['pan'], 'remarks': data['remarks'], 'phone': data['phone'].strip()}

        if request.files:
            image = request.files["image"]
            extension = os.path.splitext(image.filename)[1]

            if image and extension in ALLOWED_EXTENSIONS:
                f_name = secure_filename(str(client['pan']) + extension)
                image.save(os.path.join(app.config['IMAGE_UPLOADS'], f_name))
                client['image'] = f_name

        clients.update_one({"pan": client_id}, {'$set': client})

        return redirect('/profile/{}'.format(client['pan']))


@app.route('/delete/<client_id>', methods=['POST'])
def delete_client(client_id):
    if 'username' not in session:
        return redirect('/')
    client = clients.find_one({"pan": client_id})
    if client:
        clients.delete_one({"pan": client_id})
        return redirect('/')
    else:
        return "<h1>No such Client </h1>"


@app.route('/profile/<client_id>', methods=['GET'])
def show_profile(client_id):
    if 'username' not in session:
        return redirect('/')
    client = clients.find_one({"pan": client_id})
    if client:
        records = list(transactions.find({"client_id": client_id}))
        fee_records = list(fees.find({"client_id": client_id}))
        all_subrecs = {}
        for i in fee_records:
            i['total_charges'] = float(i['total_charges'])
            i['fee_granted'] = float(i['fee_granted'])
            sb = list(subrecs.find({'fid': i['id']}))
            for j in sb:
                j['fee_granted'] = float(j['fee_granted'])
            all_subrecs[i['id']] = sb
        
        return render_template('profile.html', client=client, transactions=records, fees=fee_records, subrecs=all_subrecs)
    else:
        return "No Such Profile"


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' not in session:
        return redirect('/')
    data = dict(request.form)
    required_fields = ['asmtyr', 'filing_date',
                       'return_income', 'tax', 'client_id']
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
    required_fields = ['id', 'asmtyr', 'filing_date',
                       'return_income', 'tax', 'client_id']
    if not checkFields(data, required_fields):
        return "<h1> Insufficient fields! </h1>"
    info = {}
    for field in required_fields:
        info[field] = data[field]
    transactions.update_one({"id": data['id']}, {'$set': info})
    return redirect('/profile/{}'.format(data['client_id']))


@app.route('/add_fee', methods=['POST'])
def add_receipt():
    if 'username' not in session:
        return redirect('/')
    data = dict(request.form)
    required_fields = ['total_charges', 'fee_granted',
                       'transaction_date', 'client_id']
    if not checkFields(data, required_fields):
        return '<h1> Insufficient Fields! </h1>'
    info = {}
    for field in required_fields:
        info[field] = data[field]

    t_id = salt()
    get_tid = fid.find_one({"id": t_id})
    while get_tid:
        t_id = salt()
        get_tid = fid.find_one({"id": t_id})
    info['id'] = t_id
    fid.insert_one({"id": t_id})
    fees.insert_one(info)

    record = { 'fee_granted': data['fee_granted'], 'transaction_date': data['transaction_date'], 'client_id': data['client_id'], 'fid': info['id']}
    
    t_id = salt()
    get_tid = sid.find_one({"id": t_id})
    while get_tid:
        t_id = salt()
        get_tid = sid.find_one({"id": t_id})
    record['id'] = t_id
    sid.insert_one({"id": t_id})
    subrecs.insert_one(record)
    return redirect('/profile/{}'.format(data['client_id']))


@app.route('/delete_fee', methods=['POST'])
def delete_receipt():
    if 'username' not in session:
        return redirect('/')
    if not checkFields(dict(request.form), ['id']):
        return "Insufficient Data!"
    transaction_id = dict(request.form)['id']
    transaction = fees.find_one({"id": transaction_id})
    if transaction:
        fees.delete_one({"id": transaction_id})
        fid.delete_one({"id": transaction_id})
        return redirect('/profile/{}'.format(transaction['client_id']))
    return "No such transaction"


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
        tid.delete({"id": transaction_id})
        recors = subrecs.find({"fid": transaction_id})
        for rec in recors:
            sid.delete_one({"id": rec['id']})
        subrecs.delete_many({"fid": transaction_id})
        return redirect('/profile/{}'.format(transaction['client_id']))
    return "No such transaction"


@app.route('/add_subrecord', methods=['POST'])
def add_subrecord():
    if 'username' not in session:
        return redirect('/')

    data = dict(request.form)
    required_fields = ['fee_granted', 'transaction_date', 'client_id', 'fid']

    if not checkFields(data, required_fields):
        return "<h1> Insuffiecient Fields! </h1>"

    info = {}
    for field in required_fields:
        info[field] = data[field]

    t_id = salt()
    get_tid = sid.find_one({"id": t_id})
    while get_tid:
        t_id = salt()
        get_tid = sid.find_one({"id": t_id})
    info['id'] = t_id
    sid.insert_one({"id": t_id})
    subrecs.insert_one(info)
    return redirect('/profile/{}'.format(data['client_id']))


@app.route('/delete_subrecord', methods=['POST'])
def delete_subrecord():
    if 'username' not in session:
        return redirect('/')
    if not checkFields(dict(request.form), ['id']):
        return "Insufficient Data!"
    transaction_id = dict(request.form)['id']
    transaction = subrecs.find_one({"id": transaction_id})
    if transaction:
        subrecs.delete_one({"id": transaction_id})
        sid.delete_one({"id": transaction_id})
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
    app.run(debug=True,host='0.0.0.0', port=port,
            ssl_context=('cert.pem', 'key.pem'))
