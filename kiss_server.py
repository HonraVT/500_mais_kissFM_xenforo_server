import time
from threading import Thread, Event

from flask import Flask, request, render_template, jsonify

from config import Config
from kiss_xenforo import run, set_position, load_db

conf = Config()

app = Flask(__name__)

data = {
    "running": False,
}

stop_event = Event()
thread = None


def run_thread():
    while not stop_event.is_set():
        try:
            run()
        except Exception as e:
            print(f"Erro durante a execução: {e}")
            print(f"Reiniciando tarefa em {conf.ERROR_DELAY} segundos...")
            time.sleep(conf.ERROR_DELAY)
        else:
            # print(f"Tarefa finalizada com sucesso. Reiniciando em {conf.DELAY} segundos...")
            time.sleep(conf.DELAY)
        finally:
            if stop_event.is_set():
                print("Execução interrompida.")
                break


@app.route('/rank', methods=['GET', 'POST'])
def rank():
    if request.method == 'POST':
        try:
            new_position = int(request.form.get('position', 500))
            set_position(new_position)
            return jsonify({"status": "success", "position": new_position}), 200
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid position"}), 400

    return render_template('rank.html', position=load_db()["position"])


@app.route('/configure', methods=['GET', 'POST'])
def configure():
    global thread

    message = "Aguardando ação."
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'start' and not data["running"]:
            stop_event.clear()
            thread = Thread(target=run_thread, daemon=True)
            thread.start()
            data["running"] = True
            message = "Processo iniciado."
        elif action == 'stop' and data["running"]:
            stop_event.set()
            if thread:
                thread.join()
            data["running"] = False
            message = "Processo parado."
        elif action == 'restart':
            stop_event.set()
            if thread:
                thread.join()
            stop_event.clear()
            thread = Thread(target=run_thread, daemon=True)
            thread.start()
            data["running"] = True
            message = "Processo reiniciado."
        else:
            message = "Ação inválida ou processo já no estado solicitado."

    return render_template('configure.html', message=message, running=data["running"])


if __name__ == '__main__':
    # app.run(host='127.0.0.1', port=8000)
    app.run(host="0.0.0.0", port=80)
