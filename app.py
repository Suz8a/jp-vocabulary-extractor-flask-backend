from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import tempfile
import os
import shutil
import csv

app = Flask(__name__)
CORS(app)

@app.route("/extract", methods=["POST"])
def extract_vocab():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]

    # Create temporary directory to hold input file
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.filename)
        uploaded_file.save(input_path)
        options = request.form.get('options')

        # Run the extractor in the temp directory
        # determine file type from uploaded filename extension (fallback to 'auto')
        _, ext = os.path.splitext(uploaded_file.filename)
        file_type = ext.lstrip('.').lower() if ext else 'auto'
        if not file_type:
            file_type = 'auto'

        result = subprocess.run(
            ["jpvocab-extractor", *options.split() ,"--type", file_type, input_path],
            cwd=tmpdir,  # run command in temp folder
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500

        csv_file_path = os.path.join(tmpdir, "vocab_all.csv")
        if not os.path.exists(csv_file_path):
            return jsonify({"error": "vocab_all.csv not found"}), 500

        # Read CSV for preview
        with open(csv_file_path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            vocab_list = [row for row in reader]

        # Save CSV to another temporary file for download
        download_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        shutil.copy(csv_file_path, download_file.name)
        download_file_path = download_file.name
        download_file.close()

    return jsonify({
        "headers": headers,
        "vocabulary": vocab_list,
        "csv_path": download_file_path
    })


@app.route("/download", methods=["GET"])
def download_csv():
    csv_path = request.args.get("path")
    if not csv_path or not os.path.exists(csv_path):
        return "CSV file not found", 404

    response = send_file(csv_path, mimetype="text/csv", as_attachment=True, download_name="vocabulary.csv")
    
    # Clean up temp CSV after download
    os.remove(csv_path)
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
