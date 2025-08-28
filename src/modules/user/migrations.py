"""Database migrations for User module.

Creates the essential user table with proper indexing and constraints.
"""

import asyncio
import logging
from typing import Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None


logger = logging.getLogger(__name__)


USER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    language_code VARCHAR(10) DEFAULT 'es',
    is_vip BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB DEFAULT '{}',
    telegram_metadata JSONB DEFAULT '{}'
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_users_language ON users(language_code);",
    "CREATE INDEX IF NOT EXISTS idx_users_vip ON users(is_vip) WHERE is_vip = TRUE;",
    "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);",
    "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);"
]


async def create_user_table(connection_pool: Optional[any] = None, database_url: Optional[str] = None) -> bool:
    """
    Create user table with indexes.
    
    Args:
        connection_pool: Existing asyncpg connection pool
        database_url: Database URL if pool not provided
        
    Returns:
        True if successful, False otherwise
    """
    if asyncpg is None:
        logger.error("asyncpg is required but not installed")
        return False
    
    pool = connection_pool
    created_pool = False
    
    try:
        # Create pool if not provided
        if not pool and database_url:
            pool = await asyncpg.create_pool(database_url)
            created_pool = True
        
        if not pool:
            logger.error("No connection pool or database URL provided")
            return False
        
        async with pool.acquire() as conn:
            # Create table
            logger.info("Creating users table...")
            await conn.execute(USER_TABLE_SQL)
            logger.info("Users table created successfully")
            
            # Create indexes
            logger.info("Creating indexes...")
            for index_sql in CREATE_INDEXES_SQL:
                try:
                    await conn.execute(index_sql)
                except Exception as e:
                    logger.warning(f"Index creation failed (might already exist): {e}")
            
            logger.info("User table migration completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    
    finally:
        if created_pool and pool:
            await pool.close()


async def verify_table_structure(connection_pool: Optional[any] = None, database_url: Optional[str] = None) -> bool:
    """Verify that the user table exists and has the correct structure."""
    if asyncpg is None:
        logger.error("asyncpg is required but not installed")
        return False
    
    pool = connection_pool
    created_pool = False
    
    try:
        if not pool and database_url:
            pool = await asyncpg.create_pool(database_url)
            created_pool = True
        
        if not pool:
            logger.error("No connection pool or database URL provided")
            return False
        
        async with pool.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """)
            
            if not table_exists:
                logger.error("Users table does not exist")
                return False
            
            # Check essential columns
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY column_name;
            """)
            
            required_columns = {
                'user_id', 'username', 'first_name', 'last_name',
                'language_code', 'is_vip', 'created_at', 'last_active',
                'preferences', 'telegram_metadata'
            }
            
            existing_columns = {row['column_name'] for row in columns}
            missing_columns = required_columns - existing_columns
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            logger.info("Table structure verification passed")
            return True
            
    except Exception as e:
        logger.error(f"Table verification failed: {e}")
        return False
    
    finally:
        if created_pool and pool:
            await pool.close()


async def drop_user_table(connection_pool: Optional[any] = None, database_url: Optional[str] = None) -> bool:
    """Drop user table (for testing/cleanup)."""
    if asyncpg is None:
        logger.error("asyncpg is required but not installed")
        return False
    
    pool = connection_pool
    created_pool = False
    
    try:
        if not pool and database_url:
            pool = await asyncpg.create_pool(database_url)
            created_pool = True
        
        if not pool:
            logger.error("No connection pool or database URL provided")
            return False
        
        async with pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS users CASCADE;")
            logger.info("Users table dropped successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to drop table: {e}")
        return False
    
    finally:
        if created_pool and pool:
            await pool.close()


# Command line interface for migrations
if __name__ == "__main__":
    import os
    import sys
    
    async def main():
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("ERROR: DATABASE_URL environment variable not set")
            sys.exit(1)
        
        command = sys.argv[1] if len(sys.argv) > 1 else "migrate"
        
        if command == "migrate":
            success = await create_user_table(database_url=database_url)
            if success:
                print("Migration completed successfully")
            else:
                print("Migration failed")
                sys.exit(1)
                
        elif command == "verify":
            success = await verify_table_structure(database_url=database_url)
            if success:
                print("Table structure verified")
            else:
                print("Table structure verification failed")
                sys.exit(1)
                
        elif command == "drop":
            success = await drop_user_table(database_url=database_url)
            if success:
                print("Table dropped successfully")
            else:
                print("Failed to drop table")
                sys.exit(1)
        else:
            print("Usage: python migrations.py [migrate|verify|drop]")
            sys.exit(1)
    
    asyncio.run(main())