import os
import json
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
from services.price_sync import sync_gear_prices_batch, fetch_price_for_gear
from acoustics import classify_sound_signature
import os
load_dotenv()


# Set instance_path to /tmp so Flask-SQLAlchemy can create its folder without failing
app = Flask(__name__, instance_path='/tmp')

# Ensure your database URI is set (e.g., Neon PostgreSQL)
# Fix 'postgres://' URI compatibility if pulling from environment variables
db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:////tmp/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy AFTER app with instance_path='/tmp' is created
db = SQLAlchemy(app)

# ----------------------------------------------------
# ROUTES
# ----------------------------------------------------
@app.route('/')
def index():
    search_query = request.args.get('q', '').strip()

    if search_query:
        pattern = f"%{search_query}%"
        sql = text("""
            SELECT gear_id, name, brand, category, price, image_url, description 
            FROM gear 
            WHERE name ILIKE :pattern OR brand ILIKE :pattern OR category ILIKE :pattern
        """)
        rows = db.session.execute(sql, {"pattern": pattern}).mappings().all()
    else:
        sql = text("SELECT gear_id, name, brand, category, price, image_url, description FROM gear")
        rows = db.session.execute(sql).mappings().all()

    gear_items = [{
        "GearID": r["gear_id"],
        "Name": r["name"],
        "Brand": r["brand"] if r["brand"] else "Unknown",
        "Category": r["category"] if r["category"] else "Audio",
        "Price": float(r["price"]) if r["price"] is not None else 0.0,
        "ImageURL": r["image_url"] if r["image_url"] else "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
        "Description": r["description"] if r["description"] else "High-fidelity audio benchmark measurement."
    } for r in rows]

    return render_template("index.html", gear_items=gear_items, search_query=search_query)


@app.route("/gear/<int:gear_id>")
def gear_detail(gear_id):
    sql_gear = text("""
        SELECT gear_id, name, brand, category, price, price_last_updated, image_url, description 
        FROM gear WHERE gear_id = :gear_id
    """)
    gear_row = db.session.execute(sql_gear, {"gear_id": gear_id}).mappings().first()

    if not gear_row:
        return "Audio equipment item not found.", 404

    gear = {
        "GearID": gear_row["gear_id"],
        "Name": gear_row["name"],
        "Brand": gear_row["brand"],
        "Category": gear_row["category"],
        "Price": float(gear_row["price"]) if gear_row["price"] is not None else 0.0,
        "PriceLastUpdated": gear_row["price_last_updated"],
        "ImageURL": gear_row["image_url"],
        "Description": gear_row["description"],
    }

    # Lazy On-Demand Price Refresh (30-Day Threshold)
    thirty_days_ago = datetime.now() - timedelta(days=30)

    if not gear["PriceLastUpdated"] or gear["PriceLastUpdated"] < thirty_days_ago:
        fresh_price = fetch_price_for_gear(gear["Brand"], gear["Name"])
        now = datetime.now()

        if fresh_price:
            update_sql = text("UPDATE gear SET price = :price, price_last_updated = :now WHERE gear_id = :gear_id")
            db.session.execute(update_sql, {"price": fresh_price, "now": now, "gear_id": gear_id})
            db.session.commit()
            gear["Price"] = fresh_price
            gear["PriceLastUpdated"] = now
        else:
            update_sql = text("UPDATE gear SET price_last_updated = :now WHERE gear_id = :gear_id")
            db.session.execute(update_sql, {"now": now, "gear_id": gear_id})
            db.session.commit()

    # Fetch EAV Specs
    sql_specs = text("SELECT spec_name, spec_value FROM specs_eav WHERE gear_id = :gear_id")
    spec_rows = db.session.execute(sql_specs, {"gear_id": gear_id}).mappings().all()
    specs = {row["spec_name"]: row["spec_value"] for row in spec_rows}

    # Fetch Frequency Response Data
    sql_freq = text("""
        SELECT frequency_hz, amplitude_db 
        FROM frequency_data 
        WHERE gear_id = :gear_id 
        ORDER BY frequency_hz ASC
    """)
    freq_rows = db.session.execute(sql_freq, {"gear_id": gear_id}).mappings().all()
    freq_data = {
        "hz": [float(r["frequency_hz"]) for r in freq_rows],
        "db": [float(r["amplitude_db"]) for r in freq_rows],
    }

    # Calculate Algorithmic Sound Signature
    raw_points = [{"x": h, "y": d} for h, d in zip(freq_data["hz"], freq_data["db"])]
    signature = classify_sound_signature(raw_points) if raw_points else None

    # AutoEq PNG URL Construction
    rig = specs.get("Measurement Rig", "oratory1990").lower().strip()
    cat_clean = str(gear["Category"]).lower().strip()
    form_factor = "in-ear" if cat_clean in ["iem", "in-ear"] else "over-ear"

    encoded_rig = urllib.parse.quote(rig)
    encoded_name = urllib.parse.quote(gear["Name"].strip())
    autoeq_png_url = f"https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/results/{encoded_rig}/{form_factor}/{encoded_name}/{encoded_name}.png"

    return render_template(
        "gear_detail.html",
        gear=gear,
        specs=specs,
        freq_data_json=json.dumps(freq_data),
        signature=signature,
        autoeq_png_url=autoeq_png_url,
    )


