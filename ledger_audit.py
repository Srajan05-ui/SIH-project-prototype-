import hashlib
import sqlite3
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LedgerAudit:
    def __init__(self, db_path='audit_ledger.db'):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    route TEXT,
                    pure_fare REAL,
                    collector_id TEXT,
                    hash TEXT,
                    prev_hash TEXT
                )
            ''')
            
    def _calculate_hash(self, timestamp, route, pure_fare, collector_id, prev_hash):
        # Hash combination of target payload
        data = f"{timestamp}{route}{pure_fare}{collector_id}{prev_hash}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
        
    def get_last_hash(self, conn):
        cursor = conn.cursor()
        cursor.execute('SELECT hash FROM transactions ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        return row[0] if row else "0" * 64
        
    def record_transaction(self, route, pure_fare, collector_id):
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            prev_hash = self.get_last_hash(conn)
            tx_hash = self._calculate_hash(timestamp, route, pure_fare, collector_id, prev_hash)
            
            conn.execute('''
                INSERT INTO transactions (timestamp, route, pure_fare, collector_id, hash, prev_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, route, pure_fare, collector_id, tx_hash, prev_hash))
            
        logger.info(f"Recorded block securely. Hash: {tx_hash[:8]}...")
        return tx_hash
        
    def validate_ledger(self):
        """Scans the ledger and verifies cryptographic integrity of the blockchain."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql('SELECT * FROM transactions ORDER BY id', conn)
            
        if df.empty:
            return True, "Ledger is empty."
            
        valid = True
        issues = []
        expected_prev = "0" * 64
        
        for _, row in df.iterrows():
            if row['prev_hash'] != expected_prev:
                valid = False
                issues.append(f"Broken chain at ID {row['id']}")
                
            calc_hash = self._calculate_hash(row['timestamp'], row['route'], row['pure_fare'], row['collector_id'], row['prev_hash'])
            if calc_hash != row['hash']:
                valid = False
                issues.append(f"Tampered data at ID {row['id']}")
                
            expected_prev = row['hash']
            
        if valid:
            return True, "✅ Cryptographically Sealed & Tamper-Proof"
        else:
            return False, "; ".join(issues)
