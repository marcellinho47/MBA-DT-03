"""Entry point da API da Loja. É um composition root fino: toda a montagem está em src/app.py.

Uso: `python app.py` ou `flask --app app run`.
"""
import logging

from src.app import create_app

app = create_app()

if __name__ == "__main__":
    host, port, debug = app.config["HOST"], app.config["PORT"], app.config["DEBUG"]
    logging.getLogger(__name__).info("Servidor iniciado em http://%s:%s (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
