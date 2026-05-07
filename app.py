import streamlit as st
import joblib
import pandas as pd
import smtplib
import json, os, random, string, time
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

st.set_page_config(page_title="Churn Intelligence | Donatus Victor", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

OWNER_EMAIL    = "donatusvictor76@gmail.com"
OWNER_PASSWORD = "donatus2024"
OWNER_NAME     = "Donatus Victor"
OWNER_TITLE    = "Business Data Scientist"
OWNER_PHONE    = "+2348137790780"
OWNER_LI       = "https://www.linkedin.com/in/donatusvictor"

# ----- CSS (unchanged) -----
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.brand-bar{background:linear-gradient(135deg,#0d1117,#161b27,#0f2027);border-radius:16px;padding:18px 24px;margin-bottom:8px;border:1px solid rgba(0,255,180,.15);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;}
.brand-title{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:600;color:#00ffb4;letter-spacing:.04em;margin:0;}
.brand-name{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:#fff;margin:2px 0 0;}
.brand-sub{font-size:.75rem;color:rgba(255,255,255,.4);margin:2px 0 0;text-transform:uppercase;letter-spacing:.06em;}
.brand-buttons{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.brand-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;border-radius:50px;font-size:.78rem;font-weight:500;text-decoration:none !important;transition:all .2s;white-space:nowrap;}
.btn-phone{background:#00ffb4;color:#0d1117 !important;}
.btn-linkedin{background:#0a66c2;color:#fff !important;}
.btn-email{background:#1e293b;color:#94a3b8 !important;border:1px solid #334155;}
.risk-critical{background:#ff4757;color:#fff;padding:3px 14px;border-radius:50px;font-weight:600;font-size:.82rem;}
.risk-high{background:#ffa502;color:#0d1117;padding:3px 14px;border-radius:50px;font-weight:600;font-size:.82rem;}
.risk-medium{background:#eccc68;color:#0d1117;padding:3px 14px;border-radius:50px;font-weight:600;font-size:.82rem;}
.risk-low{background:#2ed573;color:#0d1117;padding:3px 14px;border-radius:50px;font-weight:600;font-size:.82rem;}
.sec-hdr{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#f1f5f9;border-bottom:2px solid #00ffb4;padding-bottom:5px;margin:16px 0 12px;display:inline-block;}
[data-testid="stSidebar"]{background:#0d1117;padding-bottom:150px !important;}
[data-testid="stSidebar"] .stMarkdown{color:#94a3b8;}
.stTabs [data-baseweb="tab"]{font-family:'Syne',sans-serif;font-weight:600;}
div.stButton>button{border-radius:8px;}
.landing-hero { text-align: center; padding: 3rem 1rem; background: linear-gradient(135deg, #0a0f1a, #0f2027); border-radius: 24px; margin-bottom: 2rem; }
.landing-feature { background: #0d1117; border-radius: 16px; padding: 1.5rem; border: 1px solid #1e293b; margin: 1rem 0; }
</style>""", unsafe_allow_html=True)

# ----- File management -----
CONFIG_FILE = "alert_config.json"
HISTORY_FILE = "alert_history.json"
USERS_FILE = "users.json"

def _load(p, d):
    if os.path.exists(p):
        try:
            with open(p) as f: return json.load(f)
        except: pass
    return d
def _save(p, d):
    with open(p, "w") as f: json.dump(d, f, indent=2)

def load_config():
    d = {"emails": [], "telegram_bot_token": "", "telegram_chat_ids": [], "gmail_sender": "", "gmail_app_password": "", "churn_threshold": 0.70}
    d.update(_load(CONFIG_FILE, {}))
    return d
def save_config(c): _save(CONFIG_FILE, c)
def load_history(): return _load(HISTORY_FILE, [])
def save_history(h): _save(HISTORY_FILE, h[-500:])
def load_users(): return _load(USERS_FILE, {})
def save_users(u): _save(USERS_FILE, u)
def log_alert(e): h = load_history(); h.append(e); save_history(h)
def gen_otp(): return "".join(random.choices(string.digits, k=6))

# ----- Email & Telegram functions -----
def send_gmail(cfg, subj, html, recipients=None):
    targets = recipients if recipients is not None else cfg.get("emails", [])
    if not cfg.get("gmail_sender") or not cfg.get("gmail_app_password"): return False, "Gmail not configured."
    if not targets: return False, "No recipients."
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(cfg["gmail_sender"], cfg["gmail_app_password"])
            for r in targets:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subj
                msg["From"] = f"Churn Intelligence <{cfg['gmail_sender']}>"
                msg["To"] = r
                msg.attach(MIMEText(html, "html"))
                s.sendmail(cfg["gmail_sender"], r, msg.as_string())
        return True, f"Sent to {len(targets)} recipient(s)."
    except Exception as e: return False, f"Email error: {e}"

def send_telegram(cfg, message):
    token = cfg.get("telegram_bot_token", "").strip()
    chats = cfg.get("telegram_chat_ids", [])
    if not token: return False, "No token."
    if not chats: return False, "No chats."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    sent = 0
    for cid in chats:
        try:
            r = requests.post(url, json={"chat_id": cid.strip(), "text": message, "parse_mode": "HTML"}, timeout=10)
            if r.ok: sent += 1
        except: pass
    return sent > 0, f"Sent to {sent}/{len(chats)} chat(s)."

# ----- UI helpers -----
def _rc(p): return "#ff4757" if p>=.8 else "#ffa502" if p>=.6 else "#eccc68" if p>=.4 else "#2ed573"

def tpl_single(phone, prob, cluster, profile, strategy, factor, ts):
    h = "🚨 High Risk Alert" if prob>=.7 else "📊 Churn Scan Result"
    rc = _rc(prob)
    return f"""<div style="font-family:'Segoe UI',sans-serif;max-width:560px;margin:auto;background:#f8fafc;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
  <div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;">
    <p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">Churn Intelligence System</p>
    <h1 style="color:#fff;margin:0;font-size:20px;">{h}</h1>
    <p style="color:#94a3b8;font-size:12px;margin:5px 0 0">{ts}</p>
  </div>
  <div style="padding:22px 26px;">
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px;width:150px">Phone</td><td style="font-weight:600;color:#1e293b">{phone}</td></tr>
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px">Churn Risk</td><td style="background:{rc};color:#fff;padding:3px 12px;border-radius:20px;font-weight:700">{prob*100:.1f}%</span></td><tr>
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px">Segment</td><td style="font-weight:600;color:#1e293b">Cluster {cluster} — {profile}</td></tr>
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px">Top Risk Factor</td><td style="color:#ef4444;font-weight:500">{factor}</td></tr>
    </table>
    <div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;padding:12px 16px;margin:18px 0">
      <p style="margin:0;font-size:13px;color:#92400e;font-weight:600">Recommended Action</p>
      <p style="margin:5px 0 0;font-size:13px;color:#78350f">{strategy}</p>
    </div>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:16px">Churn Intelligence · <strong>{OWNER_NAME}</strong> · {OWNER_PHONE}</p>
  </div>
</div>"""

def tpl_bulk(lst, threshold, ts):
    def row_html(r):
        color = _rc(r["prob"])
        return (f"<tr style='border-bottom:1px solid #e2e8f0'>"
                f"<td style='padding:8px;font-size:12px'>{r['phone']}</td>"
                f"<td style='padding:8px;font-size:12px;font-weight:700;color:{color}'>{r['prob']*100:.1f}%</td>"
                f"<td style='padding:8px;font-size:12px'>{r['profile']}</td>"
                f"<td style='padding:8px;font-size:12px;color:#64748b'>{r['factor']}</td>"
                f"<td style='padding:8px;font-size:12px'>{r['strategy']}</td></tr>")
    rows = "".join([row_html(r) for r in sorted(lst, key=lambda x: x["prob"], reverse=True)])
    return f"""<div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;">
    <p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">Bulk Scan · {ts}</p>
    <h1 style="color:#fff;margin:0;font-size:20px;">📊 Churn Intelligence Report</h1>
    <p style="color:#94a3b8;font-size:13px;margin:7px 0 0">{len(lst)} customers flagged above {threshold*100:.0f}% threshold</p>
  </div>
  <div style="padding:22px 26px;overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;min-width:580px">
      <thead><tr style="background:#f1f5f9"><th style="padding:9px 8px;font-size:11px;text-align:left">PHONE</th><th>CHURN %</th><th>SEGMENT</th><th>TOP FACTOR</th><th>ACTION</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:20px">Churn Intelligence · <strong>{OWNER_NAME}</strong> · {OWNER_PHONE}</p>
  </div>
</div>"""

def tpl_otp(name, user_email, otp):
    return f"""<div style="font-family:'Segoe UI',sans-serif;max-width:480px;margin:auto;background:#f8fafc;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
  <div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;"><p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">New Business Signup</p><h1 style="color:#fff;margin:0;font-size:20px;">Approve New Company</h1></div>
  <div style="padding:22px 26px;"><p style="color:#1e293b;font-size:14px"><strong>{name}</strong> ({user_email}) has registered their company.</p>
    <div style="background:#f0fdf4;border:2px solid #00ffb4;border-radius:10px;padding:16px;text-align:center;margin:20px 0">
      <p style="margin:0;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px">Activation OTP for {name}</p>
      <p style="margin:8px 0 0;font-family:monospace;font-size:2.4rem;font-weight:800;color:#0d1117;letter-spacing:.25em">{otp}</p>
    </div>
    <p style="color:#64748b;font-size:13px">After approval, they can set their alert limits. Contact them for pricing discussion.</p>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:16px">Churn Intelligence · {OWNER_NAME}</p></div></div>"""

def tg_single(phone, prob, cluster, profile, strategy, factor, ts):
    i = "🔴" if prob>=.8 else "🟠" if prob>=.6 else "🟡" if prob>=.4 else "🟢"
    return f"📡 <b>CHURN SCAN — {ts}</b>\n──────────────────────\n{i} <b>Risk: {prob*100:.1f}%</b>\n\n📞 Phone: <code>{phone}</code>\n📌 Cluster {cluster} — {profile}\n⚠️ Top Factor: {factor}\n\n💡 <b>Action:</b> {strategy}\n──────────────────────\nBy <b>{OWNER_NAME}</b> | {OWNER_PHONE}"

def cluster_info(c): return {0:("Basic Traditionalist","Upsell Digital Bundles and online security add-ons."),1:("At-Risk Starter","Offer Annual Contract discounts immediately."),2:("Loyal Power User","Enrol in Premium Loyalty Programme.")}.get(int(c),("Unknown","Manual review required."))
def top_factor(row):
    for col, lbl in [("Contract_Month-to-month","Month-to-Month Contract"),("InternetService_Fiber optic","Fiber Optic Internet"),("OnlineSecurity_No","No Online Security"),("TechSupport_No","No Tech Support")]:
        if col in row.index and row[col]==1: return lbl
    return "Usage pattern anomaly"
def risk_label(p): return "CRITICAL" if p>=.8 else "HIGH" if p>=.6 else "MEDIUM" if p>=.4 else "LOW"
def risk_badge(p): cls={"CRITICAL":"risk-critical","HIGH":"risk-high","MEDIUM":"risk-medium","LOW":"risk-low"}[risk_label(p)]; return f'<span class="{cls}">{risk_label(p)}</span>'

@st.cache_resource(show_spinner="Loading intelligence models…")
def load_models():
    mdl = joblib.load("churn_model.pkl")
    km = joblib.load("segmentation_model.pkl")
    sc = joblib.load("scaler.pkl")
    db = pd.read_csv("customer_lookup_database.csv", dtype={"Phone_Number": str})
    return mdl, km, sc, db

try:
    model, kmeans, scaler, _default_db = load_models()
    all_columns = list(model.get_booster().feature_names)
    tenure_col = next((c for c in all_columns if "tenure" in c.lower()), all_columns[0])
    charge_col = next((c for c in all_columns if "charge" in c.lower()), all_columns[1])
except Exception as e:
    st.error(f"Could not load models or customer_lookup_database.csv: {e}"); st.stop()

# ----- Session state init -----
for k, v in [("cfg", None), ("logged_in", False), ("user_email", ""), ("user_name", ""), ("is_owner", False), ("custom_db", None), ("auth_step", "login")]:
    if k not in st.session_state: st.session_state[k] = v
if st.session_state.cfg is None: st.session_state.cfg = load_config()
cfg = st.session_state.cfg

# ----- Sidebar (only shown when logged in) -----
def show_sidebar():
    with st.sidebar:
        st.markdown("### 🔍 Customer Lookup")
        search_term = st.text_input("Customer ID or Phone Number", placeholder="CUST_00001 or 08012345678")
        run_single = st.button("🔎 Analyse Customer", use_container_width=True)
        st.divider()
        threshold_pct = st.slider("🎚️ Alert Threshold (%)", 40, 95, int(cfg.get("churn_threshold", 0.70)*100), 5)
        cfg["churn_threshold"] = threshold_pct/100; save_config(cfg)
        st.divider()
        st.markdown("### 🗄️ Connect Your Database")
        st.caption("Upload a preprocessed customer CSV (all model feature columns + Phone_Number).")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="db_up")
        if uploaded:
            try:
                tmp = pd.read_csv(uploaded, dtype={"Phone_Number": str})
                miss = [c for c in all_columns if c not in tmp.columns]
                if miss: st.error(f"Missing {len(miss)} column(s): {', '.join(miss[:4])}…")
                else:
                    st.session_state.custom_db = tmp
                    st.success(f"✅ {len(tmp):,} customers loaded.")
            except Exception as e: st.error(f"Read error: {e}")
        if st.session_state.custom_db is not None:
            if st.button("🔄 Revert to Default DB", use_container_width=True):
                st.session_state.custom_db = None
                st.rerun()
        st.divider()
        st.caption(f"📊 {len(lookup_db):,} customers in database")
        if st.button("🚪 Sign Out", use_container_width=True):
            for k, v in [("logged_in", False), ("user_email", ""), ("user_name", ""), ("is_owner", False), ("auth_step", "login")]:
                st.session_state[k] = v
            st.rerun()
    return run_single, search_term, threshold_pct

# ----- Landing Page (with brand bar and "Retain") -----
def landing_page():
    st.markdown(f"""
    <div class="brand-bar">
      <div>
        <p class="brand-title">📡 CHURN INTELLIGENCE SYSTEM</p>
        <p class="brand-name">{OWNER_NAME}</p>
        <p class="brand-sub">{OWNER_TITLE}</p>
      </div>
      <div class="brand-buttons">
        <a class="brand-btn btn-phone" href="tel:{OWNER_PHONE}">📞 Phone</a>
        <a class="brand-btn btn-linkedin" href="{OWNER_LI}" target="_blank">💼 LinkedIn</a>
        <a class="brand-btn btn-email" href="mailto:{OWNER_EMAIL}">✉️ Email</a>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="landing-hero">
            <h1 style="font-family:Syne; font-size:2.5rem; color:#00ffb4;">Predict. Prevent. Retain.</h1>
            <p style="font-size:1.2rem; color:#cbd5e1;">AI‑powered churn prediction and retention intelligence for Businesses.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## 🚀 Why Churn Intelligence?")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="landing-feature">
        <h3>🎯 85% Accuracy</h3>
        <p>Identify customers about to leave with machine learning models trained on real telecom data.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="landing-feature">
        <h3>📊 Actionable Insights</h3>
        <p>Get the top risk factor and a recommended retention strategy for every customer.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="landing-feature">
        <h3>🔔 Real‑time Alerts</h3>
        <p>Receive email and Telegram alerts when churn risk exceeds your threshold.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("## 💼 For Every Operators")
    st.markdown("""
    - Upload your own customer database (CSV) we handle the rest.
    - Set custom alert thresholds and notification channels.
    - Bulk scan thousands of customers in seconds.
    - **Pricing is tailored to your needs. Contact us for a discussion.**
    """)

    # st.markdown("## 👨‍💻 Built by Donatus Victor")
    # st.markdown(f"""
    # - 📞 {OWNER_PHONE}
    # - 💼 [LinkedIn]({OWNER_LI})
    # - ✉️ {OWNER_EMAIL}
    # """)

    st.divider()
    st.markdown("### 🏢 Ready to reduce churn?")
    col_a, col_b, col_c = st.columns(3)
    with col_b:
        if st.button("📝 Sign up your company", use_container_width=True, type="primary"):
            st.session_state.auth_step = "register"
            st.rerun()

    st.markdown("---")
    col_login1, col_login2, col_login3 = st.columns(3)
    with col_login2:
        if st.button("🔐 Already have an account? Login here", use_container_width=True):
            st.session_state.auth_step = "login"
            st.rerun()

if st.session_state.logged_in:
    st.markdown("---")
    st.caption("© 2025 Churn Intelligence by Donatus Victor. All rights reserved.")

# ----- Auth UI (with Resend OTP) -----
def show_auth():
    col = st.columns([1, 1.2, 1])[1]
    users = load_users()
    with col:
        if st.session_state.auth_step == "login":
            with st.container(border=True):
                st.markdown("#### 🔐 Sign In to your Company Account")
                email = st.text_input("Business Email", key="li_em", placeholder="company@example.com")
                pwd = st.text_input("Password", key="li_pw", type="password", placeholder="Your password")
                ca, cb = st.columns(2)
                do_login = ca.button("Sign In", use_container_width=True, type="primary")
                do_reg = cb.button("New? Sign up", use_container_width=True)
                if do_login:
                    em = email.strip()
                    pw = pwd.strip()
                    if em == OWNER_EMAIL and pw == OWNER_PASSWORD:
                        st.session_state.update({"logged_in": True, "user_email": OWNER_EMAIL, "user_name": OWNER_NAME, "is_owner": True})
                        st.rerun()
                    else:
                        u = users.get(em)
                        if u is None:
                            st.error("❌ Email not registered. Please sign up first.")
                        elif u.get("status") != "approved":
                            st.warning("⏳ Your account is pending approval. You will receive an OTP via email once approved.")
                        elif u.get("password", "") != pw:
                            st.error("❌ Incorrect password.")
                        else:
                            st.session_state.update({"logged_in": True, "user_email": em, "user_name": u.get("name", "User"), "is_owner": False})
                            st.rerun()
                if do_reg:
                    st.session_state.auth_step = "register"
                    st.rerun()
            with st.expander("🔑 Received an OTP? Activate here"):
                oe = st.text_input("Your Email", key="otp_em", placeholder="company@example.com")
                ov = st.text_input("OTP Code", key="otp_val", placeholder="6-digit code", max_chars=6)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Activate Account", use_container_width=True):
                        email_clean = oe.strip()
                        otp_clean = ov.strip()
                        u = users.get(email_clean)
                        if u is None:
                            st.error("❌ Email not found. Please sign up first.")
                        elif u.get("status") == "approved":
                            st.warning("✅ This account is already approved. You can sign in directly.")
                        elif u.get("otp") == otp_clean:
                            u["status"] = "approved"
                            # Optionally clear OTP after use
                            # u["otp"] = ""
                            save_users(users)
                            st.success("✅ Account activated! You can now sign in.")
                        else:
                            st.error("❌ Wrong OTP. Please check your email or click 'Resend OTP' below.")
                with col_b:
                    if st.button("Resend OTP", use_container_width=True):
                        email_clean = oe.strip()
                        u = users.get(email_clean)
                        if u is None:
                            st.error("❌ Email not found. Please sign up first.")
                        elif u.get("status") == "approved":
                            st.warning("Account already approved. No OTP needed.")
                        else:
                            new_otp = gen_otp()
                            u["otp"] = new_otp
                            save_users(users)
                            ok, msg = send_gmail(cfg, f"New OTP for {u.get('name', 'User')} | Churn Intelligence",
                                                 tpl_otp(u.get('name', 'User'), email_clean, new_otp), recipients=[email_clean])
                            if ok:
                                st.success(f"✅ New OTP sent to {email_clean}. Check your inbox (spam folder).")
                            else:
                                st.error(f"Failed to send email: {msg}. Contact {OWNER_EMAIL} for your OTP.")
        elif st.session_state.auth_step == "register":
            with st.container(border=True):
                st.markdown("#### 🏢 Register Your Company")
                st.caption(f"Submit your company details. {OWNER_NAME} will review and contact you to discuss pricing and set up your account.")
                r_name = st.text_input("Full Name", key="rg_name", placeholder="Jane Smith")
                r_email = st.text_input("Work Email", key="rg_em", placeholder="company@example.com")
                r_co = st.text_input("Company Name", key="rg_co", placeholder="Acme Telecom Ltd")
                r_pwd = st.text_input("Choose Password", key="rg_pw", type="password", placeholder="Min 6 characters")
                r_pwd2 = st.text_input("Confirm Password", key="rg_pw2", type="password", placeholder="Repeat password")
                ca, cb = st.columns(2)
                do_sub = ca.button("Submit Registration", use_container_width=True, type="primary")
                do_back = cb.button("← Back to Login", use_container_width=True)
                if do_back:
                    st.session_state.auth_step = "login"
                    st.rerun()
                if do_sub:
                    if not r_name.strip(): st.error("Please enter your full name.")
                    elif not r_email.strip() or "@" not in r_email: st.error("Valid email required.")
                    elif not r_co.strip(): st.error("Company name required.")
                    elif not r_pwd.strip() or len(r_pwd.strip()) < 6: st.error("Password must be at least 6 characters.")
                    elif r_pwd.strip() != r_pwd2.strip(): st.error("Passwords do not match.")
                    elif r_email.strip() == OWNER_EMAIL: st.error("That is the admin account.")
                    elif r_email.strip() in users and users[r_email.strip()].get("status") == "approved":
                        st.warning("Already approved. Please sign in.")
                    else:
                        otp = gen_otp()
                        users[r_email.strip()] = {
                            "name": r_name.strip(),
                            "company": r_co.strip(),
                            "password": r_pwd.strip(),
                            "status": "pending",
                            "otp": otp,
                            "registered": datetime.now().strftime("%d %b %Y %H:%M"),
                            "email_limit": 5,
                            "chat_limit": 3
                        }
                        save_users(users)
                        ok, msg = send_gmail(cfg, f"New Business Signup – {r_name.strip()} | Churn Intelligence",
                                             tpl_otp(r_name.strip(), r_email.strip(), otp), recipients=[OWNER_EMAIL])
                        if ok: st.success(f"✅ Registration submitted! {OWNER_NAME} will review and send you an OTP to activate your account.")
                        else: st.success("✅ Request saved."); st.info(f"Email notification failed ({msg}). Contact {OWNER_EMAIL} for next steps.")
                        time.sleep(1)
                        st.session_state.auth_step = "login"
                        st.rerun()

# ----- Main App (only after login) -----
if not st.session_state.logged_in:
    landing_page()
    st.markdown("---")
    show_auth()
    st.stop()

# After login, proceed with the main application (no brand bar at top)
lookup_db = st.session_state.custom_db if st.session_state.custom_db is not None else _default_db

# Simple title after login
st.markdown('<p style="font-family:Syne,sans-serif;font-size:1.85rem;font-weight:800;color:#f1f5f9;margin:14px 0 2px;letter-spacing:-.03em">Strategic Churn & Segment Predictor</p>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#64748b;font-size:.85rem;margin-bottom:18px">Signed in as <strong>{st.session_state.user_name}</strong> ({st.session_state.user_email})</p>', unsafe_allow_html=True)

run_single, search_term, threshold_pct = show_sidebar()

tab_list = ["🔍 Single Scan", "📊 Bulk Scan", "🔔 Alert Settings", "📋 Alert History"]
if st.session_state.is_owner:
    tab_list.append("👥 User Management")
all_tabs = st.tabs(tab_list)
tab1, tab2, tab3, tab4 = all_tabs[0], all_tabs[1], all_tabs[2], all_tabs[3]
tab5 = all_tabs[4] if st.session_state.is_owner else None

# Helper function to enforce user limits
def enforce_limits():
    if st.session_state.is_owner: return (999, 999)
    users = load_users()
    user = users.get(st.session_state.user_email, {})
    email_limit = user.get("email_limit", 5)
    chat_limit = user.get("chat_limit", 3)
    return email_limit, chat_limit

# ----- All the tabs (same as before, no changes needed for content) -----
# TAB 1 — SINGLE SCAN
with tab1:
    if not run_single:
        st.info("👈 Enter a Customer ID or Phone Number in the sidebar and click **Analyse Customer**.")
    elif not search_term.strip():
        st.warning("Please enter a Customer ID or Phone Number.")
    else:
        clean = str(search_term).strip()
        record = pd.DataFrame()
        if "CustomerID" in lookup_db.columns:
            record = lookup_db[lookup_db["CustomerID"].astype(str).str.strip() == clean].copy()
        if record.empty and "Phone_Number" in lookup_db.columns:
            record = lookup_db[lookup_db["Phone_Number"].astype(str).str.strip() == clean].copy()
        if record.empty:
            st.error(f"❌ Customer **{clean}** not found. Make sure you have CustomerID or Phone_Number in your database.")
        else:
            miss = [c for c in all_columns if c not in record.columns]
            if miss: st.error(f"❌ Database missing {len(miss)} model column(s): {', '.join(miss[:6])}"); st.stop()
            st.success("✅ Customer found!")
            st.markdown('<p class="sec-hdr">Customer Profile</p>', unsafe_allow_html=True)
            disp = record.copy()
            if "gender" in disp.columns: disp["gender"] = disp["gender"].replace({1: "Male", 0: "Female"})
            show_cols = [c for c in [tenure_col, charge_col, "gender", "Contract_Month-to-month", "InternetService_Fiber optic", "OnlineSecurity_No", "TechSupport_No", "Partner", "Dependents", "Cluster"] if c in disp.columns]
            st.dataframe(disp[show_cols], use_container_width=True)
            st.divider()
            inp = record[all_columns].copy()
            if "gender" in inp.columns: inp["gender"] = inp["gender"].replace({"Male": 1, "Female": 0}).astype(int)
            prob = float(model.predict_proba(inp)[0][1])
            cluster = int(record["Cluster"].values[0]) if "Cluster" in record.columns else 0
            profile, strategy = cluster_info(cluster)
            factor = top_factor(record.iloc[0])
            ts = datetime.now().strftime("%d %b %Y, %H:%M")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown('<p class="sec-hdr">Churn Risk</p>', unsafe_allow_html=True)
                st.metric("Probability", f"{prob*100:.1f}%")
                st.markdown(risk_badge(prob), unsafe_allow_html=True)
            with c2:
                st.markdown('<p class="sec-hdr">Segment</p>', unsafe_allow_html=True)
                st.info(f"Cluster {cluster} — {profile}")
                st.caption(strategy)
            with c3:
                st.markdown('<p class="sec-hdr">Top Risk Factor</p>', unsafe_allow_html=True)
                st.error(factor)
            st.divider()
            if prob >= cfg["churn_threshold"]:
                st.warning(f"⚠️ **High Risk — {prob*100:.1f}%** exceeds your {threshold_pct}% threshold.")
            else:
                st.success(f"✅ **Low Risk — {prob*100:.1f}%** is below the {threshold_pct}% threshold.")
            html_b = tpl_single(clean, prob, cluster, profile, strategy, factor, ts)
            tg_b = tg_single(clean, prob, cluster, profile, strategy, factor, ts)
            subj = f"{'🚨' if prob>=cfg['churn_threshold'] else '📊'} Churn Scan | {clean} — {prob*100:.0f}% Risk"
            email_ok, email_msg = send_gmail(cfg, subj, html_b)
            tg_ok, tg_msg = send_telegram(cfg, tg_b)
            log_alert({"ts": ts, "channel": "Single Scan", "customer_id": "SINGLE", "phone": clean, "prob": round(prob,4), "status": "sent" if (email_ok or tg_ok) else "no channels", "detail": f"{email_msg} | {tg_msg}"})
            st.markdown("**Notification Status:**")
            n1, n2 = st.columns(2)
            with n1:
                if email_ok: st.success(f"📧 {email_msg}")
                elif cfg.get("emails"): st.error(f"📧 {email_msg}")
                else: st.info("📧 No email recipients — add in Alert Settings.")
            with n2:
                if tg_ok: st.success(f"💬 {tg_msg}")
                elif cfg.get("telegram_chat_ids"): st.error(f"💬 {tg_msg}")
                else: st.info("💬 No Telegram chats — add in Alert Settings.")

# TAB 2 — BULK SCAN (unchanged)
with tab2:
    st.markdown('<p class="sec-hdr">Bulk Customer Scan</p>', unsafe_allow_html=True)
    missing_cols = [c for c in all_columns if c not in lookup_db.columns]
    if missing_cols:
        st.error(f"❌ Active database missing **{len(missing_cols)}** model column(s):")
        st.code(", ".join(missing_cols))
        st.info("Upload the correct preprocessed CSV in the sidebar or revert to the default database.")
        with st.expander("📋 All required columns"): st.write(all_columns)
        st.stop()
    st.write(f"Ready to scan **{len(lookup_db):,}** customers · Threshold: **{threshold_pct}%**")
    bc1, bc2 = st.columns([2, 1])
    run_bulk = bc1.button("🚀 Run Full Scan", use_container_width=True, type="primary")
    send_after = bc2.checkbox("Send alerts after scan", value=True)
    if run_bulk:
        prog = st.progress(0, text="Initialising…")
        results = []
        errors = []
        total = len(lookup_db)
        for idx, row in lookup_db.iterrows():
            try:
                inp = lookup_db.loc[[idx], all_columns].copy()
                if "gender" in inp.columns:
                    inp["gender"] = inp["gender"].replace({"Male": 1, "Female": 0}).astype(int)
                prob = float(model.predict_proba(inp)[0][1])
                cluster = int(row.get("Cluster", 0)) if "Cluster" in lookup_db.columns else 0
                profile, strategy = cluster_info(cluster)
                factor = top_factor(row)
                cust_id = str(row.get("CustomerID", "N/A")) if "CustomerID" in lookup_db.columns else "N/A"
                results.append({
                    "Phone Number": str(row.get("Phone_Number", "N/A")),
                    "CustomerID": cust_id,
                    "Churn %": round(prob*100, 1),
                    "Risk Level": risk_label(prob),
                    "Cluster": cluster,
                    "Segment": profile,
                    "Top Risk Factor": factor,
                    "Action": strategy,
                    "_prob": prob,
                    "_cluster": cluster,
                    "_profile": profile,
                    "_strategy": strategy,
                    "_factor": factor
                })
            except Exception as e:
                errors.append({"Row": idx, "Phone": str(row.get("Phone_Number", "?")), "Error": str(e), "Missing columns": [c for c in all_columns if c not in row.index]})
            done = len(results)+len(errors)
            prog.progress(done/total, text=f"Scanning… {done}/{total}")
        prog.empty()
        if errors:
            with st.expander(f"⚠️ {len(errors)} row(s) skipped"): st.dataframe(pd.DataFrame(errors), use_container_width=True)
        if not results:
            st.error("❌ No valid predictions returned. All rows failed.")
            st.stop()
        df_r = pd.DataFrame(results)
        at_risk = df_r[df_r["_prob"] >= cfg["churn_threshold"]]
        ts = datetime.now().strftime("%d %b %Y, %H:%M")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Scanned", f"{len(df_r):,}")
        m2.metric("At-Risk", f"{len(at_risk):,}", delta=f"{len(at_risk)/len(df_r)*100:.1f}%", delta_color="inverse")
        m3.metric("Critical (≥80%)", f"{len(df_r[df_r['_prob']>=.8]):,}")
        m4.metric("Threshold", f"{threshold_pct}%")
        st.divider()
        DCOLS = ["CustomerID", "Phone Number", "Churn %", "Risk Level", "Cluster", "Segment", "Top Risk Factor", "Action"]
        st.markdown(f"### 🚨 {len(at_risk)} At-Risk Customers")
        if not at_risk.empty:
            st.dataframe(at_risk[DCOLS].sort_values("Churn %", ascending=False).reset_index(drop=True), use_container_width=True)
            st.download_button("⬇️ Download At-Risk CSV", at_risk[DCOLS].to_csv(index=False), "at_risk_customers.csv", "text/csv")
            if send_after:
                rl = [{"phone": r["Phone Number"], "prob": r["_prob"], "cluster": r["_cluster"], "profile": r["_profile"], "strategy": r["_strategy"], "factor": r["_factor"]} for r in at_risk.to_dict("records")]
                html_b = tpl_bulk(rl, cfg["churn_threshold"], ts)
                subj_b = f"📊 Churn Report — {ts} | {len(at_risk)} At-Risk Customers"
                tg_s = (f"📊 <b>Bulk Scan — {ts}</b>\n──────────────────────\n🔍 Scanned: {len(df_r):,}\n🚨 At-Risk ({threshold_pct}%+): <b>{len(at_risk)}</b>\n🔴 Critical: {len(df_r[df_r['_prob']>=.8])}\n🟠 High: {len(df_r[(df_r['_prob']>=.6) & (df_r['_prob']<.8)])}")
                with st.spinner("Sending alerts…"):
                    email_ok, email_msg = send_gmail(cfg, subj_b, html_b)
                    tg_ok, tg_msg = send_telegram(cfg, tg_s)
                a1,a2 = st.columns(2)
                (a1.success if email_ok else a1.warning)(f"📧 {email_msg}")
                (a2.success if tg_ok else a2.warning)(f"💬 {tg_msg}")
                log_alert({"ts": ts, "channel": "Bulk Scan", "customer_id": "BULK", "phone": f"{len(at_risk)} customers", "prob": 0, "status": "sent", "detail": f"{email_msg} | {tg_msg}"})
        else: st.success("✅ All clear — no customers above threshold.")
        with st.expander("📄 Full Scan Results"): st.dataframe(df_r[DCOLS].sort_values("Churn %", ascending=False).reset_index(drop=True), use_container_width=True)

# TAB 3 — ALERT SETTINGS (unchanged)
with tab3:
    st.markdown('<p class="sec-hdr">Gmail Sender Configuration</p>', unsafe_allow_html=True)
    st.caption("This Gmail account sends all alert emails. Requires a Gmail App Password.")
    st.markdown("👉 [How to create a Gmail App Password](https://support.google.com/accounts/answer/185833)")
    g1,g2 = st.columns(2)
    new_gs = g1.text_input("Sender Gmail", value=cfg.get("gmail_sender", ""), placeholder="alerts@gmail.com")
    new_gp = g2.text_input("App Password", value=cfg.get("gmail_app_password", ""), type="password", placeholder="xxxx xxxx xxxx xxxx")
    if st.button("💾 Save Gmail Config"):
        cfg["gmail_sender"] = new_gs.strip()
        cfg["gmail_app_password"] = new_gp.strip()
        save_config(cfg)
        st.success("✅ Saved.")
    st.divider()
    st.markdown('<p class="sec-hdr">Email Recipients</p>', unsafe_allow_html=True)
    email_limit, chat_limit = enforce_limits()
    if not st.session_state.is_owner:
        st.info(f"Your plan allows up to **{email_limit}** email recipients. Contact admin to increase limit.")
    st.caption("Everyone listed here receives alerts after every scan.")
    ne = st.text_input("Add Email", placeholder="team@company.com", key="add_em")
    if st.button("➕ Add Email"):
        if "@" in ne and ne.strip() not in cfg["emails"]:
            if not st.session_state.is_owner and len(cfg["emails"]) >= email_limit:
                st.error(f"❌ You have reached your limit of {email_limit} email recipients. Contact administrator to increase.")
            else:
                cfg["emails"].append(ne.strip())
                save_config(cfg)
                st.success(f"✅ {ne.strip()} added.")
                st.rerun()
        elif ne.strip() in cfg["emails"]: st.warning("Already in list.")
        else: st.error("Invalid email address.")
    for i, em in enumerate(cfg["emails"]):
        c1, c2 = st.columns([6,1])
        c1.write(f"✉️  {em}")
        if c2.button("🗑️", key=f"re{i}"):
            cfg["emails"].remove(em)
            save_config(cfg)
            st.rerun()
    if not cfg["emails"]: st.info("No recipients yet.")
    st.divider()
    st.markdown('<p class="sec-hdr">Telegram Bot</p>', unsafe_allow_html=True)
    st.markdown("1. Telegram → **@BotFather** → `/newbot`\n2. Copy **Bot Token** below\n3. Get **Chat ID** from [@userinfobot](https://t.me/userinfobot)")
    nt = st.text_input("Bot Token", value=cfg.get("telegram_bot_token", ""), type="password", placeholder="123456789:ABCdef...")
    if st.button("💾 Save Token"):
        cfg["telegram_bot_token"] = nt.strip()
        save_config(cfg)
        st.success("✅ Saved.")
    nc = st.text_input("Add Chat ID", placeholder="-1001234567890", key="add_cid")
    if st.button("➕ Add Chat"):
        if nc.strip() and nc.strip() not in cfg["telegram_chat_ids"]:
            if not st.session_state.is_owner and len(cfg["telegram_chat_ids"]) >= chat_limit:
                st.error(f"❌ You have reached your limit of {chat_limit} Telegram chats. Contact administrator.")
            else:
                cfg["telegram_chat_ids"].append(nc.strip())
                save_config(cfg)
                st.success("✅ Added.")
                st.rerun()
    for i, cid in enumerate(cfg["telegram_chat_ids"]):
        c1, c2 = st.columns([6,1])
        c1.write(f"💬  {cid}")
        if c2.button("🗑️", key=f"rc{i}"):
            cfg["telegram_chat_ids"].remove(cid)
            save_config(cfg)
            st.rerun()
    if not cfg["telegram_chat_ids"]: st.info("No Telegram chats yet.")
    st.divider()
    st.markdown('<p class="sec-hdr">Test Alerts</p>', unsafe_allow_html=True)
    t1,t2 = st.columns(2)
    if t1.button("🧪 Test Email", use_container_width=True):
        ok, msg = send_gmail(cfg, "✅ Test — Churn Intelligence", tpl_single("080XXXXXXXX", 0.85, 1, "At-Risk Starter", "Offer Annual Contract discount.", "Month-to-Month Contract", datetime.now().strftime("%d %b %Y, %H:%M")))
        (st.success if ok else st.error)(msg)
    if t2.button("🧪 Test Telegram", use_container_width=True):
        ok, msg = send_telegram(cfg, tg_single("080XXXXXXXX", 0.85, 1, "At-Risk Starter", "Offer Annual Contract discount.", "Month-to-Month Contract", datetime.now().strftime("%d %b %Y, %H:%M")))
        (st.success if ok else st.error)(msg)

# TAB 4 — ALERT HISTORY (unchanged)
with tab4:
    st.markdown('<p class="sec-hdr">Alert History</p>', unsafe_allow_html=True)
    history = load_history()
    if not history:
        st.info("No alerts logged yet. Run a Single Scan or Bulk Scan — history will appear here automatically.")
    else:
        df_h = pd.DataFrame(history[::-1])
        h1,h2,h3 = st.columns(3)
        h1.metric("Total Logged", len(df_h))
        h2.metric("Single Scans", len(df_h[df_h["channel"]=="Single Scan"]))
        h3.metric("Bulk Scans", len(df_h[df_h["channel"]=="Bulk Scan"]))
        st.divider()
        st.dataframe(df_h[["ts","channel","phone","prob","status","detail"]].rename(columns={"ts":"Time","channel":"Channel","phone":"Phone","prob":"Churn Prob","status":"Status","detail":"Detail"}), use_container_width=True)
        st.download_button("⬇️ Export CSV", df_h.to_csv(index=False), "alert_history.csv", "text/csv")
        if st.button("🗑️ Clear History"): save_history([]); st.success("Cleared."); st.rerun()

# TAB 5 — USER MANAGEMENT (with debug OTP view)
if tab5 is not None:
    with tab5:
        st.markdown('<p class="sec-hdr">Company Management</p>', unsafe_allow_html=True)
        st.caption("Approve new companies, set their email/Telegram limits, or remove access.")
        users = load_users()
        if not users:
            st.info("No registered companies yet.")
        else:
            for email, u in list(users.items()):
                if email == OWNER_EMAIL: continue
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    col1.markdown(f"**{u.get('name', '?')}**")
                    col1.caption(f"{email} · {u.get('company', '?')} · {u.get('registered', '?')}")
                    status = u.get("status", "pending")
                    col2.write("🟢 Approved" if status == "approved" else "⏳ Pending")
                    if status == "pending":
                        col2.code(f"OTP: {u.get('otp', 'N/A')}")
                        if col3.button("✅ Approve", key=f"ap_{email}", help="Approve company"):
                            users[email]["status"] = "approved"
                            save_users(users)
                            st.success(f"✅ {email} approved.")
                            st.rerun()
                    email_limit = u.get("email_limit", 5)
                    chat_limit = u.get("chat_limit", 3)
                    new_email_limit = col3.number_input("Email limit", value=email_limit, min_value=0, max_value=100, step=1, key=f"el_{email}")
                    new_chat_limit = col4.number_input("Telegram limit", value=chat_limit, min_value=0, max_value=20, step=1, key=f"cl_{email}")
                    if new_email_limit != email_limit or new_chat_limit != chat_limit:
                        users[email]["email_limit"] = new_email_limit
                        users[email]["chat_limit"] = new_chat_limit
                        save_users(users)
                        st.success(f"Limits updated for {email}")
                    if col4.button("🗑️ Remove", key=f"rm_{email}", help="Delete company"):
                        del users[email]
                        save_users(users)
                        st.rerun()
        st.divider()
        st.markdown('<p class="sec-hdr">Add Company Manually</p>', unsafe_allow_html=True)
        mn = st.text_input("Name", key="man_n", placeholder="Jane Smith")
        me = st.text_input("Email", key="man_e", placeholder="company@example.com")
        mc = st.text_input("Company", key="man_c", placeholder="Acme Telecom")
        mp = st.text_input("Password", key="man_p", type="password", placeholder="Temporary password")
        mel = st.number_input("Email Limit", min_value=0, max_value=100, value=5)
        mcl = st.number_input("Telegram Chat Limit", min_value=0, max_value=20, value=3)
        if st.button("➕ Add & Approve", type="primary"):
            if mn.strip() and me.strip() and mp.strip():
                users[me.strip()] = {
                    "name": mn.strip(),
                    "company": mc.strip(),
                    "password": mp.strip(),
                    "status": "approved",
                    "otp": "",
                    "registered": datetime.now().strftime("%d %b %Y %H:%M"),
                    "email_limit": mel,
                    "chat_limit": mcl
                }
                save_users(users)
                st.success(f"✅ {mn.strip()} added and approved.")
                st.rerun()
            else:
                st.error("Please fill Name, Email and Password.")
        
        # Debug: Show pending OTPs (admin only)
        with st.expander("🔧 Debug: Pending OTPs (admin only)"):
            pending = {email: u.get("otp") for email, u in users.items() if u.get("status") == "pending"}
            if pending:
                st.json(pending)
            else:
                st.info("No pending accounts.")

# # ----- Footer for logged-in pages -----
st.caption("© 2025 Churn Intelligence by Donatus Victor. All rights reserved.")