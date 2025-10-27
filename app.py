import os
import json
import asyncio
import base64
import logging
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# 🔐 AES Encryption (misol sifatida)
def encrypt_message(message: bytes):
    try:
        key = b"1234567890abcdef"  # o'z kaliting bilan almashtir
        iv = b"abcdef1234567890"
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        padded = message + b"\0" * (16 - len(message) % 16)
        encrypted = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        app.logger.error(f"Encryption error: {e}")
        return None

# 📦 Protobuf xabari yaratish (mock)
def create_protobuf_message(uid, region):
    try:
        return f"{uid}:{region}".encode()
    except Exception as e:
        app.logger.error(f"Protobuf creation error: {e}")
        return None

# 🔑 Tokenlarni yuklash
def load_tokens(region):
    try:
        file_path = f"tokens_{region}.json"
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Token load error: {e}")
        return None

# 🌐 So‘rov yuborish (mock)
async def send_request(encrypted_uid, token, url):
    await asyncio.sleep(0.01)  # simulyatsiya uchun
    # bu yerda requests yoki aiohttp bilan haqiqiy so‘rov yuboriladi
    return {"success": True, "token": token}

# 🔄 Global counter
request_counter = 0

# ⚙️ Asosiy parallel so‘rov funksiyasi
async def send_multiple_requests(uid, region, url):
    global request_counter
    request_counter += 1  # har /aruzlike chaqiruvda bittaga oshadi

    try:
        protobuf_message = create_protobuf_message(uid, region)
        if protobuf_message is None:
            return {"success": False, "error": "Failed to create protobuf message"}

        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            return {"success": False, "error": "Encryption failed"}

        tokens = load_tokens(region)
        if tokens is None or len(tokens) == 0:
            return {"success": False, "error": "Failed to load tokens for region"}

        # --- 🔢 Token blokini aniqlaymiz ---
        block_size = 100  # har blokda 100 token
        block_index = (request_counter - 1) // 28  # har 28 chaqiruvdan keyin keyingi blok
        start = block_index * block_size
        end = start + block_size

        # Agar tokenlar soni yetmasa, boshidan qaytadi
        if start >= len(tokens):
            start = 0
            end = block_size if len(tokens) >= block_size else len(tokens)

        selected_tokens = tokens[start:end]

        # --- 🚀 Parallel yuborish ---
        tasks = []
        for token_data in selected_tokens:
            token = token_data["token"]
            tasks.append(send_request(encrypted_uid, token, url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- 📊 Natijalar ---
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        failure_count = len(results) - success_count

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "block_index": block_index,
            "tokens_used": f"{start}-{end - 1}",
            "call_number": request_counter
        }

    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests: {e}")
        return {"success": False, "error": "Internal server error"}

# 🌐 Flask route
@app.route("/aruzlike", methods=["POST"])
def aruzlike():
    try:
        data = request.get_json()
        uid = data.get("uid")
        region = data.get("region", "uz")
        url = data.get("url")

        if not uid or not url:
            return jsonify({"success": False, "error": "Missing UID or URL"}), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_multiple_requests(uid, region, url))
        return jsonify(result)

    except Exception as e:
        app.logger.error(f"/aruzlike error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# 🧭 Test uchun oddiy status endpoint
@app.route("/status")
def status():
    global request_counter
    return jsonify({
        "requests_made": request_counter,
        "message": "Server is running smoothly 🚀"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
