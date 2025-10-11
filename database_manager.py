import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="contributions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                year INTEGER NOT NULL,
                month TEXT NOT NULL,
                contribution_type TEXT NOT NULL,
                family_member_name TEXT,
                amount REAL NOT NULL,
                screenshot_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    def get_all_contributions(self):
        """Get all contributions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contributions ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_user_contributions(self, user_id):
        """Get contributions for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM contributions WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_monthly_summary(self, year, month):
        """Get monthly summary of contributions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                contribution_type,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM contributions 
            WHERE year = ? AND month = ?
            GROUP BY contribution_type
        ''', (year, month))
        
        results = cursor.fetchall()
        conn.close()
        return results

if __name__ == '__main__':
    # Test the database manager
    db = DatabaseManager()
    
    # Get all contributions
    contributions = db.get_all_contributions()
    print(f"Total contributions: {len(contributions)}")
    
    # Print recent contributions
    for contribution in contributions[:5]:
        print(contribution)