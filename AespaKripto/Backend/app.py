from flask import Flask, render_template, request, jsonify, send_file
import os
import tempfile
import base64
import json

from ecc_crypto import generate_ecc_keypair, encrypt_ecc, decrypt_ecc
from audio_stego import embed_data_in_audio, extract_data_from_audio

app = Flask(__name__, template_folder="../templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate_keys", methods=["GET"])
def generate_keys():
    private_key, public_key = generate_ecc_keypair()
    return jsonify({
        "private_key": private_key,
        "public_key": public_key
    })


@app.route("/generate_license", methods=["POST"])
def generate_license():
    data = request.json
    customer_info = {
        "name": data["name"],
        "email": data["email"]
    }
    private_key = data["private_key"]
    validity_days = data.get("days", 365)

    from datetime import datetime, timedelta
    from hashlib import sha256
    import secrets

    issue_date = datetime.now()
    expiry_date = issue_date + timedelta(days=int(validity_days))

    license_data = {
        "customer": customer_info,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "license_id": secrets.token_hex(8),
        "type": "standard",
        "features": data.get("features", []),
    }

    json_data = json.dumps(license_data, indent=2)
    license_hash = sha256(json_data.encode()).hexdigest()
    license_data["hash"] = license_hash

    encrypted = encrypt_ecc(json.dumps(license_data), private_key)
    encoded = base64.b64encode(encrypted).decode()

    return jsonify({"license": encoded})


@app.route("/embed_audio", methods=["POST"])
def embed_audio():
    license_data = request.form.get("license")
    audio_file = request.files["audio"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_input:
        audio_file.save(temp_input.name)

    output_path = temp_input.name.replace(".wav", "_stego.wav")

    success = embed_data_in_audio(license_data, temp_input.name, output_path)

    if not success:
        return jsonify({"error": "Failed to embed license"}), 500

    return send_file(output_path, as_attachment=True, download_name="stego_output.wav")


@app.route("/verify_license", methods=["POST"])
def verify_license():
    audio_file = request.files["audio"]
    public_key = request.form.get("public_key")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        audio_file.save(temp_audio.name)

    extracted = extract_data_from_audio(temp_audio.name)
    if not extracted:
        return jsonify({"error": "Failed to extract data"}), 400

    try:
        encrypted = base64.b64decode(extracted)
        decrypted_json = decrypt_ecc(encrypted, public_key)
        data = json.loads(decrypted_json)

        return jsonify({"license": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)