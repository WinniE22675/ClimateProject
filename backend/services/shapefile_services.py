import geopandas as gpd

def detect_region_columns(shapefile_path: str) -> dict:
    """
    Reads the schema of a shapefile to find text columns 
    and suggests the most likely column for region names.
    """
    try:
        # Trick: Read only the first row (rows=1) to save memory and processing time.
        # We only need the column headers and their data types, not the full geometry.
        gdf = gpd.read_file(shapefile_path, rows=1)
        
        # 1. Filter only string/object columns (ignore numbers, dates, and geometry)
        string_cols = [
            col for col in gdf.columns 
            if gdf[col].dtype == 'object' and col.lower() != 'geometry'
        ]
        
        if not string_cols:
            return {"columns": [], "default": None}
            
        # 2. Define keywords commonly used for area names
        keywords = ['name', 'nam', 'prov', 'adm', 'dist', 'changwat', 'th', 'en']
        
        best_match = None
        
        # 3. Search for the best matching column based on keywords
        for col in string_cols:
            col_lower = col.lower()
            if any(kw in col_lower for kw in keywords):
                best_match = col
                break # Stop at the first logical match
                
        # 4. Fallback: If no keyword matches, just pick the first string column
        if not best_match:
            best_match = string_cols[0]
            
        return {
            "columns": string_cols,
            "default": best_match
        }
        
    except Exception as e:
        print(f"Error detecting shapefile columns: {e}")
        return {"columns": [], "default": None}