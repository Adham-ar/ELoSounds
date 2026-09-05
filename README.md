# EloSounds 🎧

## 🌐 Live Application

You can try out the live web app here: **[https://elosounds.vercel.app](https://elosounds.vercel.app)**

> A web application designed for audio enthusiasts to explore, compare, and analyze audio equipment specifications and real-time market pricing.

---

## 📌 Overview

**EloSounds** aggregates detailed specifications for audio gear (In-Ear Monitors, Headphones, and DACs/Amps) and synchronizes market prices automatically via external search APIs. Built with a lightweight Python/Flask backend, EloSounds features server-side rendering with Jinja2, clean ORM abstraction with Flask-SQLAlchemy, and seamless serverless deployment on Vercel backed by PostgreSQL.

---

## ✨ Key Features

* **Real-Time Price Synchronization:** Automated fetching and parsing of live vendor pricing using **SerpApi**.
* **Clean Audio Spec Catalog:** Browse, filter, and compare audio gear based on sound signatures, categories, and brands.
* **Flexible Database Architecture:** Seamlessly toggles between local SQLite for development and hosted PostgreSQL (Supabase/Neon) for production with URI sanitization.
* **Serverless Optimized:** Engineered for zero-downtime, stateless serverless hosting on Vercel with server-side rendered HTML cards via Jinja2.

---

## 🛠 Tech Stack

| Domain | Technology / Tool |
| :--- | :--- |
| **Backend Framework** | Python 3, Flask |
| **Database & ORM** | Flask-SQLAlchemy, SQLAlchemy 1.4+, PostgreSQL, SQLite |
| **Frontend** | HTML5, CSS3, Jinja2 Templating Engine |
| **APIs & Data Sync** | SerpApi (Google Shopping / Search integration) |
| **Hosting & DevOps** | Vercel (WSGI Serverless Functions), Git, GitHub |

---

## 🏗 System Architecture & Data Flow

```
┌─────────────────┐        1. HTTP GET /        ┌──────────────────────────┐
│  Client Browser │ ──────────────────────────> │ Vercel Serverless Function│
└────────┬────────┘                             └────────────┬─────────────┘
         │                                                   │
         │                                          2. Invoke Application
         │                                                   │
         │ 4. Rendered HTML Page                             ▼
         │ <─────────────────────────────────── ┌──────────────────────────┐
         │                                      │   Flask Application      │
         │                                      │        (app.py)          │
         │                                      └────────────┬─────────────┘
         │                                                   │
         │                                          3. SQL Execution &
         │                                             Row Mapping
         │                                                   │
         ▼                                                   ▼
┌─────────────────┐                             ┌──────────────────────────┐
│ Jinja2 Templates│                             │ PostgreSQL / SQLite DB   │
│  (index.html)   │                             │      (gear table)        │
└─────────────────┘                             └──────────────────────────┘
```



## 👤 Author

* **Adham Amr**
  * Portfolio: [https://github.com/AdhamAmr](https://github.com/)
  * LinkedIn: [[https://linkedin.com/in/adhamamr](https://www.linkedin.com/in/adham-amr-18a2562a3/)](https://linkedin.com/)
