import os
import time
import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def fetch_price_for_gear(brand, name):
    """Query Google Shopping via SerpApi for a specific product."""
    if not SERPAPI_KEY:
        print("Error: SERPAPI_KEY not found in environment variables.")
        return None

    search_query = f"{brand} {name}"

    params = {
        "engine": "google_shopping",
        "q": search_query,
        "api_key": SERPAPI_KEY,
        "gl": "us",
        "hl": "en"
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        shopping_results = results.get("shopping_results", [])

        if shopping_results:
            first_result = shopping_results[0]
            price = first_result.get("extracted_price")
            return float(price) if price else None
    except Exception as e:
        print(f"SerpApi Error for {search_query}: {e}")

    return None


def sync_gear_prices_batch(get_db_connection, batch_size=10):
    """
    Fetch and update prices for a limited batch of gear missing prices
    or needing refresh, avoiding SerpApi quota exhaustion.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query items with no updated price first (or older than 30 days)
    # Using SQL slicing / fetchmany to ensure cross-database compatibility
    cursor.execute(
        """
        SELECT GearID, Brand, Name 
        FROM Gear 
        WHERE PriceLastUpdated IS NULL 
        ORDER BY GearID ASC
        """
    )
    gear_items = cursor.fetchmany(batch_size)

    if not gear_items:
        print("All gear items are currently up to date.")
        cursor.close()
        conn.close()
        return

    print(f"Starting batch price sync for {len(gear_items)} items...")

    for item in gear_items:
        # Compatibility handling for tuple or pyodbc Row
        gear_id = getattr(item, 'GearID', item[0])
        brand = getattr(item, 'Brand', item[1])
        name = getattr(item, 'Name', item[2])

        print(f"Fetching [{gear_id}] {brand} {name}...")
        price = fetch_price_for_gear(brand, name)

        now = datetime.datetime.now()
        if price is not None:
            cursor.execute(
                """
                UPDATE Gear 
                SET Price = ?, PriceLastUpdated = ? 
                WHERE GearID = ?
                """,
                (price, now, gear_id)
            )
            print(f"  └─ SUCCESS: Updated {name} -> ${price:.2f}")
        else:
            # Stamp timestamp even if failed so it won't loop on the same broken item
            cursor.execute(
                "UPDATE Gear SET PriceLastUpdated = ? WHERE GearID = ?",
                (now, gear_id)
            )
            print(f"  └─ WARNING: No price found for {name}. Timestamped to skip.")

        # Save progress per item
        conn.commit()
        # Brief pause between HTTP requests
        time.sleep(1)

    cursor.close()
    conn.close()
    print("Batch price sync finished.")