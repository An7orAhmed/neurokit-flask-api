from flask import Flask, request, jsonify
from flask_cors import CORS
import neurokit2 as nk
import numpy as np

app = Flask(__name__)
CORS(app=app, origins="*")

def process(signal):
    # Process the ECG signal
    _, info = nk.ecg_process(signal, sampling_rate=500)

    # Clean the R peaks and calculate RR intervals
    cleaned_r = [x for x in info['ECG_R_Peaks'] if not isinstance(x, float) or not np.isnan(x)]
    rr_intervals = np.diff(cleaned_r) 
    positive_rr_intervals = rr_intervals[rr_intervals > 0]
    positive_rr_intervals_ms = positive_rr_intervals / 500
    mean_rr_interval = np.mean(positive_rr_intervals_ms) if len(positive_rr_intervals_ms) > 0 else np.nan

    bpm = 60 / mean_rr_interval if mean_rr_interval > 0 else np.nan

    # PR Interval Calculation
    try:
        cleaned_p = [x for x in info['ECG_P_Peaks'] if not isinstance(x, float) or not np.isnan(x)]
        if len(cleaned_r) != len(cleaned_p):
            # Get the minimum length and trim both lists to the same size
            min_length = min(len(cleaned_p), len(cleaned_r))
            cleaned_p = cleaned_p[:min_length]
            cleaned_r = cleaned_r[:min_length]
        PR_intervals = np.array(cleaned_r) - np.array(cleaned_p)
        positive_pr_intervals = PR_intervals[PR_intervals > 0]  
        pr_intervals_ms = (positive_pr_intervals / 500) * 1000  
        mean_pr_interval = pr_intervals_ms.mean() if len(pr_intervals_ms) > 0 else np.nan
    except KeyError:
        mean_pr_interval = np.nan   

    # QT Interval Calculation
    try:
        cleaned_q = [x for x in info['ECG_Q_Peaks'] if not isinstance(x, float) or not np.isnan(x)]
        cleaned_t = [x for x in info['ECG_T_Peaks'] if not isinstance(x, float) or not np.isnan(x)]
        if len(cleaned_q) != len(cleaned_t):
            # If lengths differ, we can trim the longer one to match the shorter one
            min_length = min(len(cleaned_q), len(cleaned_t))
            cleaned_q = cleaned_q[:min_length]
            cleaned_t = cleaned_t[:min_length]
        QT_intervals = np.array(cleaned_t) - np.array(cleaned_q)
        positive_qt_intervals = QT_intervals[QT_intervals > 0]
        qt_intervals_ms = (positive_qt_intervals / 500) * 1000  
        mean_qt_intervals = qt_intervals_ms.mean() if len(qt_intervals_ms) > 0 else np.nan
    except KeyError:
        mean_qt_intervals = np.nan  

    # QTc Interval Calculation
    qtc_intervals = mean_qt_intervals / np.sqrt(mean_rr_interval) if mean_qt_intervals and mean_rr_interval > 0 else np.nan

    # QRS Duration Calculation
    try:
        cleaned_s = [x for x in info['ECG_S_Peaks'] if not isinstance(x, float) or not np.isnan(x)]
        if len(cleaned_q) != len(cleaned_s):
            min_length = min(len(cleaned_q), len(cleaned_s))
            cleaned_q = cleaned_q[:min_length]
            cleaned_s = cleaned_s[:min_length]
        qrs_intervals = np.array(cleaned_s) - np.array(cleaned_q)
        positive_qrs = qrs_intervals[qrs_intervals > 0] 
        qrs_duration = (positive_qrs / 500) * 1000 
        mean_qrs_duration = qrs_duration.mean() if len(qrs_duration) > 0 else np.nan
    except KeyError:
        mean_qrs_duration = np.nan 

    result = {
        'bpm': 0 if np.isnan(bpm) else int(bpm),
        'pr_int': 0 if np.isnan(mean_pr_interval) else int(mean_pr_interval),
        'qrs_int': 0 if np.isnan(mean_qrs_duration) else int(mean_qrs_duration),
        'qt_int': 0 if np.isnan(mean_qt_intervals) else int(mean_qt_intervals),
        'qtc_int': 0 if np.isnan(qtc_intervals) else int(qtc_intervals) 
    }

    return result

@app.route('/')
def sayHello():
    return "Hello, World!"

@app.route('/process', methods=['GET'])
def process_get():
    try:
        result = {"response": "success"}
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/process', methods=['POST'])
def process_ecg():
    try:
        data = request.json
        signal = data.get('data')
        result = process(signal)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5072)