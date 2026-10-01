from flask import Flask, jsonify, send_from_directory, abort, render_template_string
import sqlite3
import os

app = Flask(__name__, static_folder='.')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'Database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def find_image_file(block_id, theme_id, image_type, image_id):
    prefix = f"{block_id}-{theme_id}-{image_type}-{image_id}."
    images_dir = os.path.join(BASE_DIR, 'Images')
    if os.path.exists(images_dir):
        for fname in os.listdir(images_dir):
            if fname.lower().startswith(prefix.lower()):
                return f"/Images/{fname}"
    return None

def find_person_image_file(block_id, person_id):
    prefix = f"{block_id}-{person_id}."
    pimages_dir = os.path.join(BASE_DIR, 'PersonImages')
    if os.path.exists(pimages_dir):
        for fname in os.listdir(pimages_dir):
            if fname.lower().startswith(prefix.lower()):
                return f"/PersonImages/{fname}"
    return None

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_root_files(filename):
    if os.path.isfile(os.path.join(BASE_DIR, filename)):
        return send_from_directory(BASE_DIR, filename)
    abort(404)

@app.route('/api/blocks')
def get_blocks():
    conn = get_db_connection()
    blocks_rows = conn.execute('SELECT Block_Id, Block_Name FROM Blocks ORDER BY Block_Id').fetchall()
    themes_rows = conn.execute('SELECT Theme_Id, theme_name, block_id FROM Themes ORDER BY Theme_Id').fetchall()
    conn.close()

    themes_by_block = {}
    for t in themes_rows:
        themes_by_block.setdefault(t['block_id'], []).append({
            'id': t['Theme_Id'],
            'name': t['theme_name']
        })

    result = []
    for b in blocks_rows:
        result.append({
            'id': b['Block_Id'],
            'name': b['Block_Name'],
            'themes': themes_by_block.get(b['Block_Id'], [])
        })

    return jsonify(result)

@app.route('/api/theme/<int:theme_id>')
def get_theme(theme_id):
    conn = get_db_connection()
    theme = conn.execute(
        'SELECT t.Theme_Id, t.theme_name, t.block_id, b.Block_Name '
        'FROM Themes t '
        'JOIN Blocks b ON t.block_id = b.Block_Id '
        'WHERE t.Theme_Id = ?',
        (theme_id,)
    ).fetchone()

    if not theme:
        conn.close()
        abort(404, description='Theme not found')

    dates_rows = conn.execute(
        'SELECT Date_Id, Date_name, Date_description, Is_Mandority '
        'FROM Dates WHERE theme_id = ? ORDER BY Date_Id',
        (theme_id,)
    ).fetchall()

    terms_rows = conn.execute(
        'SELECT Term_Id, Term_name, Term_description '
        'FROM Terms WHERE theme_id = ? ORDER BY Term_Id',
        (theme_id,)
    ).fetchall()

    images_rows = conn.execute(
        'SELECT Image_Id, image_doc_name, image_name, image_type '
        'FROM Images WHERE theme_id = ? ORDER BY Image_Id',
        (theme_id,)
    ).fetchall()

    conn.close()

    block_id = theme['block_id']
    markdown_path = os.path.join(BASE_DIR, 'Notes', f'{block_id}-{theme_id}.md')
    markdown_content = ''
    if os.path.exists(markdown_path):
        with open(markdown_path, 'r', encoding='utf-8', errors='replace') as f:
            markdown_content = f.read()

    images_list = []
    for img in images_rows:
        img_url = find_image_file(block_id, theme_id, img['image_type'], img['Image_Id'])
        images_list.append({
            'id': img['Image_Id'],
            'doc_name': img['image_doc_name'],
            'name': img['image_name'],
            'type': img['image_type'],
            'url': img_url or ''
        })

    return jsonify({
        'theme_id': theme['Theme_Id'],
        'theme_name': theme['theme_name'],
        'block_id': block_id,
        'block_name': theme['Block_Name'],
        'markdown': markdown_content,
        'dates': [
            {
                'id': d['Date_Id'],
                'key': d['Date_name'],
                'value': d['Date_description'],
                'is_mandority': d['Is_Mandority']
            }
            for d in dates_rows
        ],
        'terms': [
            {
                'id': t['Term_Id'],
                'key': t['Term_name'],
                'value': t['Term_description']
            }
            for t in terms_rows
        ],
        'images': images_list
    })

@app.route('/api/persons/<int:block_id>')
def get_persons(block_id):
    conn = get_db_connection()
    persons_rows = conn.execute(
        'SELECT p.Person_Id, p.Person_name, p.Person_description, b.Block_Name '
        'FROM Person p '
        'JOIN Blocks b ON p.block_id = b.Block_Id '
        'WHERE p.block_id = ? ORDER BY p.Person_Id',
        (block_id,)
    ).fetchall()
    conn.close()

    result = []
    for p in persons_rows:
        img_url = find_person_image_file(block_id, p['Person_Id'])
        result.append({
            'id': p['Person_Id'],
            'name': p['Person_name'],
            'bio': p['Person_description'],
            'imageUrl': img_url,
            'block': p['Block_Name']
        })

    return jsonify(result)

@app.route('/api/all-persons')
def get_all_persons():
    conn = get_db_connection()
    blocks_rows = conn.execute('SELECT Block_Id, Block_Name FROM Blocks ORDER BY Block_Id').fetchall()
    persons_rows = conn.execute(
        'SELECT p.Person_Id, p.Person_name, p.Person_description, p.block_id, b.Block_Name '
        'FROM Person p '
        'JOIN Blocks b ON p.block_id = b.Block_Id '
        'ORDER BY p.Person_Id'
    ).fetchall()
    conn.close()

    result = {b['Block_Name']: [] for b in blocks_rows}
    for p in persons_rows:
        img_url = find_person_image_file(p['block_id'], p['Person_Id'])
        item = {
            'id': p['Person_Id'],
            'name': p['Person_name'],
            'bio': p['Person_description'],
            'imageUrl': img_url,
            'block': p['Block_Name']
        }
        result.setdefault(p['Block_Name'], []).append(item)

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
