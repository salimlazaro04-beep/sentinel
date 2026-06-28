from flask import Flask, render_template, request, jsonify, abort
import datetime
import re
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── RATE LIMITING ─────────────────────────────────────────────
rate_limit = {}
blocked_ips = {}
MAX_MSGS = 3
RESET_HOURS = 24
MAX_ATTEMPTS = 10       # tentativas antes de bloquear o IP
BLOCK_MINUTES = 60      # minutos de bloqueio

def get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def is_blocked(ip):
    if ip in blocked_ips:
        block_time = blocked_ips[ip]
        if (datetime.datetime.now() - block_time).total_seconds() < BLOCK_MINUTES * 60:
            return True
        else:
            del blocked_ips[ip]
    return False

def register_attempt(ip):
    now = datetime.datetime.now()
    if ip not in rate_limit:
        rate_limit[ip] = {'count': 0, 'attempts': 0, 'first_time': now}
    rate_limit[ip]['attempts'] = rate_limit[ip].get('attempts', 0) + 1
    if rate_limit[ip]['attempts'] >= MAX_ATTEMPTS:
        blocked_ips[ip] = now
        print(f"[SEGURANÇA] IP bloqueado por excesso de tentativas: {ip}")
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

# ── VALIDAÇÃO E SANITIZAÇÃO ───────────────────────────────────
def sanitize(text, max_len=500):
    if not text or not isinstance(text, str):
        return ''
    # Remove tags HTML e scripts
    text = re.sub(r'<[^>]*>', '', text)
    # Remove caracteres perigosos
    text = re.sub(r'[<>"\';\\]', '', text)
    return text.strip()[:max_len]

def valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def detect_injection(text):
    patterns = [
        r'(?i)(select|insert|update|delete|drop|union|exec|script)',
        r'(?i)(onload|onerror|onclick|javascript:)',
        r'(?i)(<script|<iframe|<object)',
        r'(\.\./|\.\.\\)',  # path traversal
    ]
    for p in patterns:
        if re.search(p, text):
            return True
    return False

# ── HEADERS DE SEGURANÇA ──────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self' https://script.google.com;"
    )
    return response

# ── ROTAS ─────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact():
    ip = get_ip()

    # Verifica se IP está bloqueado
    if is_blocked(ip):
        print(f"[SEGURANÇA] Tentativa de IP bloqueado: {ip}")
        abort(429)

    # Verifica Content-Type
    if not request.is_json:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Requisição inválida.'}), 400

    data = request.get_json(silent=True)
    if not data:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Dados inválidos.'}), 400

    # Sanitiza entradas
    name    = sanitize(data.get('name', ''), 100)
    email   = sanitize(data.get('email', ''), 150)
    message = sanitize(data.get('message', ''), 1000)

    # Valida campos
    if not name or len(name) < 2:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Nome inválido.'}), 400

    if not email or not valid_email(email):
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'E-mail inválido.'}), 400

    if not message or len(message) < 10:
        register_attempt(ip)
        return jsonify({'success': False, 'error': 'Mensagem muito curta.'}), 400

    # Detecta tentativas de injeção
    for field in [name, email, message]:
        if detect_injection(field):
            blocked_ips[ip] = datetime.datetime.now()
            print(f"[SEGURANÇA] Tentativa de injeção bloqueada — IP: {ip}")
            return jsonify({'success': False, 'error': 'Conteúdo inválido detectado.'}), 403

    # Verifica limite diário
    allowed, msg = check_limit(ip)
    if not allowed:
        return jsonify({'success': False, 'error': msg}), 429

    # Registra mensagem
    rate_limit[ip]['count'] += 1
    restante = MAX_MSGS - rate_limit[ip]['count']
    print(f"[{datetime.datetime.now()}] Contato de {name} <{email}> (IP: {ip}): {message}")

    return jsonify({
        'success': True,
        'message': f'Mensagem enviada! Voce ainda pode enviar mais {restante} mensagem(ns) hoje.' if restante > 0 else 'Mensagem enviada! Limite diario atingido.'
    })

@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({'success': False, 'error': 'Muitas tentativas. Tente mais tarde.'}), 429

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)