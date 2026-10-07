from app import create_app
from seed import seed_data

app = create_app()

if __name__ == '__main__':
    seed_data()
    app.run(debug=True, port=5000)
