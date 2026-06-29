from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO, emit, join_room
import datetime
import re
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ── RATE LIMITING & SEGURANÇA ─────────────────────────────────
rate_limit = {}
blocked_ips = {}
MAX_MSGS = 3
RESET_HOURS = 24
MAX_ATTEMPTS = 10
BLOCK_MINUTES = 60

def get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def is_blocked(ip):
    if ip in blocked_ips:
        if (datetime.datetime.now() - blocked_ips[ip]).total_seconds() < BLOCK_MINUTES * 60:
            return True
        del blocked_ips[ip]
    return False

def register_attempt(ip):
    if ip not in rate_limit:
        rate_limit[ip] = {'count': 0, 'attempts': 0, 'first_time': datetime.datetime.now()}
    rate_limit[ip]['attempts'] = rate_limit[ip].get('attempts', 0) + 1
    if rate_limit[ip]['attempts'] >= MAX_ATTEMPTS:
        blocked_ips[ip] = datetime.datetime.now()
        print(f"[SEGURANÇA] IP bloqueado: {ip}")
        return False
    return True

def check_limit(ip):
    now = datetime.datetime.now()
    if ip in rate_limit:
        data = rate_limit[ip]
        diff = now - data['first_time']
        if diff.total_seconds() > RESET_HOURS * 3600:
            rate_limit[ip] = {'count': 0, 'attempts': 0, 'first_time': now}
        if rate_limit[ip]['count'] >= MAX_MSGS:
            restante = RESET_HOURS * 3600 - diff.total_seconds()
            horas = int(restante // 3600)
            minutos = int((restante % 3600) // 60)
            return False, f'Limite atingido. Tente novamente em {horas}h {minutos}min.'
    else:
        rate_limit[ip] = {'count': 0, 'attempts': 0, 'first_time': now}
    return True, None

def sanitize(text, max_len=500):
    if not text or not isinstance(text, str):
        return ''
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'[<>"\';\\]', '', text)
    return text.strip()[:max_len]

def valid_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))

def detect_injection(text):
    patterns = [
        r'(?i)(select|insert|update|delete|drop|union|exec|script)',
        r'(?i)(onload|onerror|onclick|javascript:)',
        r'(?i)(<script|<iframe|<object)',
        r'(\.\./|\.\.\\)',
    ]
    return any(re.search(p, text) for p in patterns)

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ── ROTAS HTTP ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/contact', methods=['POST'])
def contact():
    ip = get_ip()
    if is_blocked(ip):
        abort(429)
    if not request.is_json:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Requisição inválida.'}), 400
    data = request.get_json(silent=True)
    if not data:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Dados inválidos.'}), 400

    name    = sanitize(data.get('name', ''), 100)
    email   = sanitize(data.get('email', ''), 150)
    message = sanitize(data.get('message', ''), 1000)

    if not name or len(name) < 2:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Nome inválido.'}), 400
    if not email or not valid_email(email):
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'E-mail inválido.'}), 400
    if not message or len(message) < 10:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Mensagem muito curta.'}), 400
    for field in [name, email, message]:
        if detect_injection(field):
            blocked_ips[ip] = datetime.datetime.now()
            return jsonify({'success': False, 'error': 'Conteúdo inválido.'}), 403

    allowed, msg = check_limit(ip)
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 429

    rate_limit[ip]['count'] += 1
    restante = MAX_MSGS - rate_limit[ip]['count']
    print(f"[{datetime.datetime.now()}] {name} <{email}> (IP:{ip}): {message}")

    return jsonify({
        'success': True,
        'message': f'Mensagem enviada! Voce ainda pode enviar mais {restante} mensagem(ns) hoje.' if restante > 0 else 'Mensagem enviada! Limite diario atingido.'
    })

# ── WEBSOCKET — agente envia dados aqui ──────────────────────
@socketio.on('connect')
def on_connect():
    print(f"[WS] Cliente conectado: {request.sid}")

@socketio.on('disconnect')
def on_disconnect():
    print(f"[WS] Cliente desconectado: {request.sid}")

@socketio.on('agent_data')
def on_agent_data(data):
    # Agente envia dados → servidor repassa para o dashboard
    token = data.get('token', '')
    if not token:
        return
    # Repassa para a sala do token (dashboard do usuário)
    emit('dashboard_update', data, room=token, include_self=False)

@socketio.on('join_dashboard')
def on_join_dashboard(data):
    token = data.get('token', '')
    if token:
        join_room(token)
        emit('status', {'msg': 'Conectado ao dashboard'})

@app.errorhandler(429)
def too_many(e):
    return jsonify({'success': False, 'error': 'Muitas tentativas.'}), 429

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)