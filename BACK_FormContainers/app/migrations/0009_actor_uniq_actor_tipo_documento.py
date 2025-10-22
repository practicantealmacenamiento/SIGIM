# app/migrations/0009_actor_uniq_actor_tipo_documento.py

from django.db import migrations

INDEX_NAME = "app_actor_tipo_documento_uq"

def create_index_for_vendor(apps, schema_editor):
    # Obtén el nombre de tabla histórico del modelo en ESTE punto del plan de migraciones
    Actor = apps.get_model("app", "Actor")
    table = Actor._meta.db_table                 # p.ej. 'app_actor' o un nombre custom
    qtable = schema_editor.quote_name(table)     # p.ej. [app_actor] en MSSQL

    vendor = schema_editor.connection.vendor

    if vendor == "microsoft":
        # Determinar el esquema (default 'dbo' si no está definido)
        schema = "dbo"
        try:
            opts = schema_editor.connection.settings_dict.get("OPTIONS", {}) or {}
            schema = opts.get("schema", schema) or "dbo"
        except Exception:
            pass

        # Nombres totalmente calificados para OBJECT_ID
        fq = f"{schema}.{table}"                 # p.ej. dbo.app_actor
        qindex = schema_editor.quote_name(INDEX_NAME)

        sql = f"""
IF OBJECT_ID(N'{fq}', N'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'{INDEX_NAME}'
      AND object_id = OBJECT_ID(N'{fq}', N'U')
)
BEGIN
    CREATE UNIQUE INDEX {qindex}
    ON {qtable} ([tipo], [documento])
    WHERE [documento] IS NOT NULL;
END
"""
        schema_editor.execute(sql)

    elif vendor == "postgresql":
        # Postgres: índice único parcial
        sql = f"""
CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
ON {table} (tipo, documento)
WHERE documento IS NOT NULL;
"""
        schema_editor.execute(sql)

    elif vendor == "sqlite":
        # SQLite no soporta índices filtrados. No creamos nada aquí.
        pass

    else:
        # Fallback: no hacer nada
        pass


def drop_index_for_vendor(apps, schema_editor):
    Actor = apps.get_model("app", "Actor")
    table = Actor._meta.db_table
    qtable = schema_editor.quote_name(table)
    vendor = schema_editor.connection.vendor

    if vendor == "microsoft":
        schema = "dbo"
        try:
            opts = schema_editor.connection.settings_dict.get("OPTIONS", {}) or {}
            schema = opts.get("schema", schema) or "dbo"
        except Exception:
            pass
        fq = f"{schema}.{table}"
        qindex = schema_editor.quote_name(INDEX_NAME)
        sql = f"""
IF OBJECT_ID(N'{fq}', N'U') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'{INDEX_NAME}'
      AND object_id = OBJECT_ID(N'{fq}', N'U')
)
BEGIN
    DROP INDEX {qindex} ON {qtable};
END
"""
        schema_editor.execute(sql)

    elif vendor == "postgresql":
        schema_editor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")

    elif vendor == "sqlite":
        pass
    else:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0008_remove_answer_answer_has_some_value"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_index_for_vendor, reverse_code=drop_index_for_vendor),
            ],
            state_operations=[],
        ),
    ]
