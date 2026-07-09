import os
import sys

# Ensure parent directory is accessible for standalone package execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import get_connection

# Resolve dynamic paths depending on local vs cPanel execution environments
BASE_DIR = "/home/vsmwrurd/repositories/AiEC-Bot" if os.path.exists("/home/vsmwrurd") else "."
TX_FILE_PATH = os.path.join(BASE_DIR, "knowledge_base/company_data.txt")

def populate_kb():
    if not os.path.exists(TX_FILE_PATH):
        print(f"[-] Knowledge source file not found at {TX_FILE_PATH}")
        return

    print(f"[*] Reading data from {TX_FILE_PATH}...")
    with open(TX_FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    entries = [block.strip() for block in content.split("\n\n") if block.strip()]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_base;")
        
        for entry in entries:
            lines = entry.split('\n')
            category = "General"
            keyword = lines[0][:50] if lines else "Info Block"
            
            cursor.execute("""
                INSERT INTO knowledge_base (category, keyword, content)
                VALUES (?, ?, ?)
            """, (category, keyword, entry))
            
        conn.commit()
        print(f"[+] Ingested {len(entries)} data blocks cleanly into SQLite 'knowledge_base'.")

if __name__ == "__main__":
    populate_kb()
