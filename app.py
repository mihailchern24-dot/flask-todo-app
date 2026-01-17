"""Основное приложение Flask для Render"""
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extensions import db, migrate, login_manager
from models import User, Task

load_dotenv()

def create_app():
    """Фабрика приложений Flask для Render"""
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static')
    app.config.from_object(Config)
    
    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    return app

APP = create_app()

# ==================== Routes: Auth ====================
@APP.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@APP.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('Вход выполнен успешно!', 'success')
            return redirect(next_page or url_for('index'))
        
        flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@APP.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# ==================== Routes: Pages ====================
@APP.route('/')
@login_required
def index():
    """Главная страница с задачами"""
    return render_template('index.html', username=current_user.username)

@APP.route('/about')
def about():
    """Страница "О проекте" (доступна без авторизации)"""
    return render_template('about.html')

# ==================== API: Tasks ====================
@APP.route('/api/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    """Получение списка задач с пагинацией"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', APP.config['ITEMS_PER_PAGE']))
    except ValueError:
        page = 1
        per_page = APP.config['ITEMS_PER_PAGE']
    
    # Оптимизированный запрос с сортировкой
    query = Task.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Task.done.asc(),
        Task.due_iso.asc().nullsfirst(),
        Task.created_at.desc()
    )
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    items = []
    for task in pagination.items:
        items.append({
            'id': str(task.id),
            'uuid': task.uuid,
            'title': task.title,
            'description': task.description or '',
            'due_iso': task.due_iso,
            'done': str(task.done),
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'is_overdue': task.is_overdue
        })
    
    return jsonify({
        'items': items,
        'meta': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

@APP.route('/api/tasks', methods=['POST'])
@login_required
def api_add_task():
    """Добавление новой задачи"""
    data = request.json or {}
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    due_iso = data.get('due_iso', '')
    
    if not title:
        return jsonify({'error': 'Название задачи обязательно'}), 400
    
    # Валидация даты
    if due_iso:
        try:
            datetime.fromisoformat(due_iso.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Неверный формат даты'}), 400
    
    task = Task(
        user_id=current_user.id,
        title=title,
        description=description if description else None,
        due_iso=due_iso if due_iso else None,
        done=False
    )
    
    db.session.add(task)
    db.session.commit()
    
    payload = {
        'id': str(task.id),
        'uuid': task.uuid,
        'title': task.title,
        'description': task.description or '',
        'due_iso': task.due_iso,
        'done': str(task.done),
        'user_id': task.user_id
    }
    
    return jsonify(payload), 201

@APP.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def api_update_task(task_id):
    """Обновление задачи"""
    data = request.json or {}
    
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    # Обновляем только переданные поля
    if 'title' in data:
        task.title = data['title'].strip()
    if 'description' in data:
        task.description = data['description'].strip() or None
    if 'due_iso' in data:
        task.due_iso = data['due_iso'] or None
    if 'done' in data:
        task.done = str(data['done']).lower() in ('true', '1', 'yes', 'y')
    
    db.session.commit()
    
    payload = {
        'id': str(task.id),
        'uuid': task.uuid,
        'title': task.title,
        'description': task.description or '',
        'due_iso': task.due_iso,
        'done': str(task.done)
    }
    
    return jsonify(payload)

@APP.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    """Удаление задачи"""
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    task_id_str = str(task.id)
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'success': True, 'id': task_id_str})

# ==================== Проверка напоминаний ====================
@APP.route('/api/check_reminders')
@login_required
def check_reminders():
    """Проверка напоминаний (вызывается из JavaScript)"""
    now = datetime.now(timezone.utc)
    reminders = []
    
    tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.done == False,
        Task.due_iso.isnot(None),
        Task.due_iso != ''
    ).all()
    
    for task in tasks:
        try:
            due = datetime.fromisoformat(task.due_iso.replace('Z', '+00:00'))
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            
            time_to_due = (due - now).total_seconds()
            if 0 <= time_to_due <= 300:  # 5 минут до дедлайна
                reminders.append({
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description or '',
                    'due_iso': task.due_iso
                })
        except (ValueError, TypeError):
            continue
    
    return jsonify({'reminders': reminders})

# ==================== Инициализация БД ====================
@APP.before_app_first_request
def init_db():
    """Инициализация базы данных при первом запросе"""
    with APP.app_context():
        try:
            db.create_all()
            print("✅ База данных успешно инициализирована")
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            # Если ошибка, создаем таблицы принудительно
            try:
                from extensions import db
                db.create_all()
                print("✅ Таблицы созданы принудительно")
            except:
                print("❌ Не удалось создать таблицы")

# ==================== Обработчики ошибок ====================
@APP.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@APP.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ==================== Запуск приложения ====================
if __name__ == '__main__':
    with APP.app_context():
        db.create_all()
    APP.run(host='0.0.0.0', port=5000, debug=False)