@app.route("/compare")
def compare():
    raw_ids = request.args.getlist("ids")
    gear_ids = []
    for item in raw_ids:
        for val in item.split(","):
            val = val.strip()
            if val.isdigit():
                gear_ids.append(int(val))

    gear_ids = list(dict.fromkeys(gear_ids))

    # 1. Fetch all products to populate search dropdown
    sql_all = text("SELECT gear_id, brand, name FROM gear ORDER BY brand ASC, name ASC")
    all_gear_rows = db.session.execute(sql_all).mappings().all()
    all_gear = [{"GearID": r["gear_id"], "Brand": r["brand"], "Name": r["name"]} for r in all_gear_rows]

    if not gear_ids:
        return render_template("compare.html", items=[], chart_data_json=json.dumps([]), all_gear=all_gear)

    # 2. Fetch selected items using PostgreSQL ANY array binding
    sql_selected = text("""
        SELECT gear_id, name, brand, category, price, image_url 
        FROM gear 
        WHERE gear_id = ANY(:gear_ids)
    """)
    gear_rows = db.session.execute(sql_selected, {"gear_ids": gear_ids}).mappings().all()

    gear_map = {}
    for r in gear_rows:
        g_id = r["gear_id"]
        gear_map[g_id] = {
            "GearID": g_id,
            "Name": r["name"],
            "Brand": r["brand"],
            "Category": r["category"],
            "Price": float(r["price"]) if r["price"] is not None else None,
            "ImageURL": r["image_url"],
        }

    items = [gear_map[gid] for gid in gear_ids if gid in gear_map]

    palette = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2"]
    chart_datasets = []

    for idx, item in enumerate(items):
        gid = item["GearID"]

        # Fetch EAV Specs
        sql_specs = text("SELECT spec_name, spec_value FROM specs_eav WHERE gear_id = :gid")
        spec_rows = db.session.execute(sql_specs, {"gid": gid}).mappings().all()
        specs = {row["spec_name"]: row["spec_value"] for row in spec_rows}

        rig = specs.get("Measurement Rig", "oratory1990").lower().strip()
        cat_clean = str(item["Category"]).lower().strip()
        form_factor = "in-ear" if cat_clean in ["iem", "in-ear"] else "over-ear"

        encoded_rig = urllib.parse.quote(rig)
        encoded_name = urllib.parse.quote(item["Name"].strip())
        item["AutoEqURL"] = f"https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/results/{encoded_rig}/{form_factor}/{encoded_name}/{encoded_name}.png"

        # Fetch Frequency Response Data
        sql_freq = text("""
            SELECT frequency_hz, amplitude_db 
            FROM frequency_data 
            WHERE gear_id = :gid 
            ORDER BY frequency_hz ASC
        """)
        freq_rows = db.session.execute(sql_freq, {"gid": gid}).mappings().all()
        points = [{"x": float(r["frequency_hz"]), "y": float(r["amplitude_db"])} for r in freq_rows]

        # Calculate Algorithmic Sound Signature
        item["Signature"] = classify_sound_signature(points) if points else None

        color = palette[idx % len(palette)]
        item["Color"] = color

        chart_datasets.append(
            {
                "label": f"{item['Brand']} {item['Name']}",
                "data": points,
                "borderColor": color,
                "backgroundColor": color,
                "borderWidth": 2.5,
                "pointRadius": 0,
                "pointHoverRadius": 5,
                "fill": False,
                "tension": 0.1,
            }
        )

    return render_template(
        "compare.html",
        items=items,
        chart_data_json=json.dumps(chart_datasets),
        all_gear=all_gear,
    )


@app.cli.command("sync-prices")
def sync_prices_command():
    """CLI command to update gear prices in small batches."""
    sync_gear_prices_batch(db, batch_size=10)


if __name__ == "__main__":
    app.run(debug=True, port=5000)