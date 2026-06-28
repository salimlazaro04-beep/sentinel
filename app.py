from flask import Flask, render_template, request, jsonify
import datetime

app = Flask(__name__)

rate_limit = {}
MAX_MSGS = 3
RESET_HOURS = 24

def get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()

def check_limit(ip):
    now = datetime.datetime.now()
    if ip in rate_limit:
        data = rate_limit[ip]
        diff = now - data['first_time']
        if diff.total_seconds() > RESET_HOURS * 3600:
            rate_limit[ip] = {'count': 0, 'first_time': now}
        if rate_limit[ip]['count'] >= MAX_MSGS:
            restante = RESET_HOURS * 3600 - diff.total_seconds()
            horas = int(restante // 3600)
            minutos = int((restante % 3600) // 60)
            return False, f'Limite atingido. Tente novamente em {horas}h {minutos}min.'
    else:
        rate_limit[ip] = {'count': 0, 'first_time': now}
    return True, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact():
    data = request.get_json()
    name    = data.get('name', '').strip()
    email   = data.get('email', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not message:
        return jsonify({'success': False, 'error': 'Preencha todos os campos.'}), 400

    ip = get_ip()
    allowed, msg = check_limit(ip)

    if not allowed:
        return jsonify({'success': False, 'error': msg}), 429

    rate_limit[ip]['count'] += 1
    restante = MAX_MSGS - rate_limit[ip]['count']

    print(f"[{datetime.datetime.now()}] Contato de {name} <{email}> (IP: {ip}): {message}")

    return jsonify({
        'success': True,
        'message': f'Mensagem enviada! Voce ainda pode enviar mais {restante} mensagem(ns) hoje.' if restante > 0 else 'Mensagem enviada! Limite diario atingido.'
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)