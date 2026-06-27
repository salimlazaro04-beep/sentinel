from flask import Flask, render_template, request, jsonify
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact', methods=['POST'])
def contact():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not message:
        return jsonify({'success': False, 'error': 'Preencha todos os campos.'}), 400

    # Em produção: integrar com SMTP ou serviço de e-mail
    print(f"[{datetime.datetime.now()}] Contato de {name} <{email}>: {message}")
    return jsonify({'success': True, 'message': 'Mensagem recebida! Entraremos em contato.'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)