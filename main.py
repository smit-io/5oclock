import sys
from src.constants import FILES_TO_DOWNLOAD, FORCE_UPDATE
from src.downloader import sync_all_datasets
from src.database import import_data, create_indexes
from src.processor import (
    get_cities_from_best_hour_match,
    process_refined_data, 
    create_timezone_specific_tables,
)
from src.exporter import export_all_timezones_to_json, export_list_to_json

def initialize_pipeline(force: bool = False):
    """
    One function to rule them all: 
    Syncs data, builds the DB, partitions tables, and exports JSONs.
    """
    print("🚀 Starting GeoNames Pipeline Initialization...")

    # 1. Sync Remote Data (Downloads only if newer or forced)
    print("\n[Step 1/5] Syncing remote datasets...")
    sync_all_datasets(FILES_TO_DOWNLOAD, force=force)

    # 2. Build Raw SQLite DB (Imports only if .txt files are newer)
    print("\n[Step 2/5] Importing raw text data into geonames.db...")
    import_data()

    # 3. Build Refined cities.db (Joins and cleans data)
    print("\n[Step 3/5] Generating refined cities.db (Master Tables)...")
    process_refined_data()
    create_indexes()

    # 4. Create Partitioned Timezone Tables
    print("\n[Step 4/5] Creating individual tables for each timezone...")
    create_timezone_specific_tables(force=force)

    # 5. Export JSON Files
    print("\n[Step 5/5] Exporting all timezones to JSON files...")
    # Optional: pass a limit (e.g. 100) if you don't want massive JSON files
    export_all_timezones_to_json(force=force)

    print("\n✅ Initialization Pipeline Complete!")

def main():
    # You can pass 'force' as a command line argument if you want
    force_flag = FORCE_UPDATE
    if "--force" in sys.argv:
        force_flag = True
        
    initialize_pipeline(force=force_flag)
    
    target_hour = 17 
    cities = get_cities_from_best_hour_match(target_hour, city_limit=100)

    if cities:
        export_list_to_json(
            cities, 
            filename=f"best_match_hour_{target_hour}", 
            force=True
        )

if __name__ == "__main__":
    main()