from sqlalchemy import create_engine, MetaData

engine = create_engine("sqlite:///nugamoto.sqlite", future=True)
meta = MetaData()
meta.reflect(bind=engine)


TABLE = "food_item_alias"

if __name__ == "__main__":
    print(meta.tables[TABLE].columns.keys())