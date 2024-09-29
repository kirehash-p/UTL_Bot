class SQLTemplate():
    """各SQLモジュールで実行するクエリの生成を行うクラス"""
    def __init__(self, dialect):
        self.dialect = dialect

    def create_table_query(self, table_name, columns):
        columns_str = ", ".join([f"{' '.join(self.dialect.get(col, col))}" for col in columns])
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"

    def insert_query(self, table_name, columns):
        columns_str = ", ".join(columns)
        values_str = ", ".join([self.dialect['placeholder'] for _ in columns])
        return f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"

    def update_query(self, table_name, columns, where):
        columns_str = ", ".join([f"{col} = {self.dialect['placeholder']}" for col in columns])
        where_str = " AND ".join([f"{col} = {self.dialect['placeholder']}" for col in where])
        return f"UPDATE {table_name} SET {columns_str} WHERE {where_str}"