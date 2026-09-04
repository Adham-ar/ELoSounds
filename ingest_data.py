from urllib.parse import quote
import pyodbc
import requests

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-DB6NAB1\\MSSQLSERVER22;"
    "DATABASE=AudiophileDB;"
    "Trusted_Connection=yes;"
)


def fetch_github_catalog(limit=200):
    """Scans AutoEq's GitHub repository tree and builds a dynamic catalog."""
    print(
        f"[1/3] Crawling GitHub repository tree for up to {limit} models..."
    )
    tree_url = "https://api.github.com/repos/jaakkopasanen/AutoEq/git/trees/master?recursive=1"
    response = requests.get(tree_url, timeout=15)

    if response.status_code != 200:
        raise Exception("Failed to fetch repository tree from GitHub API.")

    tree = response.json().get("tree", [])
    catalog = []

    # Target reliable measurement sources (oratory1990, crinacle)
    allowed_sources = ("oratory1990", "crinacle")

    for item in tree:
        path = item["path"]
        if path.startswith("measurements/") and path.endswith(".csv"):
            parts = path.split("/")
            # Path format: measurements/<source>/data/<ear-type>/<model>.csv
            if len(parts) == 5 and parts[1] in allowed_sources:
                source, ear_type, file_name = parts[1], parts[3], parts[4]
                model_name = file_name.replace(".csv", "")
                brand = model_name.split()[0]  # Heuristic brand extraction

                category = "Headphone" if ear_type == "over-ear" else "IEM"

                catalog.append(
                    {
                        "Name": model_name,
                        "Brand": brand,
                        "Category": category,
                        "Price": 199.99,  # Default catalog price baseline
                        "ImageURL": "https://images.unsplash.com/photo-1546435770-a3e426bf472b",
                        "Description": f"Automated response measurement sourced from {source}.",
                        "RelPath": path.replace("measurements/", ""),
                        "Specs": {
                            "Category": category,
                            "Measurement Rig": source.capitalize(),
                            "Target Curve": "Harman Standard",
                        },
                    }
                )

                if len(catalog) >= limit:
                    break

    print(f"  └─ Discovered {len(catalog)} products dynamically!\n")
    return catalog


def run_etl():
    catalog = fetch_github_catalog(limit=200)

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.fast_executemany = True

    base_raw_url = (
        "https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/measurements/"
    )

    print("[2/3] Ingesting Dynamic Gear & Measurement Curves...\n")

    for item in catalog:
        # A. Check if Gear already exists; if so, skip re-insertion
        cursor.execute(
            "SELECT GearID FROM Gear WHERE Name = ?", (item["Name"],)
        )
        existing_gear = cursor.fetchone()

        if existing_gear:
            gear_id = existing_gear[0]
            print(
                f"[*] Skipping {item['Name']} — Already in DB (GearID: {gear_id})"
            )
            continue  # Move to next product without duplicating specs or FR points

        # Insert new product if it doesn't exist
        insert_gear_sql = """
                    INSERT INTO Gear (Name, Brand, Category, Price, ImageURL, Description)
                    OUTPUT INSERTED.GearID
                    VALUES (?, ?, ?, ?, ?, ?);
                """
        cursor.execute(
            insert_gear_sql,
            (
                item["Name"],
                item["Brand"],
                item["Category"],
                item["Price"],
                item["ImageURL"],
                item["Description"],
            ),
        )
        gear_id = cursor.fetchone()[0]
        print(f"[+] Inserted Product: {item['Name']} (GearID: {gear_id})")

        # B. Insert Specs
        specs_data = [
            (gear_id, k, v) for k, v in item["Specs"].items()
        ]
        cursor.executemany(
            "INSERT INTO Specs_EAV (GearID, SpecName, SpecValue) VALUES (?, ?, ?);",
            specs_data,
        )

        # C. Fetch Raw Measurement Points
        target_url = f"{base_raw_url}{quote(item['RelPath'])}"
        freq_points = []

        try:
            resp = requests.get(target_url, timeout=5)
            if resp.status_code == 200:
                for line in resp.text.strip().splitlines()[1:]:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        try:
                            hz = float(parts[0].strip())
                            db_raw = float(parts[1].strip())
                            freq_points.append((gear_id, hz, db_raw + 80.0))
                        except ValueError:
                            continue
        except Exception:
            pass

        if freq_points:
            cursor.executemany(
                "INSERT INTO FrequencyData (GearID, FrequencyHz, AmplitudeDB) VALUES (?, ?, ?);",
                freq_points,
            )
            print(
                f"[+] Stored Product ID {gear_id}: {item['Name']} ({len(freq_points)} FR Points)"
            )

    conn.commit()
    cursor.close()
    conn.close()
    print("\n[3/3] Dynamic ETL Ingestion Completed Successfully!")


if __name__ == "__main__":
    run_etl()