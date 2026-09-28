#!/usr/bin/env python3
"""
Applies the Black / Charcoal + Gold + White palette to frontend/src/App.css.
Replaces all legacy blue (#2563eb, #1d4ed8, #3b82f6, #06b6d4, etc.)
and legacy white/light surfaces (#ffffff, #f8fafc, #f1f5f9, #eff6ff, #dbeafe)
with the strict enterprise color palette:
  Primary bg:     #080808
  Secondary bg:   #0D0D0D
  Card/surface:   #151515
  Elevated:       #1C1C1C
  Border:         #2A2A2A / #292929 / #242424
  Primary text:   #F5F5F5
  Secondary text: #B8B8B8
  Muted text:     #777777
  Accent Gold:    #D4AF37
  Lighter Gold:   #E5C45A
  Danger:         #B85C5C
"""

from pathlib import Path
import re

css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "App.css"
css = css_path.read_text(encoding="utf-8")

# 1. Update :root definition
root_pattern = r':root\s*\{[^}]*\}'

new_root = """:root {
  /* =========================================================
     ENTERPRISE CONTROL TOWER - BLACK + GOLD + WHITE PALETTE
  ========================================================= */
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  /* Primary Gold Accent */
  --accent: #D4AF37;
  --accent-gold: #D4AF37;
  --accent-hover: #E5C45A;
  --accent-active: #B89628;
  --accent-glow: rgba(212, 175, 55, 0.22);
  --accent-subtle: rgba(212, 175, 55, 0.10);
  --accent-border: rgba(212, 175, 55, 0.35);

  --brand-primary: #D4AF37;
  --brand-primary-hover: #E5C45A;
  --brand-primary-active: #B89628;
  --brand-glow: rgba(212, 175, 55, 0.20);
  
  /* Surfaces & Backgrounds */
  --bg-primary: #080808;
  --bg-secondary: #0D0D0D;
  --bg-canvas: #080808;
  --surface: #151515;
  --surface-hover: #1A1A1A;
  --surface-active: #222222;
  --surface-card: #151515;
  --surface-elevated: #1C1C1C;
  --surface-muted: #111111;
  
  /* Sidebar Surfaces */
  --sidebar-bg: #0A0A0A;
  --sidebar-border: #242424;
  --sidebar-text: #A8A8A8;
  --sidebar-text-bright: #F5F5F5;
  --sidebar-hover: #161616;
  --sidebar-active: #1B1B1B;
  
  /* Borders */
  --border: #292929;
  --border-light: #242424;
  --border-subtle: #1E1E1E;
  --border-focus: #D4AF37;
  --border-gold-hover: #5A4A18;
  
  /* Typography */
  --text-primary: #F5F5F5;
  --text-secondary: #B8B8B8;
  --text-muted: #777777;
  --text-subtle: #555555;
  --text-inverse: #080808;
  
  /* Status & Risk Colors - Calibrated Restrained Enterprise */
  --risk-critical: #B85C5C;
  --risk-critical-bg: rgba(184, 92, 92, 0.15);
  --risk-critical-border: rgba(184, 92, 92, 0.35);
  --risk-critical-text: #E07A7A;
  
  --risk-high: #D4AF37;
  --risk-high-bg: rgba(212, 175, 55, 0.15);
  --risk-high-border: rgba(212, 175, 55, 0.40);
  --risk-high-text: #E5C45A;
  
  --risk-medium: #C8B98A;
  --risk-medium-bg: #1E1E1E;
  --risk-medium-border: #3A3A3A;
  --risk-medium-text: #C8B98A;
  
  --risk-low: #888888;
  --risk-low-bg: #161616;
  --risk-low-border: #2C2C2C;
  --risk-low-text: #A0A0A0;
  
  --success: #D4AF37;
  --warning: #D4AF37;
  --danger: #B85C5C;
  --info: #B8B8B8;

  /* Shadows */
  --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.3);
  --shadow-card: 0 8px 30px rgba(0, 0, 0, 0.35);
  --shadow-hover: 0 10px 35px rgba(0, 0, 0, 0.45);
  --shadow-lg: 0 14px 40px rgba(0, 0, 0, 0.5);

  /* Radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* Transitions */
  --transition-fast: all 140ms ease;
  --transition: all 180ms ease;
  --transition-slow: all 260ms ease;

  color: var(--text-primary);
  background: var(--bg-primary);
}"""

