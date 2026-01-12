import logging
import random
import time
from flask import Flask, request

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s %(levelname)s [TraceID: %(otelTraceID)s] %(message)s')
logger = logging.getLogger(__name__)

@app.route("/pay", methods=["POST"])
def pay():
    delay = random.uniform(0.1, 0.5)
    time.sleep(delay)
    
    amount = request.json.get("amount", 0)
    
    if amount < 0:
        logger.error("Negatif tutar hatası!")
        return {"status": "error", "message": "Invalid amount"}, 400
        
    logger.info(f"Ödeme alındı: {amount} TL. İşlem süresi: {delay:.2f}s")
    return {"status": "success", "amount": amount}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
