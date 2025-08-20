import sqlite3
import json
from datetime import datetime

def view_database():
    """View database contents"""
    conn = sqlite3.connect('startup_analyzer.db')
    cursor = conn.cursor()
    
    print("=== STARTUP ANALYZER DATABASE ===\n")
    
    # Show tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("📋 Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    print()
    
    # View analysis history
    print("📊 Analysis History:")
    cursor.execute('''
        SELECT filename, document_type, created_at, id
        FROM analysis_history 
        ORDER BY created_at DESC 
        LIMIT 10
    ''')
    history = cursor.fetchall()
    
    if history:
        for row in history:
            print(f"  📄 {row[0]} ({row[1]}) - {row[2]} (ID: {row[3]})")
    else:
        print("  No analyses yet")
    print()
    
    # View user metrics
    print("📈 Usage Metrics:")
    cursor.execute('''
        SELECT document_type, analysis_count, last_analyzed
        FROM user_metrics 
        ORDER BY analysis_count DESC
    ''')
    metrics = cursor.fetchall()
    
    if metrics:
        for row in metrics:
            print(f"  📊 {row[0]}: {row[1]} analyses (Last: {row[2]})")
    else:
        print("  No metrics yet")
    print()
    
    # Total counts
    cursor.execute('SELECT COUNT(*) FROM analysis_history')
    total_analyses = cursor.fetchone()[0]
    print(f"🎯 Total Analyses: {total_analyses}")
    
    conn.close()

if __name__ == "__main__":
    view_database()
