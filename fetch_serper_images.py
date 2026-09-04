import json
import pyodbc
import requests

SERPER_API_KEY = "0d7a007074934f974bd910a9022796eff14335e2"

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-DB6NAB1\\MSSQLSERVER22;"
    "DATABASE=AudiophileDB;"
    "Trusted_Connection=yes;"
)


def fetch_google_image(query: str) -> str:
    """Queries Serper.dev Google Images API for clean product photos."""
    url = "https://google.serper.dev/images"
    payload = json.dumps({"q": f"{query} audiophile product photo"})
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url, headers=headers, data=payload, timeout=10
        )
        data = response.json()
        if "images" in data and len(data["images"]) > 0:
            return data["images"][0]["imageUrl"]
    except Exception as e:
        print(f"[!] Error for '{query}': {e}")
    return None


def update_catalog_images():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("SELECT GearID, Name FROM Gear")
    records = cursor.fetchall()

    print(
        f"[*] Fetching Google product images for {len(records)} items via Serper API..."
    )

    for row in records:
        gear_id = row.GearID
        name = row.Name

        image_url = fetch_google_image(name)
        if image_url:
            cursor.execute(
                "UPDATE Gear SET ImageURL = ? WHERE GearID = ?",
                (image_url, gear_id),
            )
            print(f"[+] Updated {name}\n    └─ {image_url}")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n[✔] All product images updated successfully.")


if __name__ == "__main__":
    update_catalog_images()