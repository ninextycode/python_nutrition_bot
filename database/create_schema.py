from database import food_database_model, config
from sqlalchemy import create_engine


if __name__ == "__main__":
    target_metadata = food_database_model.Base.metadata
    engine = create_engine(config.sqlalchemy_url, echo=True)

    food_database_model.Base.metadata.create_all(engine)
