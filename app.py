import os
import re
import json
import shutil
import sqlite3
from functools import wraps
from flask import Flask, jsonify, request, session, redirect, send_from_directory, abort, render_template_string

app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'nmtesher-secret-key-12345')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'Database.db')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

ADMIN_LOGIN_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Вхід до адмін-панелі - NMTesher</title>
  <style>
    :root {
      --c-primary-dark: #624621;
      --c-primary: #9F6D2D;
      --c-accent-peach: #F8DAB2;
      --c-bg-paper: #EEEBE4;
      --c-border: #D2D2D2;
      --c-accent-red: #E93C35;
      --c-text-dark: #2B3034;
      --c-surface: #FDFCFA;
      --c-surface-card: #FFFFFF;
      --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-main);
      background-color: var(--c-bg-paper);
      color: var(--c-text-dark);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .login-card {
      background: var(--c-surface-card);
      border: 1px solid var(--c-border);
      border-radius: 12px;
      padding: 32px 28px;
      width: 100%;
      max-width: 400px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }
    .brand-title {
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--c-primary-dark);
      margin-bottom: 6px;
      text-align: center;
    }
    .brand-subtitle {
      font-size: 0.9rem;
      color: var(--c-primary);
      margin-bottom: 24px;
      text-align: center;
    }
    .alert-error {
      background: #ffebee;
      color: #c62828;
      border: 1px solid #ffcdd2;
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      margin-bottom: 18px;
    }
    .form-group {
      margin-bottom: 18px;
    }
    .form-label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--c-primary-dark);
      margin-bottom: 6px;
    }
    .form-input {
      width: 100%;
      padding: 10px 12px;
      font-size: 0.95rem;
      border-radius: 6px;
      border: 1px solid var(--c-border);
      background: var(--c-surface);
      color: var(--c-text-dark);
      font-family: inherit;
    }
    .form-input:focus {
      outline: none;
      border-color: var(--c-primary);
      box-shadow: 0 0 0 2px rgba(159, 109, 45, 0.15);
    }
    .submit-btn {
      width: 100%;
      background: var(--c-primary);
      color: #FFFFFF;
      border: 1px solid var(--c-primary-dark);
      padding: 10px 14px;
      font-size: 0.95rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .submit-btn:hover {
      background: var(--c-primary-dark);
    }
    .back-link {
      display: block;
      text-align: center;
      margin-top: 18px;
      font-size: 0.85rem;
      color: var(--c-primary);
      text-decoration: none;
    }
    .back-link:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="login-card">
    <h1 class="brand-title">NMTesher</h1>
    <p class="brand-subtitle">Вхід до адмін-панелі</p>
    {% if error %}
      <div class="alert-error">{{ error }}</div>
    {% endif %}
    <form method="POST" action="/admin/login">
      <div class="form-group">
        <label class="form-label" for="password">Пароль адміністратора:</label>
        <input type="password" id="password" name="password" class="form-input" required autofocus />
      </div>
      <button type="submit" class="submit-btn">Увійти</button>
      <a href="/" class="back-link">← Повернутися на головну</a>
    </form>
  </div>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER,
            block_name TEXT NOT NULL,
            theme_name TEXT NOT NULL,
            raw_markdown TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect('/admin/login')
    return send_from_directory(BASE_DIR, 'admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect('/admin')
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        else:
            error = 'Невірний пароль'
    return render_template_string(ADMIN_LOGIN_HTML, error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin/login')

@app.route('/admin/drafts/<int:draft_id>/file/<path:filename>')
@login_required
def serve_draft_file(draft_id, filename):
    folder = os.path.join(BASE_DIR, 'Drafts', str(draft_id))
    return send_from_directory(folder, filename)

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

@app.route('/api/scan-note', methods=['POST'])
def scan_note():
    data = request.get_json(silent=True) or {}
    markdown = data.get('markdown', '')
    block_name = data.get('block_name', '').strip()
    theme_name = data.get('theme_name', '').strip()

    if not block_name:
        return jsonify({'error': 'Будь ласка, оберіть або введіть назву блоку'}), 400
    if not theme_name:
        return jsonify({'error': 'Будь ласка, введіть назву теми'}), 400
    if not markdown.strip():
        return jsonify({'error': 'Текст конспекту порожній'}), 400

    conn = get_db_connection()
    block = conn.execute('SELECT Block_Id, Block_Name FROM Blocks WHERE LOWER(Block_Name) = LOWER(?)', (block_name,)).fetchone()
    if block:
        existing_theme = conn.execute('SELECT Theme_Id FROM Themes WHERE block_id = ? AND LOWER(theme_name) = LOWER(?)', (block['Block_Id'], theme_name)).fetchone()
        if existing_theme:
            conn.close()
            return jsonify({'error': f'Тема "{theme_name}" вже існує в блоці "{block["Block_Name"]}"'}), 400

    images = {}
    for m in re.finditer(r'!___([^\r\n]+?)___', markdown):
        n = m.group(1).strip()
        if n and n.lower() not in images:
            images[n.lower()] = {'doc_name': n, 'name': n, 'type': 0, 'show_in_note': True}

    c1 = re.sub(r'!___[^\r\n]+?___', ' ', markdown)
    for m in re.finditer(r'___([^\r\n]+?)___', c1):
        n = m.group(1).strip()
        if n and n.lower() not in images:
            images[n.lower()] = {'doc_name': n, 'name': n, 'type': 0, 'show_in_note': False}

    c2 = re.sub(r'!___[^\r\n]+?___', ' ', markdown)
    c2 = re.sub(r'___[^\r\n]+?___', ' ', c2)
    raw_persons = []
    for m in re.finditer(r'`([^`\r\n]+)`', c2):
        p = m.group(1).strip()
        if p and p not in raw_persons:
            raw_persons.append(p)

    c3 = re.sub(r'`[^`\r\n]+`', ' ', c2)
    terms = []
    for m in re.finditer(r'(?<!_)__([^_ \r\n][^_\r\n]*?)__(?!_)', c3):
        t = m.group(1).strip()
        if t and t not in terms:
            terms.append(t)

    c4 = re.sub(r'(?<!_)__[^_\r\n]+?__(?!_)', ' ', c3)
    dates = []
    for m in re.finditer(r'(?<!_)_([^_ \r\n][^_\r\n]*?)_(?!_)', c4):
        d = m.group(1).strip()
        if d and d not in dates:
            dates.append(d)

    existing_persons_in_block = set()
    if block:
        p_rows = conn.execute('SELECT Person_name FROM Person WHERE block_id = ?', (block['Block_Id'],)).fetchall()
        for pr in p_rows:
            existing_persons_in_block.add(pr['Person_name'].strip().lower())
    conn.close()

    persons_list = []
    for p in raw_persons:
        p_exists = p.strip().lower() in existing_persons_in_block
        persons_list.append({
            'name': p,
            'exists': p_exists
        })

    return jsonify({
        'dates': [{'name': d, 'description': '', 'is_mandatory': 0} for d in dates],
        'terms': [{'name': t, 'description': ''} for t in terms],
        'images': list(images.values()),
        'persons': persons_list
    })

@app.route('/api/drafts', methods=['POST'])
def create_draft():
    block_name = request.form.get('block_name', '').strip()
    theme_name = request.form.get('theme_name', '').strip()
    raw_markdown = request.form.get('markdown', '')

    if not block_name:
        return jsonify({'error': 'Будь ласка, вкажіть назву блоку'}), 400
    if not theme_name:
        return jsonify({'error': 'Будь ласка, вкажіть назву теми'}), 400
    if not raw_markdown.strip():
        return jsonify({'error': 'Текст конспекту порожній'}), 400

    conn = get_db_connection()
    block = conn.execute('SELECT Block_Id, Block_Name FROM Blocks WHERE LOWER(Block_Name) = LOWER(?)', (block_name,)).fetchone()
    block_id = block['Block_Id'] if block else None
    if block:
        existing_theme = conn.execute('SELECT Theme_Id FROM Themes WHERE block_id = ? AND LOWER(theme_name) = LOWER(?)', (block['Block_Id'], theme_name)).fetchone()
        if existing_theme:
            conn.close()
            return jsonify({'error': f'Тема "{theme_name}" вже існує в блоці "{block["Block_Name"]}"'}), 400

    dates_raw = request.form.get('dates', '[]')
    terms_raw = request.form.get('terms', '[]')
    images_raw = request.form.get('images', '[]')
    persons_raw = request.form.get('persons', '[]')

    try:
        dates_data = json.loads(dates_raw)
        terms_data = json.loads(terms_raw)
        images_data = json.loads(images_raw)
        persons_data = json.loads(persons_raw)
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Некоректний формат JSON даних: {str(e)}'}), 400

    cur = conn.cursor()
    cur.execute(
        'INSERT INTO Drafts (block_id, block_name, theme_name, raw_markdown, data_json) VALUES (?, ?, ?, ?, ?)',
        (block_id, block_name, theme_name, raw_markdown, '{}')
    )
    draft_id = cur.lastrowid
    conn.commit()

    draft_folder = os.path.join(BASE_DIR, 'Drafts', str(draft_id))
    os.makedirs(draft_folder, exist_ok=True)

    for idx, img in enumerate(images_data):
        doc_key = img.get('doc_name', f'img_{idx}')
        file_obj = request.files.get(f'image_file_{doc_key}') or request.files.get(f'image_file_{idx}')
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1] or '.png'
            safe_name = f"image_{idx}{ext}"
            target_path = os.path.join(draft_folder, safe_name)
            file_obj.save(target_path)
            img['file_path'] = os.path.join('Drafts', str(draft_id), safe_name).replace('\\', '/')

    for idx, per in enumerate(persons_data):
        p_name = per.get('name', f'person_{idx}')
        file_obj = request.files.get(f'person_photo_{p_name}') or request.files.get(f'person_photo_{idx}')
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1] or '.jpg'
            safe_name = f"person_{idx}{ext}"
            target_path = os.path.join(draft_folder, safe_name)
            file_obj.save(target_path)
            per['photo_path'] = os.path.join('Drafts', str(draft_id), safe_name).replace('\\', '/')

    final_payload = {
        'dates': dates_data,
        'terms': terms_data,
        'images': images_data,
        'persons': persons_data
    }

    conn.execute('UPDATE Drafts SET data_json = ? WHERE id = ?', (json.dumps(final_payload, ensure_ascii=False), draft_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok', 'draft_id': draft_id, 'message': 'Конспект успішно збережено в чернетки'})

@app.route('/api/admin/drafts')
@login_required
def get_admin_drafts():
    conn = get_db_connection()
    rows = conn.execute('SELECT id, block_id, block_name, theme_name, raw_markdown, created_at, data_json FROM Drafts ORDER BY id DESC').fetchall()
    conn.close()

    result = []
    for r in rows:
        try:
            d = json.loads(r['data_json'])
        except Exception:
            d = {}
        result.append({
            'id': r['id'],
            'block_id': r['block_id'],
            'block_name': r['block_name'],
            'theme_name': r['theme_name'],
            'created_at': r['created_at'],
            'dates_count': len(d.get('dates', [])),
            'terms_count': len(d.get('terms', [])),
            'images_count': len(d.get('images', [])),
            'persons_count': len(d.get('persons', []))
        })
    return jsonify(result)

@app.route('/api/admin/drafts/<int:draft_id>')
@login_required
def get_admin_draft(draft_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id, block_id, block_name, theme_name, raw_markdown, created_at, data_json FROM Drafts WHERE id = ?', (draft_id,)).fetchone()
    conn.close()

    if not row:
        abort(404, description='Чернетку не знайдено')

    try:
        d = json.loads(row['data_json'])
    except Exception:
        d = {}

    return jsonify({
        'id': row['id'],
        'block_id': row['block_id'],
        'block_name': row['block_name'],
        'theme_name': row['theme_name'],
        'raw_markdown': row['raw_markdown'],
        'created_at': row['created_at'],
        'dates': d.get('dates', []),
        'terms': d.get('terms', []),
        'images': d.get('images', []),
        'persons': d.get('persons', [])
    })

@app.route('/api/admin/drafts/<int:draft_id>/update', methods=['POST'])
@login_required
def update_admin_draft(draft_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id, data_json FROM Drafts WHERE id = ?', (draft_id,)).fetchone()
    if not row:
        conn.close()
        abort(404, description='Чернетку не знайдено')

    block_name = request.form.get('block_name', '').strip()
    theme_name = request.form.get('theme_name', '').strip()
    raw_markdown = request.form.get('markdown', '')

    if not block_name or not theme_name:
        conn.close()
        return jsonify({'error': 'Назва блоку та теми обов’язкові'}), 400

    try:
        dates_data = json.loads(request.form.get('dates', '[]'))
        terms_data = json.loads(request.form.get('terms', '[]'))
        images_data = json.loads(request.form.get('images', '[]'))
        persons_data = json.loads(request.form.get('persons', '[]'))
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Некоректний формат JSON: {str(e)}'}), 400

    draft_folder = os.path.join(BASE_DIR, 'Drafts', str(draft_id))
    os.makedirs(draft_folder, exist_ok=True)

    for idx, img in enumerate(images_data):
        doc_key = img.get('doc_name', f'img_{idx}')
        file_obj = request.files.get(f'image_file_{doc_key}') or request.files.get(f'image_file_{idx}')
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1] or '.png'
            safe_name = f"image_{idx}_{int(os.path.getmtime(draft_folder) if os.path.exists(draft_folder) else 0)}{ext}"
            target_path = os.path.join(draft_folder, safe_name)
            file_obj.save(target_path)
            img['file_path'] = os.path.join('Drafts', str(draft_id), safe_name).replace('\\', '/')

    for idx, per in enumerate(persons_data):
        p_name = per.get('name', f'person_{idx}')
        file_obj = request.files.get(f'person_photo_{p_name}') or request.files.get(f'person_photo_{idx}')
        if file_obj and file_obj.filename:
            ext = os.path.splitext(file_obj.filename)[1] or '.jpg'
            safe_name = f"person_{idx}_{int(os.path.getmtime(draft_folder) if os.path.exists(draft_folder) else 0)}{ext}"
            target_path = os.path.join(draft_folder, safe_name)
            file_obj.save(target_path)
            per['photo_path'] = os.path.join('Drafts', str(draft_id), safe_name).replace('\\', '/')

    block = conn.execute('SELECT Block_Id FROM Blocks WHERE LOWER(Block_Name) = LOWER(?)', (block_name,)).fetchone()
    block_id = block['Block_Id'] if block else None

    final_payload = {
        'dates': dates_data,
        'terms': terms_data,
        'images': images_data,
        'persons': persons_data
    }

    conn.execute(
        'UPDATE Drafts SET block_id = ?, block_name = ?, theme_name = ?, raw_markdown = ?, data_json = ? WHERE id = ?',
        (block_id, block_name, theme_name, raw_markdown, json.dumps(final_payload, ensure_ascii=False), draft_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok', 'message': 'Чернетку оновлено'})

@app.route('/api/admin/drafts/<int:draft_id>', methods=['DELETE'])
@login_required
def delete_admin_draft(draft_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Drafts WHERE id = ?', (draft_id,))
    conn.commit()
    conn.close()

    draft_folder = os.path.join(BASE_DIR, 'Drafts', str(draft_id))
    if os.path.exists(draft_folder):
        shutil.rmtree(draft_folder, ignore_errors=True)

    return jsonify({'status': 'ok', 'message': 'Чернетку видалено'})

@app.route('/api/admin/drafts/<int:draft_id>/publish', methods=['POST'])
@login_required
def publish_admin_draft(draft_id):
    conn = get_db_connection()
    row = conn.execute('SELECT id, block_name, theme_name, raw_markdown, data_json FROM Drafts WHERE id = ?', (draft_id,)).fetchone()
    if not row:
        conn.close()
        abort(404, description='Чернетку не знайдено')

    block_name = row['block_name'].strip()
    theme_name = row['theme_name'].strip()
    raw_markdown = row['raw_markdown']

    try:
        data = json.loads(row['data_json'])
    except Exception:
        data = {}

    dates = data.get('dates', [])
    terms = data.get('terms', [])
    images = data.get('images', [])
    persons = data.get('persons', [])

    cur = conn.cursor()
    block = cur.execute('SELECT Block_Id, Block_Name FROM Blocks WHERE LOWER(Block_Name) = LOWER(?)', (block_name,)).fetchone()
    if block:
        block_id = block['Block_Id']
    else:
        cur.execute('INSERT INTO Blocks (Block_Name) VALUES (?)', (block_name,))
        block_id = cur.lastrowid

    existing_theme = cur.execute('SELECT Theme_Id FROM Themes WHERE block_id = ? AND LOWER(theme_name) = LOWER(?)', (block_id, theme_name)).fetchone()
    if existing_theme:
        conn.close()
        return jsonify({'error': f'Тема "{theme_name}" вже існує в цьому блоці'}), 400

    cur.execute('INSERT INTO Themes (theme_name, block_id) VALUES (?, ?)', (theme_name, block_id))
    theme_id = cur.lastrowid

    for d in dates:
        d_name = d.get('name', '').strip()
        d_desc = d.get('description', '').strip()
        d_mand = 1 if str(d.get('is_mandatory')) in ('1', 'true', 'True') else 0
        if d_name:
            cur.execute('INSERT INTO Dates (Date_name, Date_description, Is_Mandority, theme_id) VALUES (?, ?, ?, ?)', (d_name, d_desc, d_mand, theme_id))

    for t in terms:
        t_name = t.get('name', '').strip()
        t_desc = t.get('description', '').strip()
        if t_name:
            cur.execute('INSERT INTO Terms (Term_name, Term_description, theme_id) VALUES (?, ?, ?)', (t_name, t_desc, theme_id))

    os.makedirs(os.path.join(BASE_DIR, 'PersonImages'), exist_ok=True)
    for p in persons:
        p_name = p.get('name', '').strip()
        p_bio = p.get('bio', '').strip()
        if not p_name:
            continue
        p_row = cur.execute('SELECT Person_Id FROM Person WHERE block_id = ? AND LOWER(Person_name) = LOWER(?)', (block_id, p_name)).fetchone()
        if p_row:
            person_id = p_row['Person_Id']
            if p_bio:
                cur.execute('UPDATE Person SET Person_description = ? WHERE Person_Id = ?', (p_bio, person_id))
        else:
            cur.execute('INSERT INTO Person (Person_name, Person_description, block_id) VALUES (?, ?, ?)', (p_name, p_bio, block_id))
            person_id = cur.lastrowid

        p_photo_path = p.get('photo_path')
        if p_photo_path:
            full_src = os.path.join(BASE_DIR, p_photo_path)
            if os.path.exists(full_src):
                ext = os.path.splitext(full_src)[1] or '.jpg'
                dst_name = f"{block_id}-{person_id}{ext}"
                dst_path = os.path.join(BASE_DIR, 'PersonImages', dst_name)
                shutil.copyfile(full_src, dst_path)

    os.makedirs(os.path.join(BASE_DIR, 'Images'), exist_ok=True)
    final_markdown = raw_markdown
    for img in images:
        doc_name = img.get('doc_name', '').strip()
        display_name = img.get('name', doc_name).strip() or doc_name
        img_type = 1 if str(img.get('type')) in ('1', 'monuments') else 0
        show_in_note = bool(img.get('show_in_note'))

        cur.execute('INSERT INTO Images (image_doc_name, image_name, theme_id, image_type) VALUES (?, ?, ?, ?)', (doc_name, display_name, theme_id, img_type))
        image_id = cur.lastrowid

        img_file_path = img.get('file_path')
        ext = '.png'
        if img_file_path:
            full_src = os.path.join(BASE_DIR, img_file_path)
            if os.path.exists(full_src):
                ext = os.path.splitext(full_src)[1] or '.png'
                dst_name = f"{block_id}-{theme_id}-{img_type}-{image_id}{ext}"
                dst_path = os.path.join(BASE_DIR, 'Images', dst_name)
                shutil.copyfile(full_src, dst_path)

        new_image_rel_path = f"/Images/{block_id}-{theme_id}-{img_type}-{image_id}{ext}"
        if show_in_note and doc_name:
            pattern = re.compile(r'!___' + re.escape(doc_name) + r'___')
            final_markdown = pattern.sub(f'![Картинка]({new_image_rel_path})', final_markdown)

    os.makedirs(os.path.join(BASE_DIR, 'Notes'), exist_ok=True)
    note_file_path = os.path.join(BASE_DIR, 'Notes', f"{block_id}-{theme_id}.md")
    with open(note_file_path, 'w', encoding='utf-8') as f:
        f.write(final_markdown)

    cur.execute('DELETE FROM Drafts WHERE id = ?', (draft_id,))
    conn.commit()
    conn.close()

    draft_folder = os.path.join(BASE_DIR, 'Drafts', str(draft_id))
    if os.path.exists(draft_folder):
        shutil.rmtree(draft_folder, ignore_errors=True)

    return jsonify({'status': 'ok', 'block_id': block_id, 'theme_id': theme_id})

@app.route('/<path:filename>')
def serve_root_files(filename):
    if filename.startswith(('api/', 'admin')):
        abort(404)
    target = os.path.join(BASE_DIR, filename)
    if os.path.isfile(target):
        return send_from_directory(BASE_DIR, filename)
    abort(404)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
