"""
NexCare Full-Stack Application Entry Point
Flask Web Server, Static Asset Serving, API Routing, and Health Checks
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# Add parent directory to sys.path so package imports work cleanly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.api import api
from backend.config import SECRET_KEY, DATA_MODE, BASE_DIR
from backend.database import repo


def find_frontend_dir():
    """Locate frontend directory regardless of execution working directory."""
    candidates = [
        os.path.join(parent_dir, "frontend"),
        os.path.join(current_dir, "..", "frontend"),
        os.path.join(os.getcwd(), "frontend"),
        os.path.join(os.getcwd(), "NexCare", "frontend"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return os.path.join(parent_dir, "frontend")


def create_app():
    frontend_path = find_frontend_dir()
    app = Flask(
        __name__,
        static_folder=frontend_path,
        static_url_path="",
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    CORS(app)

    # Register REST API blueprint
    app.register_blueprint(api)

    # Health Check Endpoint
    @app.get("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "service": "NexCare Healthcare Support API",
            "active_data_mode": repo.mode,
            "mysql_connected": repo._mysql_available,
            "version": "1.0.0",
        })

    # Frontend Page Routes
    @app.get("/")
    def index():
        return send_from_directory(frontend_path, "index.html")

    @app.get("/patient")
    @app.get("/patient.html")
    def patient_page():
        return send_from_directory(frontend_path, "patient.html")

    @app.get("/staff")
    @app.get("/staff.html")
    def staff_page():
        return send_from_directory(frontend_path, "staff.html")

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found"}), 404
        return send_from_directory(frontend_path, "index.html"), 200

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"success": False, "error": "Internal server error occurred"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("=" * 65)
    print("  NexCare — Healthcare Support Web Application")
    print(f"  Active Data Mode: {repo.mode.upper()}")
    print("  Server running at: http://127.0.0.1:5000")
    print("  Patient Portal:    http://127.0.0.1:5000/patient.html")
    print("  Staff Portal:      http://127.0.0.1:5000/staff.html")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)
