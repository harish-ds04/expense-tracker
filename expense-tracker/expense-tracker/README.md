# Student Expense Tracker

A simple Flask web app for tracking student expenses. Built as a learning project.

## Features
- Add, edit, and delete expenses (amount, category, description, date)
- Default categories (Food, Travel, Shopping, Bills, Entertainment, Other) + custom categories
- Duplicate expense detection
- Server-side + client-side validation
- Category breakdown with progress bars
- Sort expenses by date, amount, or category
- Responsive dark UI (sidebar on desktop, bottom nav on mobile)
- In-memory storage (data resets when the server restarts) — no database needed for this prototype

## Tech stack
Python, Flask, HTML, CSS, vanilla JavaScript. No frontend framework, no database.

## Running locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Project structure

```
expense-tracker/
├── app.py            # Flask routes
├── data.py           # In-memory data + business logic
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── add_expense.html
└── static/
    ├── style.css
    └── script.js
```

## Notes
This is a prototype/MVP. Planned next steps: persistent storage (SQLite), monthly budgets,
theme toggle, and a settings page.
