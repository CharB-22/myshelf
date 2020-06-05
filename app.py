import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required

app = Flask(__name__)
app.secret_key = "stepwpkhpo"


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


'''Connect to the database'''
con = sqlite3.connect('myshelf.db')

@app.route("/", methods=["POST", "GET"])
@login_required
def index():
    user = session["user_id"]
    current_owner = "Me"
    bookshelves = []
    '''Connect to the database'''
    with sqlite3.connect("myshelf.db") as con:
        db = con.cursor()
        sql_request = ("SELECT * from books WHERE user_id = ? AND with = ?")
        db.execute(sql_request, (user, current_owner))
        rows = db.fetchall()
        for index in rows:
            if index[4] == "bought" or index[4] == "borrowed":
                    bookshelves.append(index[1])
    return render_template("index.html", bookshelves=bookshelves)

@app.route("/login", methods=["POST", "GET"])
def login():
    '''Forget any user_id'''
    session.clear()

    if request.method == "POST":
        '''Store the information from the form'''
        name = request.form["username"]
        password = request.form["password"]
        '''Check if user exist'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            sql_request = ("SELECT * from users WHERE username = ?")
            db.execute(sql_request,[name])
            rows = db.fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0][2], password):
            message = "Invalid username/password"
            return render_template("error.html", message=message)
        '''Remember which user has logged in'''
        session["user_id"] = rows[0][0]
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        '''Store form information in variables'''
        name = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        '''Check that confirmation is matching password'''
        if password != confirmation:
            message = "The confirmation is different from the password"
            return render_template("error.html", message=message)
        '''Connection with the database'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            sql_request = ("SELECT * from users WHERE username = ?")
            db.execute(sql_request,[name])
            rows = db.fetchall()
        '''Check if this user exists'''
        if len(rows) == 1:
            message = "This username already exists"
            return render_template("error.html", message=message)
        '''Save those data in the database'''
        sql_request = ("INSERT INTO users (username, hash) VALUES (?,?)")
        db.execute(sql_request, (name, hash))
        con.commit()
        '''Now that user created - check if in database to login successfully'''
        sql_request = ("SELECT * from users WHERE username = ?")
        db.execute(sql_request,[name])
        rows = db.fetchall()
        session["user_id"] = rows[0][0]
        return redirect("/")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == 'GET':
        return render_template("search.html")
    else:
        '''Search a book in your bookshelves'''
        search = request.form.get("search")
        results = []

        '''Connect to the database'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            db.execute("SELECT * from books WHERE title LIKE '%'||?||'%' OR author LIKE '%'||?||'%'", (search, search))
            rows = db.fetchall()
            print(rows)
            for index in rows:
                if index[5] == session["user_id"]:
                    results.append(index)
        return render_template("results.html", results=results)


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/login")


@app.route("/newbook", methods=["POST", "GET"])
@login_required
def newbook():
    if request.method == "GET":
        return render_template("newbook.html")
    else:
        '''Make sure all the fields are submitted with JS'''
        '''Store values from the form in variables'''
        title = request.form.get("title")
        author = request.form.get("author")
        status = request.form.get("status")
        description = request.form.get("description")
        current_owner = "Me"
        '''Connect to the database'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            '''Insert this new book in database'''
            sql_request = ("INSERT INTO books (title, author, description, status, user_id, with, owner) VALUES (?,?,?,?,?,?,?)")
            db.execute(sql_request, (title, author, description, status,  session["user_id"], current_owner, session["user_id"]))
            con.commit()
        return render_template("newbook.html")


@app.route("/friend", methods=["POST","GET"])
@login_required
def friend():
    if request.method == "GET":
        return render_template("friend.html")
    else:
        search_friend = request.form.get("search_friend")
        '''Query the database for this friend'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            sql_query = ("SELECT * FROM users WHERE username = ?")
            db.execute(sql_query, [search_friend])
            rows = db.fetchall()
        '''The name can't be find in the database'''
        if len(rows) != 1:
            message = "This friend is not using Myshelf"
            return render_template("error.html", message=message)
        ''' The current user cannot add himself '''
        if rows[0][0] == session["user_id"]:
            message = "Please you must have other friends than yourself!"
            return render_template("error.html", message=message)
        ''' there should not be more than 1 result for the username (see register session)'''
        if len(rows) > 1:
            message = "Make sure this is the correct and complete username"
            return render_template("error.html", message=message)
        '''Check if we are already friend'''
        id = session["user_id"]
        sql_query = ("SELECT * FROM friends WHERE user_id = ? AND name = ?")
        db.execute(sql_query, (id, search_friend))
        friends_rows = db.fetchall()
        if len(friends_rows) == 1:
            message = "You are already friends"
            return render_template("error.html", message=message)
        '''If everything is ok - add as a friend'''
        friend_id = rows[0][0]
        friend_name = rows[0][1]
        sql_request = ("INSERT INTO friends (name, friend_id, user_id) VALUES (?,?,?)")
        parameters = (friend_name, friend_id, id)
        db.execute(sql_request, parameters)
        con.commit()
        '''Make sure the current user is added to the friend's friends'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            rows = db.execute("SELECT username FROM users WHERE id = ?",[id])
            for row in rows:
                user_name = row[0]
        sql_request = ("INSERT INTO friends (name, friend_id, user_id) VALUES (?,?,?)")
        parameters = (user_name, id, friend_id)
        db.execute(sql_request, parameters)
        con.commit()
        return render_template("success.html", friend = friend_name)


@app.route("/give", methods=["GET", "POST"])
@login_required
def give():
    user_id = session["user_id"]
    if request.method == "GET":
        friends = []
        books = []
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            db.execute("SELECT name FROM friends WHERE user_id = ?", [user_id])
            rows = db.fetchall()
        for row in rows:
            friends.append(row[0])

        db.execute("SELECT title FROM books WHERE user_id = ? AND with ='Me' AND status = 'bought'", [user_id])
        bookrows = db.fetchall()
        for book in bookrows:
            books.append(book[0])
        return render_template("give.html", friends=friends, books=books)
    else:
        friend = request.form.get("friend")
        book = request.form.get("book")
        '''Update the current user bookshelf 'with' '''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            db.execute(("UPDATE books SET with = ? WHERE user_id = ? AND title = ?"),(friend, user_id, book))
            ''' Insert the book in the friend's bookshelf'''
            ''' Get the book information from the books table '''
            db.execute(("SELECT title, author, description, owner from books WHERE user_id = ? AND title = ?"), (user_id, book))
            book_info = db.fetchall()
            print(book_info)
            title = book_info[0][0]
            author = book_info[0][1]
            description = book_info[0][2]
            owner = book_info[0][3]
            '''Query database for friend id'''
            db.execute("SELECT id FROM users WHERE username = ?", [friend])
            friend_rows = db.fetchall()
            print(friend_rows)
            friend_id = friend_rows[0][0]
            status = "borrowed"
            current_owner = "Me"
            '''Insert the book in the friend bookshelf'''
            sql_request = ("INSERT INTO books (title, author, status, description, user_id, with, owner) VALUES (?,?,?,?,?,?,?)")
            bookshelf_parameter = (title, author, status, description, friend_id, current_owner,owner)
            db.execute(sql_request, bookshelf_parameter)
            con.commit()
            '''Update the exchange table'''
            sql_request = ("INSERT INTO exchange (title, user_id, owner) VALUES (?,?,?)")
            exchange_parameter = (title, friend_id, owner)
            db.execute(sql_request, exchange_parameter)
            con.commit()
            db.close()
        return redirect("/")


@app.route("/giveback", methods=["GET", "POST"])
@login_required
def giveback():
    user_id = session["user_id"]
    if request.method == "GET":
        books = []
        '''Select the book to give back'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            db.execute("SELECT title FROM books WHERE user_id = ? AND status='borrowed'", [user_id])
            bookrows = db.fetchall()
            for book in bookrows:
                books.append(book[0])
            db.close()
        return render_template("giveback.html", books=books)
    else:
        book = request.form.get("book")
        '''Find the owner of the book'''
        with sqlite3.connect("myshelf.db") as con:
            db = con.cursor()
            db.execute("SELECT owner FROM exchange WHERE title = ?", [book])
            rows = db.fetchall()
            owner = rows[0][0]
            with_name = "Me"
            status = "borrowed"
            '''Update bookshelves of the owner "with"'''
            db.execute("UPDATE books SET with = ? WHERE owner = ?", (with_name, owner))
            '''Delete book from current owner's bookshelve'''
            db.execute("DELETE FROM books WHERE title = ? AND status = ? AND user_id = ?", (book, status, user_id))
        return redirect("/")


if __name__ == "__main__":
    app.run()