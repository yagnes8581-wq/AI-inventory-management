# AI-inventory-management
An AI-driven Enterprise Inventory Management System featuring time-series demand forecasting, automated procurement, and cryptographically secure role-based access.
# 📦 AI-Driven Enterprise Inventory Management System

**An intelligent, predictive ERP application built to solve supply chain inefficiencies, phantom inventory, and reactive stockouts.**

Developed as part of the Artificial Intelligence and Data Analytics program (Internship 1 - ADA23IN201) at Sri Ramachandra Institute of Higher Education and Research (SRIHER).

---

## 🚀 Project Overview

Traditional inventory systems rely on reactive descriptive analytics—alerting managers *after* a stockout has already occurred. This project bridges the gap between academic data science and practical enterprise software by implementing a **Time-Series Machine Learning model** to predict future demand and automate procurement.

Built entirely in Python, this application features a locally hosted relational database, cryptographically secured user roles, and a strict physical-handshake receiving protocol to maintain data integrity.

## ✨ Key Features

* **🧠 Predictive Demand Forecasting:** Utilizes Pandas-driven Exponential Smoothing (EMA) on 6 months of historical sales data to predict upcoming monthly demand and dynamically adjust Reorder Points.
* **📊 Automated ABC Classification:** Automatically grades the database based on cumulative revenue, locking "Class A" (Top 80% Revenue) items to the top of the UI and triggering critical loss alerts if stock nears zero.
* **🚚 Supply Chain Procurement:** An end-to-end Purchase Order (PO) generator. Orders are tracked via a Kanban-style system (Pending -> Shipped -> Received) requiring manual verification to prevent "Phantom Inventory."
* **🔐 Cryptographic Security & RBAC:** Features a secure login gateway using `hashlib` SHA-256 encryption. Employs Role-Based Access Control (Admin, Experienced, Novice) to securely gate data.
* **📥 CSV Data Migration Engine:** Allows Admins to generate blank data templates and bulk-upload external inventory data directly into the SQLite database for instant onboarding.
* **🖥️ Progressive Disclosure UX:** The user interface actively adapts to the employee's role, providing embedded training guides for Novices while stripping away clutter for Experienced managers.

## 🛠️ Technology Stack

* **Frontend:** Streamlit (Python UI Framework)
* **Backend:** Python 3.x
* **Database:** SQLite3 (Relational Database Management)
* **Data Processing & ML:** Pandas, NumPy
* **Data Visualization:** Plotly Express
* **Security:** Python `hashlib` (SHA-256)
