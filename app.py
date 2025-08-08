from flask import Flask, render_template, request
from search_engine import TfidfSearchEngine

app = Flask(__name__)
search_engine = TfidfSearchEngine(folder_path='data')

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form['query']
        results = search_engine.search(query)

    return render_template('index.html', query=query, results=results)

if __name__ == '__main__':
    app.run(debug=True)
