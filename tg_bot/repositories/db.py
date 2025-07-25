import aiosqlite

from .sqlite import SQLiteUsersRepo, SQLiteCharactersRepo, SQLiteInventoryRepo


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self.users: SQLiteUsersRepo | None = None
        self.characters: SQLiteCharactersRepo | None = None
        self.inventory: SQLiteInventoryRepo | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        self.users = SQLiteUsersRepo(self.conn)
        self.characters = SQLiteCharactersRepo(self.conn)
        self.inventory = SQLiteInventoryRepo(self.conn)

    async def _create_tables(self):
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                chat_id INTEGER,
                username TEXT,
                gold INTEGER DEFAULT 100,
                PRIMARY KEY(user_id, chat_id)
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                name TEXT,
                class TEXT,
                level INTEGER,
                exp INTEGER,
                hp INTEGER,
                mana INTEGER,
                FOREIGN KEY(user_id, chat_id) REFERENCES users(user_id, chat_id)
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                data TEXT,
                FOREIGN KEY(user_id, chat_id) REFERENCES users(user_id, chat_id)
            )
            """
        )
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None
