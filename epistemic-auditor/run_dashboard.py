# run_dashboard.py

import webbrowser
from observability.dashboard import generate_dashboard

if __name__ == "__main__":
    path = generate_dashboard()
    webbrowser.open(f"file://{__file__.replace('run_dashboard.py', '')}{path}")
    print(f"Dashboard opened in browser.")