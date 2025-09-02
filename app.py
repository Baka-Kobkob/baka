            from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
import time
import threading
import os
import requests
from bakong_khqr import KHQR

app = Flask(name)

BAKONG_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiNmFmM2FlMWU3Yzg4NDQ3OCJ9LCJpYXQiOjE3NDM1MTE4MjUsImV4cCI6MTc1MTI4NzgyNX0.ShQ-iQ96VKcqktZZnigUgqaDuooeuPGpnduzdtNxBGA"
MY_ACCOUNT = "veasna_mom1@trmc"
khqr = KHQR(BAKONG_KEY)
current_transactions = {}

os.makedirs('static/images', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    try:
        amount = float(request.form['amount'])
        player_id = request.form.get('player_id', '')
        zone_id = request.form.get('zone_id', '')
        package = request.form.get('package', '')

        if amount <= 0 or amount > 10000:
            return jsonify({'error': 'Invalid amount'}), 400

        transaction_id = f"TRX{int(time.time())}"
        qr_data = khqr.create_qr(
            bank_account=MY_ACCOUNT,
            merchant_name='Baka Store',
            merchant_city='Phnom Penh',
            amount=amount,
            currency='USD',
            store_label='MShop',
            phone_number='855976666666',
            bill_number=transaction_id,
            terminal_label='Cashier-01',
            static=False
        )
        md5_hash = khqr.generate_md5(qr_data)
        qr_img = qrcode.make(qr_data)
        img_io = BytesIO()
        qr_img.save(img_io, 'PNG')
        img_io.seek(0)
        qr_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        expiry = datetime.now() + timedelta(minutes=3)
        current_transactions[transaction_id] = {
            'amount': amount,
            'md5_hash': md5_hash,
            'expiry': expiry.isoformat(),
            'player_id': player_id,
            'zone_id': zone_id,
            'package': package
        }

        return jsonify({
            'success': True,
            'qr_image': qr_base64,
            'transaction_id': transaction_id,
            'amount': amount,
            'expiry': expiry.isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_payment', methods=['POST'])
def check_payment():
    try:
        transaction_id = request.form['transaction_id']
        if transaction_id not in current_transactions:
            return jsonify({'error': 'Invalid transaction ID'}), 400

        transaction = current_transactions[transaction_id]
        if datetime.now() > datetime.fromisoformat(transaction['expiry']):
            return jsonify({'status': 'EXPIRED', 'message': 'QR code has expired'})

        md5_hash = transaction['md5_hash']
        status = check_bakong_payment(md5_hash)

        if status and status.get("responseCode") == 0:
            data = status.get("data", {})
            if data.get("toAccountId") != MY_ACCOUNT:
                return jsonify({'status': 'ERROR', 'message': 'Payment sent to wrong account'})

            amount = float(data.get("amount", 0))
            send_to_telegram(transaction, amount)
            return jsonify({'status': 'PAID', 'message': f'Payment of ${amount:.2f} received!', 'amount': amount})
        else:
            return jsonify({'status': 'UNPAID', 'message': 'Payment not received yet'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_bakong_payment(md5):
    try:
        url = "https://api-bakong.nbc.gov.kh/v1/check_transaction_by_md5"
        headers = {"Authorization": f"Bearer {BAKONG_KEY}", "Content-type": "application/json"}
        response = requests.post(url, headers=headers, json={"md5": md5})
        return response.json()
    except:
        return None
        def send_to_telegram(transaction, amount):
    text = f"PlayerID: {transaction['player_id']}\nZone: {transaction['zone_id']}\nPackage: {transaction['package']}\nAmount: ${amount:.2f}"
    try:
        requests.post(
            'https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage',
            json={'chat_id': 'YOUR_CHAT_ID', 'text': text}
        )
    except:
        pass

if name == 'main':
    app.run(debug=True)