css = re.sub(root_pattern, new_root, css, count=1)

# Specific Replacements for key components:

# Brand Mark
css = re.sub(
    r'\.brand-mark\s*\{[^}]*\}',
    """.brand-mark {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: #181818;
  color: #F5F5F5;
  border: 1px solid rgba(212, 175, 55, 0.4);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.06em;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  transition: var(--transition);
}""",
    css
)

# Brand Mark hover
css = re.sub(
    r'\.brand:hover \.brand-mark\s*\{[^}]*\}',
    """.brand:hover .brand-mark {
  border-color: #D4AF37;
  color: #D4AF37;
  transform: scale(1.04);
  box-shadow: 0 6px 20px rgba(212, 175, 55, 0.2);
}""",
    css
)

# Brand text
css = re.sub(
    r'\.brand-text span\s*\{[^}]*\}',
    """.brand-text span {
  font-size: 12px;
  color: #F5F5F5;
  letter-spacing: 0.02em;
}""",
    css
)

css = re.sub(
    r'\.brand-text strong\s*\{[^}]*\}',
    """.brand-text strong {
  font-size: 13px;
  color: #D4AF37;
  font-weight: 700;
  letter-spacing: -0.01em;
}""",
    css
)

# Sidebar section title
css = re.sub(
    r'\.sidebar-section-title\s*\{[^}]*\}',
    """.sidebar-section-title {
  padding: 0 12px 10px;
  color: #777777;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
}""",
    css
)

# Nav items
css = re.sub(
    r'\.nav-item\s*\{[^}]*\}',
    """.nav-item {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: #A8A8A8;
  text-decoration: none;
  font-size: 13px;
  font-weight: 550;
  position: relative;
  transition: var(--transition);
  user-select: none;
}""",
    css
)

css = re.sub(
    r'\.nav-item:hover\s*\{[^}]*\}',
    """.nav-item:hover {
  background: #141414;
  color: #F5F5F5;
  transform: translateX(2px);
}""",
    css
)

css = re.sub(
    r'\.nav-item\.active\s*\{[^}]*\}',
    """.nav-item.active {
  background: #1B1B1B;
  color: #D4AF37;
  font-weight: 650;
  border-left: 2px solid #D4AF37;
  box-shadow: none;
}""",
    css
)

# System card & indicator
css = re.sub(
    r'\.system-card\s*\{[^}]*\}',
    """.system-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #242424;
  border-radius: var(--radius-md);
  background: #121212;
  backdrop-filter: blur(8px);
  transition: var(--transition);
}""",
    css
)

css = re.sub(
    r'\.system-indicator\s*\{[^}]*\}',
    """.system-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #D4AF37;
  box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2);
  animation: pulse-dot 2.5s infinite ease-in-out;
}""",
    css
)

# Header
css = re.sub(
    r'\.top-header\s*\{[^}]*\}',
    """.top-header {
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 36px;
  background: #0B0B0B;
  border-bottom: 1px solid #242424;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}""",
    css
)

css = re.sub(
    r'\.header-eyebrow\s*\{[^}]*\}',
    """.header-eyebrow {
  margin: 0;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: #D4AF37;
}""",
    css
)

css = re.sub(
    r'\.page-eyebrow\s*\{[^}]*\}',
    """.page-eyebrow {
  margin: 0 0 6px;
  color: #D4AF37;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}""",
    css
)

css = re.sub(
    r'\.section-eyebrow\s*\{[^}]*\}',
    """.section-eyebrow {
  margin: 0 0 4px;
  color: #D4AF37;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}""",
    css
)

# Header status
css = re.sub(
    r'\.header-status\s*\{[^}]*\}',
    """.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: var(--radius-full);
  border: 1px solid #2A2A2A;
  background: #141414;
  color: #B8B8B8;
  font-size: 11px;
  font-weight: 650;
  transition: var(--transition);
  box-shadow: var(--shadow-sm);
}""",
    css
)

css = re.sub(
    r'\.header-status\.connected\s*\{[^}]*\}',
    """.header-status.connected {
  color: #D4AF37;
  background: rgba(212, 175, 55, 0.08);
  border-color: rgba(212, 175, 55, 0.3);
}""",
    css
)

