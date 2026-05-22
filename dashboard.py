# dashboard.py
import subprocess
import os
import signal
from flask import Flask, render_template_string, redirect, url_for
import csv

app = Flask(__name__)

# --- KONFIGURATION ---
ORDNER = os.path.dirname(os.path.abspath(__file__))
HAUPT_SCRIPT = os.path.join(ORDNER, "main.py")
RESET_SCRIPT = os.path.join(ORDNER, "FinalReset.py")
CSV_DATEI = os.path.join(ORDNER, "gewaechshaus_log.csv")

# Globaler Prozess-Handle
prozess = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gewaechshaus Dashboard</title>
<meta http-equiv="refresh" content="10">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 1.8em; color: #4ecca3; }
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin: 10px 0;
            font-size: 1.1em;
        }
        .status-running { background: #4ecca3; color: #1a1a2e; }
        .status-stopped { background: #e74c3c; color: #fff; }
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .btn {
            padding: 15px 40px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            color: #fff;
            transition: transform 0.1s;
        }
        .btn:active { transform: scale(0.95); }
        .btn-start { background: #4ecca3; color: #1a1a2e; }
        .btn-stop { background: #e74c3c; }
        .btn-disabled { background: #555; cursor: not-allowed; }
        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }
        .data-card {
            background: #16213e;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .data-card .label { font-size: 0.85em; color: #888; margin-bottom: 5px; }
        .data-card .value { font-size: 1.8em; font-weight: bold; color: #4ecca3; }
        .data-card .value.warn { color: #f39c12; }
        .data-card .value.danger { color: #e74c3c; }
        .chart-container {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .chart-container h3 { color: #4ecca3; margin-bottom: 15px; }
        canvas { max-height: 300px; }
        .akteur-row {
            margin-bottom: 10px;
        }
        .akteur-row canvas {
            max-height: 80px;
        }
        .akteur-label {
            color: #888;
            font-size: 0.85em;
            margin-bottom: 3px;
        }
        .log-section {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-top: 25px;
        }
        .log-section h3 { margin-bottom: 10px; color: #4ecca3; }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
        }
        th, td {
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #2a2a4a;
        }
        th { color: #888; }
</style>
</head>
<body>
<div class="header">
<h1>Gewaechshaus Dashboard</h1>
<div class="status-badge {{ 'status-running' if running else 'status-stopped' }}">
            {{ 'SYSTEM AKTIV' if running else 'SYSTEM AUS' }}
</div>
</div>

    <div class="controls">
        {% if not running %}
<a href="/start" class="btn btn-start">Start</a>
        {% else %}
<a href="/start" class="btn btn-disabled">Laeuft bereits</a>
        {% endif %}

        {% if running %}
<a href="/stop" class="btn btn-stop">Stop</a>
        {% else %}
<a href="/stop" class="btn btn-disabled">Bereits aus</a>
        {% endif %}
</div>

    {% if letzte_daten %}
<div class="data-grid">
<div class="data-card">
<div class="label">Temperatur</div>
<div class="value {{ 'danger' if letzte_daten.temp > 25 else 'warn' if letzte_daten.temp < 22 else '' }}">
                {{ letzte_daten.temp }} C
</div>
</div>
<div class="data-card">
<div class="label">Luftfeuchte</div>
<div class="value">{{ letzte_daten.hum }}%</div>
</div>
<div class="data-card">
<div class="label">Boden</div>
<div class="value {{ 'danger' if letzte_daten.boden_trocken else '' }}">
                {{ 'TROCKEN' if letzte_daten.boden_trocken else 'FEUCHT' }}
</div>
</div>
<div class="data-card">
<div class="label">Status</div>
<div class="value">{{ letzte_daten.status }}</div>
</div>
</div>
    {% endif %}

    {% if chart_daten %}
<div class="chart-container">
<h3>Temperatur und Luftfeuchte</h3>
<canvas id="tempHumChart"></canvas>
</div>

    <div class="chart-container">
<h3>Akteure</h3>
<div class="akteur-row">
<div class="akteur-label">Heizung</div>
<canvas id="heizungChart"></canvas>
</div>
<div class="akteur-row">
<div class="akteur-label">Luefter</div>
<canvas id="luefterChart"></canvas>
</div>
<div class="akteur-row">
<div class="akteur-label">Vernebler</div>
<canvas id="nebelChart"></canvas>
</div>
</div>
    {% endif %}

    {% if log_zeilen %}
<div class="log-section">
<h3>Letzte Messungen</h3>
<table>
<tr>
<th>Zeit</th>
<th>Temp</th>
<th>Feuchte</th>
<th>Boden</th>
<th>Status</th>
<th>Heizung</th>
<th>Luefter</th>
<th>Nebel</th>
</tr>
            {% for z in log_zeilen %}
<tr>
<td>{{ z.zeit }}</td>
<td>{{ z.temp }} C</td>
<td>{{ z.hum }}%</td>
<td>{{ 'trocken' if z.boden else 'feucht' }}</td>
<td>{{ z.status }}</td>
<td>{{ 'AN' if z.heizung else '-' }}</td>
<td>{{ 'AN' if z.luefter else '-' }}</td>
<td>{{ 'AN' if z.nebel else '-' }}</td>
</tr>
            {% endfor %}
</table>
</div>
    {% endif %}

    {% if chart_daten %}
<script>
        const zeitLabels = {{ chart_daten.zeit | tojson }};
        const tempDaten = {{ chart_daten.temp | tojson }};
        const humDaten = {{ chart_daten.hum | tojson }};
        const heizungDaten = {{ chart_daten.heizung | tojson }};
        const luefterDaten = {{ chart_daten.luefter | tojson }};
        const nebelDaten = {{ chart_daten.nebel | tojson }};

        // Temperatur & Luftfeuchte Chart
        new Chart(document.getElementById('tempHumChart'), {
            type: 'line',
            data: {
                labels: zeitLabels,
                datasets: [
                    {
                        label: 'Temperatur (C)',
                        data: tempDaten,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.3,
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Luftfeuchte (%)',
                        data: humDaten,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.3,
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        ticks: { color: '#888', maxTicksLimit: 15 },
                        grid: { color: '#2a2a4a' }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'Temperatur (C)', color: '#e74c3c' },
                        ticks: { color: '#e74c3c' },
                        grid: { color: '#2a2a4a' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: 'Luftfeuchte (%)', color: '#3498db' },
                        ticks: { color: '#3498db' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#eee' } }
                }
            }
        });

        // Akteur-Charts: gemeinsame Optionen
        function erstelleAkteurChart(canvasId, daten, farbe) {
            new Chart(document.getElementById(canvasId), {
                type: 'line',
                data: {
                    labels: zeitLabels,
                    datasets: [{
                        data: daten,
                        borderColor: farbe,
                        backgroundColor: farbe.replace(')', ', 0.3)').replace('rgb', 'rgba'),
                        fill: true,
                        stepped: true,
                        pointRadius: 0,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            ticks: { color: '#888', maxTicksLimit: 10, font: { size: 10 } },
                            grid: { color: '#2a2a4a' }
                        },
                        y: {
                            min: -0.1,
                            max: 1.1,
                            ticks: {
                                color: '#888',
                                callback: function(value) {
                                    if (value === 0) return 'AUS';
                                    if (value === 1) return 'AN';
                                    return '';
                                },
                                stepSize: 1
                            },
                            grid: { color: '#2a2a4a' }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        erstelleAkteurChart('heizungChart', heizungDaten, 'rgb(231, 76, 60)');
        erstelleAkteurChart('luefterChart', luefterDaten, 'rgb(46, 204, 113)');
        erstelleAkteurChart('nebelChart', nebelDaten, 'rgb(52, 152, 219)');
</script>
    {% endif %}
</body>
</html>
"""


def lese_letzte_csv_zeilen(anzahl=10):
    """Liest die letzten N Zeilen der CSV-Datei."""
    if not os.path.isfile(CSV_DATEI):
        return [], None

    zeilen = []
    try:
        with open(CSV_DATEI, 'r') as f:
            reader = list(csv.reader(f))
            if len(reader) <= 1:
                return [], None

            letzte = reader[-anzahl:] if len(reader) > anzahl else reader[1:]

            for row in letzte:
                if len(row) >= 9:
                    zeilen.append({
                        'zeit': row[0].split(' ')[1] if ' ' in row[0] else row[0],
                        'temp': row[1],
                        'hum': row[2],
                        'boden': row[3] in ('True', '1'),
                        'status': row[4],
                        'luefter': row[6] in ('True', '1'),
                        'heizung': row[7] in ('True', '1'),
                        'nebel': row[8] in ('True', '1')
                    })
    except Exception as e:
        print(f"CSV Lesefehler: {e}")
        return [], None

    letzte_daten = None
    if zeilen:
        lz = zeilen[-1]
        letzte_daten = type('obj', (object,), {
            'temp': float(lz['temp']),
            'hum': float(lz['hum']),
            'boden_trocken': lz['boden'],
            'status': lz['status']
        })()

    # Neueste Messung zuoberst
    zeilen.reverse()

    return zeilen, letzte_daten


def lese_chart_daten(anzahl=60):
    """Liest die letzten N Zeilen fuer die Graphen."""
    if not os.path.isfile(CSV_DATEI):
        return None

    try:
        with open(CSV_DATEI, 'r') as f:
            reader = list(csv.reader(f))
            if len(reader) <= 1:
                return None

            letzte = reader[-anzahl:] if len(reader) > anzahl else reader[1:]

            chart_daten = {
                'zeit': [],
                'temp': [],
                'hum': [],
                'heizung': [],
                'luefter': [],
                'nebel': []
            }

            for row in letzte:
                if len(row) >= 9:
                    zeit = row[0].split(' ')[1] if ' ' in row[0] else row[0]
                    chart_daten['zeit'].append(zeit)
                    try:
                        chart_daten['temp'].append(float(row[1]))
                    except ValueError:
                        chart_daten['temp'].append(None)
                    try:
                        chart_daten['hum'].append(float(row[2]))
                    except ValueError:
                        chart_daten['hum'].append(None)
                    chart_daten['heizung'].append(1 if row[7] in ('True', '1') else 0)
                    chart_daten['luefter'].append(1 if row[6] in ('True', '1') else 0)
                    chart_daten['nebel'].append(1 if row[8] in ('True', '1') else 0)

            return chart_daten if chart_daten['zeit'] else None

    except Exception as e:
        print(f"Chart-Daten Lesefehler: {e}")
        return None


@app.route('/')
def index():
    global prozess
    running = prozess is not None and prozess.poll() is None
    log_zeilen, letzte_daten = lese_letzte_csv_zeilen(10)
    chart_daten = lese_chart_daten(60)

    return render_template_string(HTML_TEMPLATE,
                                  running=running,
                                  letzte_daten=letzte_daten,
                                  log_zeilen=log_zeilen,
                                  chart_daten=chart_daten)


@app.route('/start')
def start():
    global prozess

    if prozess is not None and prozess.poll() is None:
        return redirect(url_for('index'))

    # 1. Reset-Script ausfuehren
    try:
        subprocess.run(['python3', RESET_SCRIPT], timeout=10)
        print("[Dashboard] Reset-Script ausgefuehrt.")
    except Exception as e:
        print(f"[Dashboard] Reset-Fehler: {e}")

    # 2. Hauptscript starten
    try:
        prozess = subprocess.Popen(
            ['python3', '-u', HAUPT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        print(f"[Dashboard] System gestartet (PID: {prozess.pid})")
    except Exception as e:
        print(f"[Dashboard] Start-Fehler: {e}")

    return redirect(url_for('index'))


@app.route('/stop')
def stop():
    global prozess

    if prozess is not None and prozess.poll() is None:
        prozess.send_signal(signal.SIGINT)
        try:
            prozess.wait(timeout=10)
        except subprocess.TimeoutExpired:
            prozess.kill()
        print("[Dashboard] System gestoppt.")

    # Reset-Script zur Sicherheit
    try:
        subprocess.run(['python3', RESET_SCRIPT], timeout=10)
    except Exception:
        pass

    prozess = None
    return redirect(url_for('index'))


if __name__ == '__main__':
    print("========================================")
    print(" GEWAECHSHAUS DASHBOARD")
    print(" Oeffne: http://<PI-IP>:5000")
    print("========================================")
    app.run(host='0.0.0.0', port=5000, debug=False)