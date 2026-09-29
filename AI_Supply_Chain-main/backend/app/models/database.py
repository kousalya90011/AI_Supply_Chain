from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

import app.models.entities  # noqa: E402,F401


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def initialize_database():
    Base.metadata.create_all(bind=engine)

    if settings.DATABASE_URL.startswith("sqlite"):
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        if "users" in table_names:
            user_columns = {col["name"] for col in inspector.get_columns("users")}
            with engine.begin() as connection:
                if "name" not in user_columns:
                    connection.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(120)"))
                if "status" not in user_columns:
                    connection.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(30) DEFAULT 'ACTIVE' NOT NULL"))

        if "suppliers" not in table_names:
            Base.metadata.tables["suppliers"].create(bind=engine)
        if "products" not in table_names:
            Base.metadata.tables["products"].create(bind=engine)
        else:
            prod_columns = {col["name"] for col in inspector.get_columns("products")}
            with engine.begin() as connection:
                if "supplier_id" not in prod_columns:
                    connection.execute(text("ALTER TABLE products ADD COLUMN supplier_id VARCHAR(100)"))
                if "approval_status" not in prod_columns:
                    connection.execute(text("ALTER TABLE products ADD COLUMN approval_status VARCHAR(30) DEFAULT 'APPROVED'"))
                    connection.execute(text("UPDATE products SET approval_status = 'APPROVED' WHERE approval_status IS NULL"))
                if "approved_by" not in prod_columns:
                    connection.execute(text("ALTER TABLE products ADD COLUMN approved_by VARCHAR(120)"))
                if "approved_at" not in prod_columns:
                    connection.execute(text("ALTER TABLE products ADD COLUMN approved_at DATETIME"))
                if "rejection_reason" not in prod_columns:
                    connection.execute(text("ALTER TABLE products ADD COLUMN rejection_reason TEXT"))
        if "orders" not in table_names:
            Base.metadata.tables["orders"].create(bind=engine)
        if "inventory" not in table_names:
            Base.metadata.tables["inventory"].create(bind=engine)
        if "supplier_offers" not in table_names:
            Base.metadata.tables["supplier_offers"].create(bind=engine)

        if "evaluation_results" in table_names:
            eval_columns = {col["name"] for col in inspector.get_columns("evaluation_results")}
            with engine.begin() as connection:
                new_eval_cols = [
                    ("expected_behavior", "TEXT"),
                    ("actual_behavior", "TEXT"),
                    ("planner_correct", "BOOLEAN"),
                    ("retrieval_correct", "BOOLEAN"),
                    ("grounding_score", "FLOAT"),
                    ("relevance_score", "FLOAT"),
                    ("rbac_correct", "BOOLEAN"),
                    ("fallback_correct", "BOOLEAN"),
                    ("audit_complete", "BOOLEAN"),
                    ("retrieval_mode", "VARCHAR(50)"),
                    ("evidence_count", "INTEGER DEFAULT 0"),
                    ("llm_used", "BOOLEAN DEFAULT 0"),
                    ("fallback_used", "BOOLEAN DEFAULT 0"),
                    ("success", "BOOLEAN DEFAULT 1"),
                    ("scope_role", "VARCHAR(50)"),
                    ("scope_supplier_id", "VARCHAR(50)"),
                    ("details", "TEXT"),
                ]
                for col_name, col_type in new_eval_cols:
                    if col_name not in eval_columns:
                        try:
                            connection.execute(text(f"ALTER TABLE evaluation_results ADD COLUMN {col_name} {col_type}"))
                        except Exception:
                            pass
    