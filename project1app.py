from flask import Flask, request, redirect, render_template_string
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_bcrypt import Bcrypt
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# ================= DATABASE =================
def db():
    conn = sqlite3.connect("portal.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = db()
    c = conn.cursor()

    c.executescript("""
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS attendance;
    DROP TABLE IF EXISTS leaves;
    DROP TABLE IF EXISTS salary;
    DROP TABLE IF EXISTS messages;
    DROP TABLE IF EXISTS reports;
    """)

    c.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, role TEXT)")
    c.execute("CREATE TABLE attendance(id INTEGER PRIMARY KEY, name TEXT, date TEXT, checkin TEXT, checkout TEXT)")
    c.execute("""CREATE TABLE leaves(
        id INTEGER PRIMARY KEY,
        name TEXT,
        from_date TEXT,
        to_date TEXT,
        return_date TEXT,
        days TEXT,
        reason TEXT,
        status TEXT
    )""")
    c.execute("CREATE TABLE salary(id INTEGER PRIMARY KEY, name TEXT, amount INT, status TEXT)")
    c.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, message TEXT)")
    c.execute("CREATE TABLE reports(id INTEGER PRIMARY KEY, name TEXT, report TEXT, admin_comment TEXT)")

    employees = ["Vaishnavi U","Varsha V","Ganasri R","Priya J","Anusri A","Harshni M"]

    for i, name in enumerate(employees):
        email = name.replace(" ","").lower()+"@mail.com"
        pwd = bcrypt.generate_password_hash("123").decode("utf-8")

        c.execute("INSERT INTO users VALUES (?,?,?,?,?)",(i+1,name,email,pwd,"Employee"))
        c.execute("INSERT INTO salary VALUES (?,?,?,?)",(i+1,name,30000,"Pending"))
        c.execute("INSERT INTO reports VALUES (?,?,?,?)",(i+1,name,"Work submitted",""))

    c.execute("INSERT INTO users VALUES (100,'Admin','admin@mail.com',?,?)",
              (bcrypt.generate_password_hash("admin123").decode("utf-8"),"Admin"))
    c.execute("INSERT INTO salary VALUES (100,'Admin',50000,'Pending')")

    conn.commit()
    conn.close()

init()

# ================= USER =================
class User(UserMixin):
    def __init__(self,id,name,email,password,role):
        self.id=id
        self.name=name
        self.email=email
        self.password=password
        self.role=role


@login_manager.user_loader
def load_user(user_id):
    conn=db()
    u=conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return User(*u) if u else None

# ================= UI TEMPLATE =================
def layout(title, body):
    portal = "Admin Portal" if current_user.role=="Admin" else "Employee Portal"

    return render_template_string(f"""
<html>
<head>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body{{background:#eef2f7}}
.sidebar{{
width:230px;height:100vh;position:fixed;
background:#0f172a;color:white;padding-top:20px;
}}
.sidebar a{{
display:block;color:#cbd5e1;padding:12px;
text-decoration:none;
}}
.sidebar a:hover{{background:#1e293b;color:white}}
.content{{margin-left:240px;padding:25px}}
</style>
</head>

<body>

<div class="sidebar">
<h4 class="text-center text-info">{portal}</h4>
<a href="/dashboard">Dashboard</a>
<a href="/attendance">Attendance</a>
<a href="/leave">Leave</a>
<a href="/salary">Salary</a>
<a href="/chat">Chat</a>
<a href="/report">Reports</a>
<a href="/logout" style="color:red">Logout</a>
</div>

<div class="content">
<h3 class="text-primary">{title}</h3>
{body}
</div>

</body>
</html>
""")

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        conn=db()
        u=conn.execute("SELECT * FROM users WHERE email=?", (request.form["email"],)).fetchone()

        if u and bcrypt.check_password_hash(u["password"], request.form["password"]):
            login_user(User(*u))
            return redirect("/dashboard")

    return """
    <div style="display:flex;justify-content:center;align-items:center;height:100vh">
    <form method="POST" class="card p-4">
    <h3>Login</h3>
    <input name="email" class="form-control" placeholder="Email"><br>
    <input type="password" name="password" class="form-control" placeholder="Password"><br>
    <button class="btn btn-primary w-100">Login</button>
    </form>
    </div>
    """

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    conn=db()

    leaves = conn.execute("SELECT COUNT(*) FROM leaves WHERE status='Pending'").fetchone()[0]
    salary = conn.execute("SELECT COUNT(*) FROM salary WHERE status='Pending'").fetchone()[0]
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    return layout("Dashboard",f"""
    <div class="row g-3">

    <div class="col-md-4"><div class="card p-3 bg-primary text-white">Employees<br><h3>{users}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 bg-warning">Leaves Pending<br><h3>{leaves}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 bg-danger text-white">Salary Pending<br><h3>{salary}</h3></div></div>

    </div>
    """)

# ================= ATTENDANCE =================
@app.route("/attendance", methods=["GET","POST"])
@login_required
def attendance():
    conn=db()

    if request.method=="POST":
        conn.execute("INSERT INTO attendance(name,date,checkin,checkout) VALUES (?,?,?,?)",
        (request.form["name"],request.form["date"],
         request.form["checkin"]+" "+request.form["ampm1"],
         request.form["checkout"]+" "+request.form["ampm2"]))
        conn.commit()

    if current_user.role=="Admin":
        data = conn.execute("SELECT * FROM attendance").fetchall()
    else:
        data = conn.execute("SELECT * FROM attendance WHERE name=?", (current_user.name,)).fetchall()

    html="""
    <form method="POST" class="card p-3">
    Name:<input name="name" class="form-control"><br>
    Date:<input type="date" name="date" class="form-control"><br>

    Check In:<input type="time" name="checkin">
    <select name="ampm1"><option>AM</option><option>PM</option></select><br>

    Check Out:<input type="time" name="checkout">
    <select name="ampm2"><option>AM</option><option>PM</option></select><br><br>

    <button class="btn btn-success">Save</button>
    </form><br>

    <table class="table table-bordered">
    <tr><th>Name</th><th>Date</th><th>In</th><th>Out</th></tr>
    """

    for d in data:
        html+=f"<tr><td>{d['name']}</td><td>{d['date']}</td><td>{d['checkin']}</td><td>{d['checkout']}</td></tr>"

    html+="</table>"
    return layout("Attendance",html)

