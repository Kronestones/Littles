from flask import Flask
from littles_web import create_app

app = Flask(__name__)
blueprint = create_app()
app.register_blueprint(blueprint)

if __name__ == "__main__":
    app.run()
