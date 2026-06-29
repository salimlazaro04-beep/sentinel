"""
Sentinel Agent — Monitor de Sistema
Execute este arquivo no PC que deseja monitorar.
Digite seu token quando solicitado.
"""

import psutil
import socketio
import time
import sys
import re
import datetime

SERVER_URL = 'https://sentinel-9gsm.onrender.com'
INTERVAL   = 5  # segundos entre envios

SUSPICIOUS = [
    'miner', 'xmrig', 'cryptonight', 'monero',
    'keylogger', 'rathole', 'njrat', 'darkcomet',
    'netbus', 'poison', 'backdoor'
]

sio = socketio.Client()

def get_metrics(token):
    # CPU
    cpu = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count(logical=True)
    try:
        cpu_freq = round(psutil.cpu_freq().current / 1000, 2)
    except:
        cpu_freq = 0

    # RAM
    ram = psutil.virtual_memory()
    ram_pct   = ram.percent
    ram_used  = round(ram.used / 1024**3, 1)
    ram_total = round(ram.total / 1024**3, 1)

    # Disco
    disk = psutil.disk_usage('/')
    disk_pct  = disk.percent
    disk_free = round(disk.free / 1024**3, 1)

    # Rede
    net = psutil.net_io_counters()
    time.sleep(0.5)
    net2 = psutil.net_io_counters()
    speed_mb = round((net2.bytes_sent + net2.bytes_recv - net.bytes_sent - net.bytes_recv) / 1024**2 * 2, 2)
    net_sent = round(net2.bytes_sent / 1024**2, 1)
    net_recv = round(net2.bytes_recv / 1024**2, 1)

    # Processos (top 10 por CPU)
    procs = []
    suspicious_found = []
    for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
        try:
            name = p.info['name'] or ''
            cpu_p = round(p.info['cpu_percent'] or 0, 1)
            mem   = round((p.info['memory_info'].rss if p.info['memory_info'] else 0) / 1024**2, 1)
            procs.append({'name': name, 'cpu': cpu_p, 'mem': mem})
            # Verifica processos suspeitos
            for s in SUSPICIOUS:
                if s.lower() in name.lower():
                    suspicious_found.append(name)
        except:
            pass

    procs.sort(key=lambda x: x['cpu'], reverse=True)

    return {
        'token': token,
        'cpu': cpu,
        'cpu_cores': cpu_cores,
        'cpu_freq': cpu_freq,
        'ram_pct': ram_pct,
        'ram_used': ram_used,
        'ram_total': ram_total,
        'disk_pct': disk_pct,
        'disk_free': disk_free,
        'net_speed': f'{speed_mb} MB/s',
        'net_sent': f'{net_sent} MB',
        'net_recv': f'{net_recv} MB',
        'processes': procs[:10],
        'suspicious_procs': list(set(suspicious_found)),
        'timestamp': datetime.datetime.now().isoformat()
    }

@sio.event
def connect():
    print(f'[✔] Conectado ao Sentinel Server')

@sio.event
def disconnect():
    print('[!] Desconectado do servidor. Reconectando...')

@sio.on('status')
def on_status(data):
    print(f"[INFO] {data.get('msg', '')}")

def main():
    print('=' * 50)
    print('  SENTINEL AGENT — Monitor de Sistema')
    print('=' * 50)
    print()

    token = input('Digite seu token (ex: AB12-CD34): ').strip().upper()
    if not re.match(r'^[A-Z0-9]{4}-[A-Z0-9]{4}$', token):
        print('[ERRO] Token inválido. Formato: XXXX-XXXX')
        sys.exit(1)

    print(f'\n[→] Conectando ao servidor...')

    try:
        sio.connect(SERVER_URL)
        print(f'[→] Iniciando monitoramento (a cada {INTERVAL}s)')
        print(f'[→] Acesse o dashboard e insira o token: {token}')
        print(f'[→] Pressione Ctrl+C para parar\n')

        while True:
            try:
                data = get_metrics(token)
                sio.emit('agent_data', data)
                print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}] CPU:{data["cpu"]}% RAM:{data["ram_pct"]}% Disco:{data["disk_pct"]}%')
                time.sleep(INTERVAL)
            except KeyboardInterrupt:
                print('\n[!] Agente encerrado.')
                sio.disconnect()
                break
            except Exception as e:
                print(f'[ERRO] {e}')
                time.sleep(INTERVAL)

    except Exception as e:
        print(f'[ERRO] Não foi possível conectar: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()