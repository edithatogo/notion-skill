#!/usr/bin/env python3
"""
Sync Adapters

Synchronizes SKILL.md to adapter directories for different AI agent platforms.

Usage:
    python scripts/sync_adapters.py
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Repository root
ROOT = Path(__file__).parent.parent

# Source file
SOURCE_SKILL = ROOT / "SKILL.md"
SOURCE_AGENTS = ROOT / "AGENTS.md"

# Adapter directories
ADAPTERS_DIR = ROOT / "adapters"

# Adapter mapping
ADAPTERS = {
    "qwen": {
        "name": "Qwen CLI",
        "config_file": "QWEN.md",
        "format": "qwen_context",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "config_file": "COPILOT.md",
        "format": "copilot_skill",
    },
    "vscode": {
        "name": "VS Code",
        "config_file": "VSCODE.md",
        "format": "vscode_extension",
    },
    "claude": {
        "name": "Claude Code",
        "config_file": "CLAUDE.md",
        "format": "claude_skill",
    },
    "cline": {
        "name": "Cline",
        "config_file": "CLINE.md",
        "format": "cline_skill",
    },
    "kilo": {
        "name": "Kilo Code",
        "config_file": "KILO.md",
        "format": "kilo_skill",
    },
    "amp": {
        "name": "Amp",
        "config_file": "AMP.md",
        "format": "amp_skill",
    },
    "opencode": {
        "name": "OpenCode",
        "config_file": "OPENCODE.md",
        "format": "opencode_skill",
    },
    "gemini": {
        "name": "Gemini CLI",
        "config_file": "GEMINI.md",
        "format": "gemini_skill",
    },
}


def sync_adapter(adapter_key: str, adapter_config: dict) -> bool:
    """Sync skill to a specific adapter."""
    adapter_dir = ADAPTERS_DIR / adapter_key
    
    # Create adapter directory if it doesn't exist
    adapter_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy SKILL.md with adapter-specific name
    dest_file = adapter_dir / adapter_config["config_file"]
    
    try:
        # Read source
        content = SOURCE_SKILL.read_text(encoding="utf-8")
        
        # Add adapter-specific header
        header = f"""---
name: notion-skill
version: 1.0.0
adapter: {adapter_config['name']}
synced: {datetime.now().strftime('%Y-%m-%d')}
source: SKILL.md
---

"""
        
        # Write to adapter
        dest_file.write_text(header + content, encoding="utf-8")
        
        print(f"✓ Synced to {adapter_config['name']} ({dest_file.name})")
        return True
        
    except Exception as e:
        print(f"✗ Failed to sync to {adapter_config['name']}: {e}")
        return False


def main():
    print("\n🔄 Syncing Notion Skill to Adapters\n")
    
    if not SOURCE_SKILL.exists():
        print(f"Error: Source file not found: {SOURCE_SKILL}")
        return 1
    
    # Ensure adapters directory exists
    ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sync to each adapter
    success_count = 0
    for adapter_key, adapter_config in ADAPTERS.items():
        if sync_adapter(adapter_key, adapter_config):
            success_count += 1
    
    print(f"\n✅ Synced {success_count}/{len(ADAPTERS)} adapters")
    
    # Update AGENTS.md metadata
    if SOURCE_AGENTS.exists():
        content = SOURCE_AGENTS.read_text(encoding="utf-8")
        # Update last_synced timestamp
        content = content.replace(
            "last_synced: 2026-02-23",
            f"last_synced: {datetime.now().strftime('%Y-%m-%d')}"
        )
        SOURCE_AGENTS.write_text(content, encoding="utf-8")
        print("✓ Updated AGENTS.md timestamp")
    
    print("\n✨ Adapter sync complete!\n")
    return 0


if __name__ == "__main__":
    exit(main())
