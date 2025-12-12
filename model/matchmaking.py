"""Matchmaking / Profile Setup - JSON File Storage

Simple JSON-based storage for profile setup tracking, independent from user.py
Functions similar to the jokes API but for matchmaking setup data.
"""

import json
import os
import fcntl
from datetime import datetime
from flask import current_app


def get_profile_setups_file():
    """Get the path to the profile setups JSON file."""
    data_folder = current_app.config.get('DATA_FOLDER', 'instance/data')
    return os.path.join(data_folder, 'profile_setups.json')


def _read_profile_setups():
    """Read profile setups from JSON file with file locking."""
    setups_file = get_profile_setups_file()
    if not os.path.exists(setups_file):
        return []
    try:
        with open(setups_file, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
            except Exception:
                data = []
            fcntl.flock(f, fcntl.LOCK_UN)
        return data
    except Exception:
        return []


def _write_profile_setups(data):
    """Write profile setups to JSON file with file locking."""
    setups_file = get_profile_setups_file()
    os.makedirs(os.path.dirname(setups_file), exist_ok=True)
    with open(setups_file, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


def profile_setup_exists(uid):
    """Check if a profile setup exists for a given uid."""
    setups = _read_profile_setups()
    return any(setup['uid'] == uid for setup in setups)


def create_profile_setup(uid):
    """Create a new profile setup record for a user."""
    setups = _read_profile_setups()
    
    # Check if already exists
    if any(setup['uid'] == uid for setup in setups):
        return None
    
    # Create new record
    new_setup = {
        'id': len(setups) + 1,
        'uid': uid,
        'created_at': datetime.utcnow().isoformat()
    }
    setups.append(new_setup)
    _write_profile_setups(setups)
    return new_setup


def get_profile_setup(uid):
    """Get a profile setup record for a given uid."""
    setups = _read_profile_setups()
    for setup in setups:
        if setup['uid'] == uid:
            return setup
    return None


def get_all_profile_setups():
    """Get all profile setups."""
    return _read_profile_setups()
