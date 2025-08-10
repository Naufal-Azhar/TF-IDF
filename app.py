import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from search_engine import TfidfSearchEngine

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Ganti dengan secret key acak untuk produksi

# Configuration
UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max upload size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Auth/DB config
AUTH_DIR = 'auth'
DB_PATH = os.path.join(AUTH_DIR, 'users.db')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUTH_DIR, exist_ok=True)

# Initialize search engine
search_engine = TfidfSearchEngine(folder_path=UPLOAD_FOLDER)

# -----------------------------
# Helper: Database (SQLite)
# -----------------------------

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_user_db():
    conn = get_db_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

init_user_db()

# -----------------------------
# Helper: Auth
# -----------------------------

def create_user(username: str, password: str):
    username = username.strip()
    if not username or not password:
        raise ValueError('Username dan password wajib diisi')
    if len(username) < 3:
        raise ValueError('Username minimal 3 karakter')
    if len(password) < 6:
        raise ValueError('Password minimal 6 karakter')

    pwd_hash = generate_password_hash(password)
    conn = get_db_conn()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, pwd_hash)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError('Username sudah digunakan')
    finally:
        conn.close()


def get_user_by_username(username: str):
    conn = get_db_conn()
    try:
        cur = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        return row
    finally:
        conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

# -----------------------------
# Utilities
# -----------------------------

def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        print(f"Invalid filename: {filename}")
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    is_allowed = ext in ALLOWED_EXTENSIONS
    
    if not is_allowed:
        print(f"Unsupported file type: {filename} (allowed: {', '.join(ALLOWED_EXTENSIONS)})")
        
    return is_allowed


def get_file_list():
    """Get list of files in the data folder"""
    files = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if allowed_file(filename):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file_size = os.path.getsize(file_path)
                files.append({
                    'name': filename,
                    'size': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2)
                })
    return sorted(files, key=lambda x: x['name'])


def get_unique_filename(original_filename):
    """Generate unique filename by adding timestamp if file exists"""
    from datetime import datetime
    name, ext = os.path.splitext(original_filename)
    filename = secure_filename(original_filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return filename
        
    # Add timestamp to filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{name}_{timestamp}{ext}"
    return secure_filename(new_filename)

# -----------------------------
# Auth Routes
# -----------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_url = request.args.get('next') or url_for('index')

        user = get_user_by_username(username)
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Username atau password salah.', 'error')
            return render_template('auth/login.html', username=username)

        # Set session
        session['user_id'] = user['id']
        session['username'] = user['username']
        flash('Login berhasil!', 'success')
        return redirect(next_url)

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if password != confirm:
            flash('Konfirmasi password tidak cocok.', 'error')
            return render_template('auth/register.html', username=username)

        try:
            create_user(username, password)
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html', username=username)

        flash('Registrasi berhasil. Silakan login.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))

# -----------------------------
# App Routes (Protected)
# -----------------------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    results = []
    query = ""
    files = get_file_list()
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            results = search_engine.search(query)
        else:
            flash('Please enter a search query.', 'warning')

    return render_template('index.html', 
                         query=query, 
                         results=results, 
                         files=files,
                         document_count=search_engine.get_document_count(),
                         current_user=session.get('username'))


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle file uploads with strict validation"""
    if 'files[]' not in request.files:
        flash('No files selected.', 'error')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    
    # Validate number of files
    if len(files) > 5:
        flash('Maksimal 5 file yang bisa diunggah sekaligus.', 'error')
        return redirect(url_for('index'))
    
    if not files or all(f.filename == '' for f in files):
        flash('No files selected.', 'error')
        return redirect(url_for('index'))
    
    # Validate file types first before saving any files
    invalid_files = []
    for file in files:
        if file and file.filename:
            if not file.filename.lower().endswith(('.pdf', '.txt')):
                invalid_files.append(file.filename)
    
    if invalid_files:
        flash(f'Format file tidak valid: {", ".join(invalid_files)}. Hanya format .pdf dan .txt yang diperbolehkan.', 'error')
        return redirect(url_for('index'))
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    success_count = 0
    error_count = 0
    
    for file in files:
        try:
            filename = get_unique_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            success_count += 1
            print(f"Saved file: {filename}")
        except Exception as e:
            error_count += 1
            print(f"Error saving {file.filename}: {e}")
            
    # Only rebuild index if files were successfully uploaded
    if success_count > 0:
        try:
            print("Rebuilding search index...")
            search_engine.reload_documents()
            flash(f'Berhasil mengunggah {success_count} file dan memperbarui indeks.', 'success')
        except Exception as e:
            flash(f'File terunggah tetapi gagal memperbarui indeks: {str(e)}', 'warning')
            
    if error_count > 0:
        flash(f'Gagal mengunggah {error_count} file.', 'error')
    
    return redirect(url_for('index'))


@app.route('/delete/<filename>', methods=['POST'])
@login_required
def delete_file(filename):
    """Handle file deletion"""
    try:
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            flash(f'File "{filename}" not found.', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(filename):
            flash('Cannot delete this file type.', 'error')
            return redirect(url_for('index'))
        
        os.remove(file_path)
        search_engine.reload_documents()
        
        flash(f'File "{filename}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/delete_all', methods=['POST'])
@login_required
def delete_all_files():
    """Delete all uploaded documents"""
    try:
        folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(folder):
            flash('Folder data tidak ditemukan.', 'error')
            return redirect(url_for('index'))

        removed = 0
        errors = 0

        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if not os.path.isfile(file_path):
                continue
            # Only delete supported types
            if not filename.lower().endswith(('.txt', '.pdf')):
                continue
            try:
                os.remove(file_path)
                removed += 1
            except Exception as e:
                print(f"Error deleting {filename}: {e}")
                errors += 1

        # Reload index after deletion
        try:
            search_engine.reload_documents()
        except Exception as e:
            flash(f'File dihapus tetapi gagal memperbarui indeks: {str(e)}', 'warning')
            return redirect(url_for('index'))

        if removed > 0:
            msg = f'Berhasil menghapus {removed} file.'
            if errors > 0:
                msg += f' Gagal menghapus {errors} file.'
            flash(msg, 'success' if errors == 0 else 'warning')
        else:
            flash('Tidak ada file untuk dihapus.', 'warning')

    except Exception as e:
        flash(f'Gagal menghapus semua file: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/api/files', methods=['GET'])
@login_required
def api_get_files():
    """API endpoint to get list of files"""
    try:
        files = get_file_list()
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    """API endpoint for search"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_n = data.get('top_n', 5)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        results = search_engine.search(query, top_n=top_n)
        
        # Format results for JSON response
        formatted_results = []
        for filename, content, score in results:
            formatted_results.append({
                'filename': filename,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'score': round(score, 4)
            })
        
        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/reload', methods=['POST'])
@login_required
def reload_index():
    """Manually reload the search index"""
    try:
        search_engine.reload_documents()
        flash('Search index reloaded successfully!', 'success')
    except Exception as e:
        flash(f'Error reloading index: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('File is too large. Maximum total upload size is 200MB.', 'error')
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
