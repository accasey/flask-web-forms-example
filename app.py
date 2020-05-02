from flask import Flask, render_template, request, redirect, url_for, g, flash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, DecimalField
from wtforms.validators import DataRequired, InputRequired, Length
import sqlite3
import pdb

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"


class ItemForm(FlaskForm):
    # The InputRequired will add the required attribute to the element
    # But if you remove that through the DEV tools, then this message will come in
    # to play. Use DataRequired to protect against whitespace blank values
    title = StringField("Title", validators=[
        InputRequired("The title is required"),
        DataRequired("The title cannot be blank"),
        Length(min=5, max=20, message="The title must be between 5 and 20 characters")
    ])
    price = DecimalField("Price")
    description = TextAreaField("Description", validators=[
        InputRequired("The description is required"),
        DataRequired("The description cannot be blank"),
        Length(min=5, max=40, message="The description must be between 5 and 40 characters")
    ])


class NewItemForm(ItemForm):
    """The first argument of StringField defines the label of the field."""

    # Use coerce to cast to str to int
    category = SelectField(""
                           "Category", coerce=int)
    subcategory = SelectField("Subcategory", coerce=int)
    submit = SubmitField("Submit")


class EditItemForm(ItemForm):
    submit = SubmitField("Update item")


class DeleteItemForm(FlaskForm):
    submit = SubmitField("Delete item")


class FilterForm(FlaskForm):
    title = StringField("Title", validators=[Length(max=20)])
    price = SelectField("Price", coerce=int, choices=[(0, "---"), (1, "High to low"), (2, "Low to high")])
    category = SelectField("Category", coerce=int)
    subcategory = SelectField("Subcategory", coerce=int)
    submit = SubmitField("Filter")


@app.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
def edit_item(item_id):
    conn = get_db()
    c = conn.cursor()

    item_from_db = c.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = c.fetchone()
    try:
        item = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4]
        }
    except:
        item = dict()

    if item:
        form = EditItemForm()
        print('before validate_on_submit')
        if form.validate_on_submit():
            print('inside validate_on_submit')
            c.execute("""
                      UPDATE items
                      SET title = ?, description = ?, price = ?
                      WHERE id = ?""",
                      (
                          form.title.data,
                          form.description.data,
                          float(form.price.data),
                          item_id
                      ))
            conn.commit()
            flash(f"Item {form.title.data} has been successfully updated.", "success")
            return redirect(url_for('item', item_id=item_id))

        print('after validate_on_submit')
        form.title.data = item['title']
        form.description.data = item['description']
        form.price.data = item['price']

        if form.errors:
            flash(f"{form.errors}", "danger")

        return render_template("edit_item.html", item=item, form=form)

    return redirect(url_for('home'))


@app.route("/item/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id):
    conn = get_db()
    c = conn.cursor()

    item_from_db = c.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = c.fetchone()
    try:
        item = {
            "id": row[0],
            "title": row[1]
        }
    except:
        item = dict()

    if item:
        c.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()

        flash(f"Item {item['title']} has been successfully deleted.", "success")
    else:
        flash("This item does not exist", "danger")

    return redirect(url_for('home'))


@app.route("/item/<int:item_id>")
def item(item_id):
    c = get_db().cursor()
    item_from_db = c.execute("""SELECT
                        i.id, i.title, i.description, i.price, i.image, c.name, s.name
                        FROM 
                        items as i
                        INNER JOIN categories AS c ON i.category_id = c.id
                        INNER JOIN subcategories AS s on i.subcategory_id = s.id
                        WHERE i.id = ?""",
                             (item_id,)
                             )
    row = c.fetchone()
    try:
        item = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "category": row[5],
            "subcategory": row[6]
        }
    except:
        item = dict()

    if item:
        deleteItemForm = DeleteItemForm()

        return render_template("item.html", item=item, deleteItemForm=deleteItemForm)
    return redirect(url_for('home'))


@app.route("/")
def home():
    conn = get_db()
    c = conn.cursor()

    form = FilterForm(request.args, meta={"csrf": False})

    c.execute("SELECT id, name FROM categories")
    categories = c.fetchall()
    categories.insert(0, (0, "---"))
    form.category.choices = categories

    c.execute("SELECT id, name FROM subcategories WHERE category_id = ?", (1,))
    subcategories = c.fetchall()
    subcategories.insert(0, (0, "---"))
    form.subcategory.choices = subcategories

    query = """SELECT
               i.id,i.title,i.description,i.price,i.image,c.name,s.name
               FROM items as i
               INNER JOIN categories AS c ON i.category_id = c.id
               INNER JOIN subcategories AS s ON i.subcategory_id = s.id
               """

    if form.validate():
        filter_queries = []
        parameters = []

        if form.title.data.strip():
            filter_queries.append("i.title LIKE ?")
            parameters.append("%" + form.title.data + "%")

        if form.category.data:
            filter_queries.append("i.category_id = ?")
            parameters.append(form.category.data)

        if form.subcategory.data:
            filter_queries.append("i.subcategory_id = ?")
            parameters.append(form.subcategory.data)

        if filter_queries:
            query += " WHERE "
            query += " AND ".join(filter_queries)

        if form.price.data:
            if form.price.data == 1:
                query += " ORDER BY i.price DESC"
            else:
                query += " ORDER BY i.price"
        else:
            query += " ORDER BY i.price DESC"

        items_from_db = c.execute(query, tuple(parameters))
        print(query)
    else:
        # just execute the original query
        items_from_db = c.execute(query + "ORDER BY i.id DESC")

    items = []
    for row in items_from_db:
        item = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "category": row[5],
            "subcategory": row[6]
        }
        items.append(item)

    return render_template("home.html", items=items, form=form)


@app.route("/item/new", methods=["GET", "POST"])
def new_item():
    conn = get_db()
    c = conn.cursor()
    form = NewItemForm()

    c.execute("SELECT id, name FROM categories")
    categories = c.fetchall()
    # [(1, 'Food'), (2, 'Technology'), (3, 'Books')]
    form.category.choices = categories

    c.execute("""SELECT id, name FROM subcategories
                WHERE category_id = ?""",
              (1,)
              )
    subcategories = c.fetchall()
    form.subcategory.choices = subcategories

    # pdb.set_trace()
    if request.method == 'POST':
        # Process the form data
        c.execute("""INSERT INTO items
                    (title, description, price, image, category_id, subcategory_id)
                    VALUES(?,?,?,?,?,?)""",
                  (
                      form.title.data,
                      form.description.data,
                      float(form.price.data),
                      "",
                      form.category.data,
                      form.subcategory.data
                  ))
        conn.commit()
        # Redirect to some page
        flash(f"Item {request.form['title']} has been successfully submitted", "success")
        return redirect(url_for('home'))

    if form.errors:
        flash(f"{form.errors}", "danger")
    return render_template("new_item.html", form=form)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('db/globomantics.db')
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