# ================= LEAVE (FIXED WORKING) =================
@app.route("/leave", methods=["GET","POST"])
@login_required
def leave():
    conn=db()

    if request.method=="POST":
        conn.execute("""INSERT INTO leaves(name,from_date,to_date,return_date,days,reason,status)
        VALUES (?,?,?,?,?,?,?)""",
        (current_user.name,
         request.form["from_date"],
         request.form["to_date"],
         request.form["return_date"],
         request.form["days"],
         request.form["reason"],
         "Pending"))
        conn.commit()

    if current_user.role=="Admin":
        data=conn.execute("SELECT * FROM leaves").fetchall()
    else:
        data=conn.execute("SELECT * FROM leaves WHERE name=?", (current_user.name,)).fetchall()

    html="""
    <div class="card p-3 mb-3">
    <h5>Apply Leave</h5>

    <form method="POST">
    From Date:<input type="date" name="from_date" class="form-control"><br>
    To Date:<input type="date" name="to_date" class="form-control"><br>
    Return Date:<input type="date" name="return_date" class="form-control"><br>
    Days:<input type="number" name="days" class="form-control"><br>
    Reason:<textarea name="reason" class="form-control"></textarea><br>
    <button class="btn btn-primary">Apply</button>
    </form>
    </div>

    <table class="table table-bordered">
    <tr><th>Name</th><th>From</th><th>To</th><th>Return</th><th>Days</th><th>Reason</th><th>Status</th></tr>
    """

    for d in data:
        html+=f"<tr><td>{d['name']}</td><td>{d['from_date']}</td><td>{d['to_date']}</td><td>{d['return_date']}</td><td>{d['days']}</td><td>{d['reason']}</td><td>{d['status']}</td></tr>"

    html+="</table>"
    return layout("Leave",html)

# ================= SALARY =================
@app.route("/salary")
@login_required
def salary():
    conn=db()

    if current_user.role=="Admin":
        data=conn.execute("SELECT * FROM salary").fetchall()
    else:
        data=conn.execute("SELECT * FROM salary WHERE name=?", (current_user.name,)).fetchall()

    html="<table class='table'><tr><th>Name</th><th>Amount</th><th>Status</th><th>Action</th></tr>"

    for d in data:
        action=""
        if current_user.role=="Admin":
            action=f"<a class='btn btn-success btn-sm' href='/pay/{d['id']}'>Mark Paid</a>"

        html+=f"<tr><td>{d['name']}</td><td>{d['amount']}</td><td>{d['status']}</td><td>{action}</td></tr>"

    html+="</table>"
    return layout("Salary",html)

@app.route("/pay/<int:id>")
@login_required
def pay(id):
    conn=db()
    conn.execute("UPDATE salary SET status='Paid' WHERE id=?", (id,))
    conn.commit()
    return redirect("/salary")

# ================= CHAT =================
@app.route("/chat", methods=["GET","POST"])
@login_required
def chat():
    conn=db()

    if request.method=="POST":
        conn.execute("INSERT INTO messages(sender,receiver,message) VALUES (?,?,?)",
        (current_user.name,request.form["to"],request.form["msg"]))
        conn.commit()

    users=conn.execute("SELECT name FROM users").fetchall()
    msgs=conn.execute("SELECT * FROM messages").fetchall()

    html="""
    <form method="POST" class="card p-3">
    To:
    <select name="to" class="form-select">
    """

    for u in users:
        html+=f"<option>{u['name']}</option>"

    html+="</select><br><input name='msg' class='form-control'><br><button class='btn btn-primary'>Send</button></form><br>"

    for m in msgs:
        if current_user.role=="Admin" or m["sender"]==current_user.name or m["receiver"]==current_user.name:
            html+=f"<div class='card p-2 mb-2'><b>To:</b>{m['receiver']} | <b>From:</b>{m['sender']}<br>{m['message']}</div>"

    return layout("Chat",html)

# ================= REPORT =================
@app.route("/report", methods=["GET","POST"])
@login_required
def report():
    conn=db()

    if request.method=="POST":
        conn.execute("UPDATE reports SET admin_comment=? WHERE id=?",
        (request.form["comment"],request.form["id"]))
        conn.commit()

    if current_user.role=="Admin":
        data=conn.execute("SELECT * FROM reports").fetchall()
    else:
        data=conn.execute("SELECT * FROM reports WHERE name=?", (current_user.name,)).fetchall()

    html=""
    for d in data:
        html+=f"<div class='card p-3 mb-2'><b>{d['name']}</b><br>{d['report']}<br>Comment: {d['admin_comment']}"

        if current_user.role=="Admin":
            html+=f"""
            <form method='POST'>
            <input type='hidden' name='id' value='{d['id']}'>
            <input name='comment' class='form-control mt-2'>
            <button class='btn btn-primary mt-2'>Comment</button>
            </form>
            """

        html+="</div>"

    return layout("Reports",html)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

# ================= RUN =================
if __name__=="__main__":
    app.run(debug=True, use_reloader=False)
