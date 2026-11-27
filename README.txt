FRESHMART - ONLINE GROCERY SHOPPING MINI PROJECT

Requirements:
- Python 3.10 or newer
- Internet connection for optional Google Fonts only

Run on Windows:
1. Extract FreshMart.zip
2. Open terminal / Command Prompt inside FreshMart folder
3. Run: py -m venv .venv
4. Run: .venv\Scripts\activate
5. Run: pip install -r requirements.txt
6. Run: python app.py
7. Open browser at http://127.0.0.1:5000

On macOS/Linux use:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

Demo admin login:
Email: admin@freshmart.com
Password: admin123

Customer: register your own account.
Database freshmart.db is created automatically on first run.

Features:
Registration/login, hashed passwords, product catalog, search/category filter,
session cart, quantity update/remove, checkout demo, order history, admin product
add/delete, admin order listing, stock decrement.

Note: This is a college demonstration project. Checkout is not connected to a
real payment gateway. For deployment, replace the demo secret key, add CSRF
protection, improve validation and use a production server.
