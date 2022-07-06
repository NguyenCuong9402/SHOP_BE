from app.app import create_app

from app.settings import DevConfig, PrdConfig, os

CONFIG = PrdConfig if os.environ.get('ENV') == 'prd' else DevConfig

app = create_app(config_object=CONFIG)

if __name__ == '__main__':
    """
    Main Application
    python server.py
    """
    app.run(host='0.0.0.0', port=5012)
