from flask import request, jsonify
from datetime import datetime


# TEMP store – replace with DB later
pdf_progress_store = {}

@app.route('/api/pdf-progress', methods=['POST'])
def save_pdf_progress():
    data = request.get_json()
    file = data.get("file")
    page = data.get("page")
    total = data.get("total")
    timestamp = datetime.utcnow().isoformat()

    if not file or page is None:
        return jsonify({"error": "Missing data"}), 400

    pdf_progress_store[file] = {
        "page": page,
        "total": total,
        "updated": timestamp
    }

    return jsonify({"status": "ok", "progress": pdf_progress_store[file]})
