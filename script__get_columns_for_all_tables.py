from sqlalchemy import create_engine, MetaData

# Verbindung zur SQLite-Datenbank
engine = create_engine("sqlite:///nugamoto.sqlite", future=True)
meta = MetaData()

# Lade Metadaten aller Tabellen
meta.reflect(bind=engine)

if __name__ == "__main__":
    # Iteriere über alle Tabellen und deren Spalten
    for table_name, table in meta.tables.items():
        print(f"Tabelle: {table_name}")
        print("Spalten:", [col.name for col in table.columns])
        print()
