from flask import Flask, render_template, jsonify
import json
from datetime import datetime
from .metrics import metrics_collector
from .logger_config import mqtt_logger

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Página principal del dashboard"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health_check():
    """Endpoint de salud del sistema"""
    try:
        health = metrics_collector.get_health_status()
        return jsonify(health)
    except Exception as e:
        mqtt_logger.log_error("Error getting health status", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/metrics')
def get_metrics():
    """Endpoint para obtener métricas actuales"""
    try:
        summary = metrics_collector.get_metrics_summary()
        return jsonify(summary)
    except Exception as e:
        mqtt_logger.log_error("Error getting metrics", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/recent')
def get_recent_alerts():
    """Endpoint para obtener alertas recientes"""
    try:
        # Leer últimas 50 líneas del log de alertas
        alerts = []
        try:
            with open('logs/alerts/alerts.log', 'r') as f:
                lines = f.readlines()
                for line in lines[-50:]:  # Últimas 50 alertas
                    if 'Alert created' in line:
                        alerts.append(line.strip())
        except FileNotFoundError:
            pass
        
        return jsonify({'alerts': alerts})
    except Exception as e:
        mqtt_logger.log_error("Error getting recent alerts", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<log_type>')
def get_logs(log_type):
    """Endpoint para obtener logs específicos"""
    try:
        log_files = {
            'system': 'logs/mqtt/system.log',
            'alerts': 'logs/alerts/alerts.log',
            'errors': 'logs/errors/errors.log',
            'metrics': 'logs/metrics.log'
        }
        
        if log_type not in log_files:
            return jsonify({'error': 'Invalid log type'}), 400
        
        logs = []
        try:
            with open(log_files[log_type], 'r') as f:
                logs = f.readlines()[-100:]  # Últimas 100 líneas
        except FileNotFoundError:
            logs = []
        
        return jsonify({'logs': logs})
    except Exception as e:
        mqtt_logger.log_error(f"Error getting {log_type} logs", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
