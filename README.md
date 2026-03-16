# 🌱 GreenCompliance AI

GreenCompliance AI is an AI-assisted environmental compliance analysis tool that helps businesses quickly identify potential environmental risks based on their operations.

The system analyzes a business description, detects possible environmental compliance issues, and provides risk levels, recommendations, and relevant regulatory areas.

---

# 🚀 Features

* 🔎 **Environmental Risk Detection**
  Automatically identifies compliance risks based on business activities.

* 📊 **Compliance Score System**
  Generates a score (0–100) indicating environmental compliance level.

* ⚠️ **Issue Identification**
  Detects environmental violations such as waste disposal, emissions, or hazardous material handling.

* ✅ **Recommendations**
  Provides actionable suggestions to improve environmental compliance.

* 📜 **Regulation Mapping**
  Links detected issues with relevant environmental regulations.

* 📥 **Downloadable Reports**
  Generates a compliance report after analysis.

* 🧪 **Automated Testing**
  Includes a regression test suite using PyTest.

---

# 🏗 Project Architecture

GreenCompliance AI uses a simple full-stack architecture:

Frontend:

* HTML
* CSS
* JavaScript

Backend:

* Python Flask API

Database:

* SQLite (stores analysis history)

Data Source:

* JSON regulation database

Testing:

* PyTest

---

# 📂 Project Structure

```
green-compliance-ai
│
├── app.py                  # Flask backend server
├── requirements.txt        # Python dependencies
├── test_app.py             # Automated test suite
├── README.md               # Project documentation
│
├── data
│   └── regulations.json    # Environmental regulations dataset
│
├── static
│   ├── script.js           # Frontend logic
│   └── style.css           # UI styling
│
├── templates
│   └── index.html          # Main web interface
│
└── greencompliance.db      # SQLite database
```

---

# ⚙️ Installation

Clone the repository:

```
git clone https://github.com/didagesierich/green-compliance-ai.git
```

Move into the project directory:

```
cd green-compliance-ai
```

Install dependencies:

```
pip install -r requirements.txt
```

Run the application:

```
python app.py
```

Open the browser:

```
http://localhost:5000
```

---

# 🧠 How It Works

1. User selects an industry and describes their business operations.
2. The backend analyzes the description using a rule-based regulation engine.
3. Keywords are matched with environmental regulations stored in `regulations.json`.
4. The system calculates a compliance score and determines a risk level.
5. Results including issues, recommendations, and regulatory areas are returned to the frontend dashboard.

---

# 📊 Risk Level System

| Compliance Score | Risk Level  |
| ---------------- | ----------- |
| 70 – 100         | Low Risk    |
| 40 – 69          | Medium Risk |
| 0 – 39           | High Risk   |

---

# 🧪 Running Tests

Run the regression test suite:

```
python -m pytest test_app.py -v
```

This validates:

* API endpoints
* rule engine logic
* regulation dataset integrity
* report generation

---

# 🌍 Example Industries Supported

* Restaurant
* Construction
* Manufacturing
* Agriculture
* Healthcare
* Retail
* Technology
* Transportation

---

# 🔮 Future Improvements

* AI-based compliance insights using LLMs
* Real environmental law database integration
* ESG scoring dashboard
* Multi-language support
* Cloud deployment

---

# 🤝 Contributors

Project developed as part of an AI environmental compliance system.

---

# 📜 License

This project is for educational and research purposes.