css = re.sub(
    r'\.header-status\.connected \.status-dot\s*\{[^}]*\}',
    """.header-status.connected .status-dot {
  background: #D4AF37;
  box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2);
}""",
    css
)

css = re.sub(
    r'\.profile-avatar\s*\{[^}]*\}',
    """.profile-avatar {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #1C1C1C;
  color: #D4AF37;
  border: 1px solid #333333;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  box-shadow: var(--shadow-sm);
}""",
    css
)

css = re.sub(
    r'\.header-profile span\s*\{[^}]*\}',
    """.header-profile span {
  font-size: 10px;
  color: #D4AF37;
  font-weight: 600;
}""",
    css
)

# Primary Button
css = re.sub(
    r'\.primary-button\s*\{[^}]*\}',
    """.primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 18px;
  border: none;
  border-radius: var(--radius-md);
  background: #D4AF37;
  color: #0A0A0A;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  transition: var(--transition);
  user-select: none;
  outline: none;
}""",
    css
)

css = re.sub(
    r'\.primary-button:hover:not\(:disabled\)\s*\{[^}]*\}',
    """.primary-button:hover:not(:disabled) {
  background: #E5C45A;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(212, 175, 55, 0.3);
}""",
    css
)

css = re.sub(
    r'\.primary-button:active:not\(:disabled\)\s*\{[^}]*\}',
    """.primary-button:active:not(:disabled) {
  transform: translateY(0);
}""",
    css
)

# Secondary Button
css = re.sub(
    r'\.secondary-button\s*\{[^}]*\}',
    """.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid #343434;
  border-radius: var(--radius-md);
  background: #171717;
  color: #F5F5F5;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: var(--transition);
  user-select: none;
  outline: none;
}""",
    css
)

css = re.sub(
    r'\.secondary-button:hover:not\(:disabled\)\s*\{[^}]*\}',
    """.secondary-button:hover:not(:disabled) {
  border-color: #D4AF37;
  color: #D4AF37;
  background: #1C1C1C;
  transform: translateY(-1px);
}""",
    css
)

# Cards & KPI Cards
css = re.sub(
    r'\.kpi-card,\s*\.stat-card\s*\{[^}]*\}',
    """.kpi-card,
.stat-card {
  min-height: 146px;
  padding: 20px 22px;
  background: #151515;
  border: 1px solid #292929;
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
  position: relative;
  overflow: hidden;
}""",
    css
)

css = re.sub(
    r'\.kpi-card:hover,\s*\.stat-card:hover\s*\{[^}]*\}',
    """.kpi-card:hover,
.stat-card:hover {
  transform: translateY(-2px);
  border-color: #5A4A18;
  box-shadow: 0 10px 35px rgba(0, 0, 0, 0.45);
}""",
    css
)

css = re.sub(
    r'\.kpi-icon\s*\{[^}]*\}',
    """.kpi-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: rgba(212, 175, 55, 0.10);
  color: #D4AF37;
  border: 1px solid rgba(212, 175, 55, 0.25);
  font-size: 13px;
  font-weight: 750;
  transition: var(--transition-fast);
}""",
    css
)

# Table background and headers
css = re.sub(
    r'\.data-table-wrapper\s*\{[^}]*\}',
    """.data-table-wrapper {
  overflow-x: auto;
  width: 100%;
  background: #111111;
  border: 1px solid #292929;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: var(--transition);
}""",
    css
)

css = re.sub(
    r'\.risk-table th\s*\{[^}]*\}',
    """.risk-table th {
  padding: 13px 18px;
  background: #181818;
  border-bottom: 1px solid #292929;
  color: #AFAFAF;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}""",
    css
)

css = re.sub(
    r'\.risk-table td\s*\{[^}]*\}',
    """.risk-table td {
  padding: 14px 18px;
  border-bottom: 1px solid #202020;
  color: #B8B8B8;
  font-size: 13px;
  transition: background 120ms ease;
  vertical-align: middle;
}""",
    css
)

css = re.sub(
    r'\.risk-table tbody tr:hover\s*\{[^}]*\}',
    """.risk-table tbody tr:hover {
  background: #191919;
}""",
    css
)

