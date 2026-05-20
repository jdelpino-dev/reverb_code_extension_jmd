from flask import Flask, request, render_template, flash

app = Flask(__name__)

@app.route('/')
@app.route('/categories')
def categories():
    query = request.args.get('query')
    if not query:
        flash("Search using a query string. While the query string "
              "is empty, there will be no search results")


