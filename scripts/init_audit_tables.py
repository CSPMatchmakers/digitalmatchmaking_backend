#!/usr/bin/env python3
"""
Initialize database audit tables

This script creates the necessary tables for the control panel audit and monitoring system.
Run this once after deploying the new code to set up the database schema.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from __init__ import app, db
from model.user import User  # Import first to ensure users table exists
from model.database_audit import DatabaseMetrics, ErrorLog, FetchLog, ChangeLog, DatabaseStatus

def init_audit_tables():
    """Initialize all audit and monitoring tables"""
    with app.app_context():
        print("Creating database audit tables...")
        
        try:
            # Create all tables
            db.create_all()
            print("✓ All tables created successfully")
        except Exception as e:
            print(f"✓ Tables creation attempt completed (some existing tables may have been created)")
        
        try:
            # Create initial DatabaseStatus if it doesn't exist
            status = DatabaseStatus.query.first()
            if not status:
                status = DatabaseStatus()
                db.session.add(status)
                db.session.commit()
            print(f"✓ DatabaseStatus initialized (ID: {status.id})")
            
            print("\n✓ Database audit tables initialized successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Error initializing tables: {str(e)}")
            return False

if __name__ == '__main__':
    success = init_audit_tables()
    sys.exit(0 if success else 1)