# Inputs and selects
css = re.sub(
    r'(\.search-input,\s*\.risk-filter|input\[type="text"\],\s*select)\s*\{[^}]*\}',
    r"""\1 {
  background: #111111;
  border: 1px solid #303030;
  border-radius: var(--radius-md);
  color: #F5F5F5;
  padding: 10px 14px;
  font-size: 13px;
  outline: none;
  transition: var(--transition);
}""",
    css
)

# General hex color replacements across the file
# Replace blues with gold or dark equivalents
css = re.sub(r'#2563eb\b', '#D4AF37', css, flags=re.IGNORECASE)
css = re.sub(r'#1d4ed8\b', '#B89628', css, flags=re.IGNORECASE)
css = re.sub(r'#3b82f6\b', '#D4AF37', css, flags=re.IGNORECASE)
css = re.sub(r'#06b6d4\b', '#D4AF37', css, flags=re.IGNORECASE)
css = re.sub(r'#00ffff\b', '#D4AF37', css, flags=re.IGNORECASE)
css = re.sub(r'#0ea5e9\b', '#E5C45A', css, flags=re.IGNORECASE)

# Replace blue rgba
css = re.sub(r'rgba\(\s*37,\s*99,\s*235,\s*0?\.\d+\)', 'rgba(212, 175, 55, 0.15)', css)
css = re.sub(r'rgba\(\s*59,\s*130,\s*246,\s*0?\.\d+\)', 'rgba(212, 175, 55, 0.15)', css)

# Replace light mode backgrounds
css = re.sub(r'background:\s*#ffffff\s*;', 'background: #151515;', css, flags=re.IGNORECASE)
css = re.sub(r'background:\s*#f8fafc\s*;', 'background: #181818;', css, flags=re.IGNORECASE)
css = re.sub(r'background:\s*#f1f5f9\s*;', 'background: #1C1C1C;', css, flags=re.IGNORECASE)
css = re.sub(r'background:\s*#eff6ff\s*;', 'background: rgba(212, 175, 55, 0.08);', css, flags=re.IGNORECASE)
css = re.sub(r'background:\s*#dbeafe\s*;', 'background: #242424;', css, flags=re.IGNORECASE)

# Replace light borders
css = re.sub(r'border:\s*1px solid #dbe4ef\s*;', 'border: 1px solid #292929;', css, flags=re.IGNORECASE)
css = re.sub(r'border:\s*1px solid #e2e8f0\s*;', 'border: 1px solid #292929;', css, flags=re.IGNORECASE)
css = re.sub(r'border:\s*1px solid #cbd5e1\s*;', 'border: 1px solid #303030;', css, flags=re.IGNORECASE)
css = re.sub(r'border-color:\s*#e2e8f0\s*;', 'border-color: #292929;', css, flags=re.IGNORECASE)
css = re.sub(r'border-bottom:\s*1px solid #e2e8f0\s*;', 'border-bottom: 1px solid #292929;', css, flags=re.IGNORECASE)
css = re.sub(r'border-bottom:\s*1px solid #f1f5f9\s*;', 'border-bottom: 1px solid #202020;', css, flags=re.IGNORECASE)
css = re.sub(r'border-color:\s*#cbd5e1\s*;', 'border-color: #343434;', css, flags=re.IGNORECASE)

# Replace dark text on light backgrounds with light text for dark mode
css = re.sub(r'color:\s*#0f172a\s*;', 'color: #F5F5F5;', css, flags=re.IGNORECASE)
css = re.sub(r'color:\s*#1e293b\s*;', 'color: #E0E0E0;', css, flags=re.IGNORECASE)
css = re.sub(r'color:\s*#334155\s*;', 'color: #B8B8B8;', css, flags=re.IGNORECASE)
css = re.sub(r'color:\s*#475569\s*;', 'color: #A0A0A0;', css, flags=re.IGNORECASE)
css = re.sub(r'color:\s*#64748b\s*;', 'color: #777777;', css, flags=re.IGNORECASE)
css = re.sub(r'color:\s*#94a3b8\s*;', 'color: #888888;', css, flags=re.IGNORECASE)

# Replace light shadows
css = re.sub(r'rgba\(\s*15,\s*23,\s*42,\s*0?\.\d+\)', 'rgba(0, 0, 0, 0.35)', css)

# Write updated css
css_path.write_text(css, encoding="utf-8")
print("App.css updated to Black + Charcoal + Gold + White palette successfully!")
