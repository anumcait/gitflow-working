from flask import Flask, jsonify, request
from app.service import add_numbers

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"message": "GitLab POC Running123"})


@app.route("/add", methods=["POST"])
def add():
    data = request.json
    a = data.get("a")
    b = data.get("b")
    return jsonify({"result": add_numbers(a, b)})


@app.route("/subtract", methods=["POST"])
def subtract():
    data = request.json
    a = data.get("a")
    b = data.get("b")
    return {"result": a - b}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
