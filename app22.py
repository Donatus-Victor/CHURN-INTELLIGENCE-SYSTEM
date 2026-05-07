import streamlit as st
import joblib
import pandas as pd
import smtplib
import json, os, random, string, time
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

st.set_page_config(page_title="Churn Intelligence System | Donatus Victor",page_icon="📡",layout="wide",initial_sidebar_state="expanded")

OWNER_EMAIL    = "donatusvictor76@gmail.com"
OWNER_PASSWORD = "donatus2024"
OWNER_NAME     = "Donatus Victor"
OWNER_TITLE    = "Business Data Scientist"
OWNER_PHONE    = "+2348137790780"
OWNER_LI       = "https://www.linkedin.com/in/donatusvictor"

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
</style>""", unsafe_allow_html=True)

CONFIG_FILE="alert_config.json"; HISTORY_FILE="alert_history.json"; USERS_FILE="users.json"

def _load(p,d):
    if os.path.exists(p):
        try:
            with open(p) as f: return json.load(f)
        except: pass
    return d
def _save(p,d):
    with open(p,"w") as f: json.dump(d,f,indent=2)
def load_config():
    d={"emails":[],"telegram_bot_token":"","telegram_chat_ids":[],"gmail_sender":"","gmail_app_password":"","churn_threshold":0.70}
    d.update(_load(CONFIG_FILE,{})); return d
def save_config(c): _save(CONFIG_FILE,c)
def load_history(): return _load(HISTORY_FILE,[])
def save_history(h): _save(HISTORY_FILE,h[-500:])
def load_users(): return _load(USERS_FILE,{})
def save_users(u): _save(USERS_FILE,u)
def log_alert(e):
    h=load_history(); h.append(e); save_history(h)
def gen_otp(): return "".join(random.choices(string.digits,k=6))

def send_gmail(cfg,subj,html,recipients=None):
    targets=recipients if recipients is not None else cfg.get("emails",[])
    if not cfg.get("gmail_sender") or not cfg.get("gmail_app_password"): return False,"Gmail not configured in Alert Settings."
    if not targets: return False,"No recipient emails configured."
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=15) as s:
            s.login(cfg["gmail_sender"],cfg["gmail_app_password"])
            for r in targets:
                msg=MIMEMultipart("alternative"); msg["Subject"]=subj
                msg["From"]=f"Churn Intelligence <{cfg['gmail_sender']}>"; msg["To"]=r
                msg.attach(MIMEText(html,"html")); s.sendmail(cfg["gmail_sender"],r,msg.as_string())
        return True,f"Email sent to {len(targets)} recipient(s)."
    except smtplib.SMTPAuthenticationError: return False,"Gmail auth failed. Check App Password in Alert Settings."
    except Exception as e: return False,f"Email error: {e}"

def send_telegram(cfg,message):
    token=cfg.get("telegram_bot_token","").strip(); chats=cfg.get("telegram_chat_ids",[])
    if not token: return False,"Telegram token not set."
    if not chats: return False,"No Telegram chats configured."
    url=f"https://api.telegram.org/bot{token}/sendMessage"; sent=0
    for cid in chats:
        try:
            r=requests.post(url,json={"chat_id":cid.strip(),"text":message,"parse_mode":"HTML"},timeout=10)
            if r.ok: sent+=1
        except: pass
    return (sent>0),f"Telegram sent to {sent}/{len(chats)} chat(s)."

def _rc(p): return "#ff4757" if p>=.8 else "#ffa502" if p>=.6 else "#eccc68" if p>=.4 else "#2ed573"

def tpl_single(phone,prob,cluster,profile,strategy,factor,ts):
    h="🚨 High Risk Alert" if prob>=.7 else "📊 Churn Scan Result"
    rc=_rc(prob)
    return f"""<div style="font-family:'Segoe UI',sans-serif;max-width:560px;margin:auto;background:#f8fafc;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
  <div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;">
    <p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">Churn Intelligence System</p>
    <h1 style="color:#fff;margin:0;font-size:20px;">{h}</h1>
    <p style="color:#94a3b8;font-size:12px;margin:5px 0 0">{ts}</p>
  </div>
  <div style="padding:22px 26px;">
    <table style="width:100%;border-collapse:collapse;">
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px;width:150px">Phone</td><td style="font-weight:600;color:#1e293b">{phone}</td></tr>
      <tr><td style="padding:7px 0;color:#64748b;font-size:13px">Churn Risk</td><td style="background:{rc};color:#fff;padding:3px 12px;border-radius:20px;font-weight:700">{prob*100:.1f}%</span></td></tr>
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
        return (
            f"<tr style='border-bottom:1px solid #e2e8f0'>"
            f"<td style='padding:8px;font-size:12px'>{r['phone']}</td>"
            f"<td style='padding:8px;font-size:12px;font-weight:700;color:{color}'>{r['prob']*100:.1f}%</td>"
            f"<td style='padding:8px;font-size:12px'>{r['profile']}</td>"
            f"<td style='padding:8px;font-size:12px;color:#64748b'>{r['factor']}</td>"
            f"<td style='padding:8px;font-size:12px'>{r['strategy']}</td>"
            f"</tr>"
        )
    rows = "".join([row_html(r) for r in sorted(lst, key=lambda x: x["prob"], reverse=True)])
    return f"""<div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;">
    <p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">Bulk Scan · {ts}</p>
    <h1 style="color:#fff;margin:0;font-size:20px;">📊 Churn Intelligence Report</h1>
    <p style="color:#94a3b8;font-size:13px;margin:7px 0 0">{len(lst)} customers flagged above {threshold*100:.0f}% threshold</p>
  </div>
  <div style="padding:22px 26px;overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;min-width:580px">
      <thead><tr style="background:#f1f5f9"><th style="padding:9px 8px;font-size:11px;text-align:left;color:#64748b">PHONE</th><th style="padding:9px 8px;font-size:11px;text-align:left;color:#64748b">CHURN %</th><th style="padding:9px 8px;font-size:11px;text-align:left;color:#64748b">SEGMENT</th><th style="padding:9px 8px;font-size:11px;text-align:left;color:#64748b">TOP FACTOR</th><th style="padding:9px 8px;font-size:11px;text-align:left;color:#64748b">ACTION</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:20px">Churn Intelligence · <strong>{OWNER_NAME}</strong> · {OWNER_PHONE}</p>
  </div>
</div>"""

def tpl_otp(name,user_email,otp):
    return f"""<div style="font-family:'Segoe UI',sans-serif;max-width:480px;margin:auto;background:#f8fafc;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
  <div style="background:linear-gradient(135deg,#0d1117,#0f2027);padding:22px 26px;"><p style="color:#00ffb4;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 4px">New Access Request</p><h1 style="color:#fff;margin:0;font-size:20px;">Approve New User</h1></div>
  <div style="padding:22px 26px;"><p style="color:#1e293b;font-size:14px"><strong>{name}</strong> ({user_email}) is requesting access.</p>
    <div style="background:#f0fdf4;border:2px solid #00ffb4;border-radius:10px;padding:16px;text-align:center;margin:20px 0">
      <p style="margin:0;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:1px">OTP for {name}</p>
      <p style="margin:8px 0 0;font-family:monospace;font-size:2.4rem;font-weight:800;color:#0d1117;letter-spacing:.25em">{otp}</p>
    </div>
    <p style="color:#64748b;font-size:13px">Share this with {name} to grant access. Ignore if unrecognised.</p>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:16px">Churn Intelligence · {OWNER_NAME}</p></div></div>"""

def tg_single(phone,prob,cluster,profile,strategy,factor,ts):
    i="🔴" if prob>=.8 else "🟠" if prob>=.6 else "🟡" if prob>=.4 else "🟢"
    return f"📡 <b>CHURN SCAN — {ts}</b>\n──────────────────────\n{i} <b>Risk: {prob*100:.1f}%</b>\n\n📞 Phone: <code>{phone}</code>\n📌 Cluster {cluster} — {profile}\n⚠️ Top Factor: {factor}\n\n💡 <b>Action:</b> {strategy}\n──────────────────────\nBy <b>{OWNER_NAME}</b> | {OWNER_PHONE}"

def cluster_info(c):
    return {0:("Basic Traditionalist","Upsell Digital Bundles and online security add-ons."),1:("At-Risk Starter","Offer Annual Contract discounts immediately."),2:("Loyal Power User","Enrol in Premium Loyalty Programme.")}.get(int(c),("Unknown","Manual review required."))

def top_factor(row):
    for col,lbl in [("Contract_Month-to-month","Month-to-Month Contract"),("InternetService_Fiber optic","Fiber Optic Internet"),("OnlineSecurity_No","No Online Security"),("TechSupport_No","No Tech Support")]:
        if col in row.index and row[col]==1: return lbl
    return "Usage pattern anomaly"

def risk_label(p): return "CRITICAL" if p>=.8 else "HIGH" if p>=.6 else "MEDIUM" if p>=.4 else "LOW"
def risk_badge(p):
    cls={"CRITICAL":"risk-critical","HIGH":"risk-high","MEDIUM":"risk-medium","LOW":"risk-low"}[risk_label(p)]
    return f'<span class="{cls}">{risk_label(p)}</span>'

@st.cache_resource(show_spinner="Loading intelligence models…")
def load_models():
    mdl=joblib.load("churn_model.pkl"); km=joblib.load("segmentation_model.pkl"); sc=joblib.load("scaler.pkl")
    db=pd.read_csv("customer_lookup_database.csv",dtype={"Phone_Number":str})
    return mdl,km,sc,db

try:
    model,kmeans,scaler,_default_db=load_models()
    all_columns=list(model.get_booster().feature_names)
    tenure_col=next((c for c in all_columns if "tenure" in c.lower()),all_columns[0])
    charge_col=next((c for c in all_columns if "charge" in c.lower()),all_columns[1])
except Exception as e:
    st.error(f"Could not load models or customer_lookup_database.csv: {e}"); st.stop()

for k,v in [("cfg",None),("logged_in",False),("user_email",""),("user_name",""),("is_owner",False),("custom_db",None),("auth_step","login")]:
    if k not in st.session_state: st.session_state[k]=v
if st.session_state.cfg is None: st.session_state.cfg=load_config()
cfg=st.session_state.cfg

st.sidebar.markdown(f"""<div style="position:fixed;bottom:0;left:0;width:260px;background:#0d1117;border-top:1px solid #1e293b;border-right:1px solid #1e293b;padding:12px 16px;z-index:9999;">
  <p style="font-family:'Syne',sans-serif;font-weight:700;color:#f1f5f9;font-size:.88rem;margin:0 0 1px">{OWNER_NAME}</p>
  <p style="color:#00ffb4;font-size:.71rem;letter-spacing:.04em;margin:0 0 8px">{OWNER_TITLE}</p>
  <a href="tel:{OWNER_PHONE}" style="display:flex;align-items:center;gap:6px;color:#64748b;font-size:.74rem;text-decoration:none;margin-bottom:4px">📞 {OWNER_PHONE}</a>
  <a href="{OWNER_LI}" target="_blank" style="display:flex;align-items:center;gap:6px;color:#64748b;font-size:.74rem;text-decoration:none;margin-bottom:4px">💼 LinkedIn</a>
  <a href="mailto:{OWNER_EMAIL}" style="display:flex;align-items:center;gap:6px;color:#64748b;font-size:.74rem;text-decoration:none">✉️ {OWNER_EMAIL}</a>
</div>""", unsafe_allow_html=True)

# ── AUTH ──────────────────────────────────────────────────────────────
def show_auth():
    st.markdown("""<div style="text-align:center;margin:50px 0 28px">
      <p style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#00ffb4;margin:0">📡 Churn Intelligence</p>
      <p style="color:#64748b;font-size:.88rem;margin:6px 0 0">Powered by Donatus Victor · Restricted Access</p></div>""", unsafe_allow_html=True)
    col=st.columns([1,1.1,1])[1]
    users=load_users()
    with col:
        if st.session_state.auth_step=="login":
            with st.container(border=True):
                st.markdown("#### 🔐 Sign In")
                email=st.text_input("Email",key="li_em",placeholder="your@email.com")
                pwd=st.text_input("Password",key="li_pw",type="password",placeholder="Your password")
                ca,cb=st.columns(2)
                do_login=ca.button("Sign In",use_container_width=True,type="primary")
                do_reg=cb.button("Request Access",use_container_width=True)
                if do_login:
                    em=email.strip(); pw=pwd.strip()
                    if em==OWNER_EMAIL and pw==OWNER_PASSWORD:
                        st.session_state.update({"logged_in":True,"user_email":OWNER_EMAIL,"user_name":OWNER_NAME,"is_owner":True})
                        st.rerun()
                    else:
                        u=users.get(em)
                        if u is None: st.error("❌ Email not registered. Click 'Request Access' first.")
                        elif u.get("status")!="approved": st.warning("⏳ Account pending. Use OTP below to activate.")
                        elif u.get("password","")!=pw: st.error("❌ Incorrect password.")
                        else:
                            st.session_state.update({"logged_in":True,"user_email":em,"user_name":u.get("name","User"),"is_owner":False})
                            st.rerun()
                if do_reg:
                    st.session_state.auth_step="register"; st.rerun()
            with st.expander("🔑 Have an OTP? Activate your account here"):
                oe=st.text_input("Your Email",key="otp_em",placeholder="your@email.com")
                ov=st.text_input("OTP Code",key="otp_val",placeholder="6-digit code",max_chars=6)
                if st.button("Activate Account",use_container_width=True):
                    u=users.get(oe.strip())
                    if u and u.get("otp")==ov.strip():
                        u["status"]="approved"; save_users(users); st.success("✅ Activated! You can now sign in.")
                    else: st.error("❌ Wrong email or OTP. Contact Donatus Victor.")
        elif st.session_state.auth_step=="register":
            with st.container(border=True):
                st.markdown("#### 📝 Request Access")
                st.caption(f"Submit your details. **{OWNER_NAME}** will send you an OTP to activate your account.")
                r_name=st.text_input("Full Name",key="rg_name",placeholder="Jane Smith")
                r_email=st.text_input("Work Email",key="rg_em",placeholder="jane@company.com")
                r_co=st.text_input("Company",key="rg_co",placeholder="Acme Telecom Ltd")
                r_pwd=st.text_input("Choose Password",key="rg_pw",type="password",placeholder="Min 6 characters")
                r_pwd2=st.text_input("Confirm Password",key="rg_pw2",type="password",placeholder="Repeat password")
                ca,cb=st.columns(2)
                do_sub=ca.button("Submit Request",use_container_width=True,type="primary")
                do_back=cb.button("← Back",use_container_width=True)
                if do_back:
                    st.session_state.auth_step="login"; st.rerun()
                if do_sub:
                    if not r_name.strip(): st.error("Please enter your full name.")
                    elif not r_email.strip() or "@" not in r_email: st.error("Please enter a valid email address.")
                    elif not r_co.strip(): st.error("Please enter your company name.")
                    elif not r_pwd.strip(): st.error("Please choose a password.")
                    elif len(r_pwd.strip())<6: st.error("Password must be at least 6 characters.")
                    elif r_pwd.strip()!=r_pwd2.strip(): st.error("Passwords do not match.")
                    elif r_email.strip()==OWNER_EMAIL: st.error("That email is the admin account. Sign in directly.")
                    elif r_email.strip() in users and users[r_email.strip()].get("status")=="approved": st.warning("Already registered. Please sign in.")
                    else:
                        otp=gen_otp()
                        users[r_email.strip()]={"name":r_name.strip(),"company":r_co.strip(),"password":r_pwd.strip(),"status":"pending","otp":otp,"registered":datetime.now().strftime("%d %b %Y %H:%M")}
                        save_users(users)
                        ok,msg=send_gmail(cfg,f"New Access Request — {r_name.strip()} | Churn Intelligence",tpl_otp(r_name.strip(),r_email.strip(),otp),recipients=[OWNER_EMAIL])
                        if ok: st.success(f"✅ Request submitted! {OWNER_NAME} will review and send you an OTP.")
                        else: st.success("✅ Request saved."); st.info(f"Email notification failed ({msg}). Contact {OWNER_EMAIL} for your OTP.")
                        time.sleep(1); st.session_state.auth_step="login"; st.rerun()

if not st.session_state.logged_in:
    show_auth(); st.stop()

# ── MAIN APP ──────────────────────────────────────────────────────────
lookup_db=st.session_state.custom_db if st.session_state.custom_db is not None else _default_db

st.markdown(f"""<div class="brand-bar"><div>
  <p class="brand-title">📡 CHURN INTELLIGENCE SYSTEM</p>
  <p class="brand-name">{OWNER_NAME}</p><p class="brand-sub">{OWNER_TITLE}</p></div>
  <div class="brand-buttons">
    <a class="brand-btn btn-phone" href="tel:{OWNER_PHONE}">📞 Phone</a>
    <a class="brand-btn btn-linkedin" href="{OWNER_LI}" target="_blank">💼 LinkedIn</a>
    <a class="brand-btn btn-email" href="mailto:{OWNER_EMAIL}">✉️ Email</a>
  </div></div>""", unsafe_allow_html=True)
st.markdown('<p style="font-family:Syne,sans-serif;font-size:1.85rem;font-weight:800;color:#f1f5f9;margin:14px 0 2px;letter-spacing:-.03em">Strategic Churn & Segment Predictor</p>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#64748b;font-size:.85rem;margin-bottom:18px">Predict who will leave · Why · What to do &nbsp;|&nbsp; Signed in as <strong>{st.session_state.user_name}</strong></p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🔍 Customer Lookup")
    search_phone=st.text_input("Phone Number",placeholder="e.g. 08012345678")
    run_single=st.button("🔎 Analyse Customer",use_container_width=True)
    st.divider()
    threshold_pct=st.slider("🎚️ Alert Threshold (%)",40,95,int(cfg.get("churn_threshold",0.70)*100),5)
    cfg["churn_threshold"]=threshold_pct/100; save_config(cfg)
    st.divider()
    st.markdown("### 🗄️ Connect Your Database")
    st.caption("Upload a preprocessed customer CSV (all model feature columns + Phone_Number).")
    uploaded=st.file_uploader("Upload CSV",type=["csv"],key="db_up")
    if uploaded:
        try:
            tmp=pd.read_csv(uploaded,dtype={"Phone_Number":str}); miss=[c for c in all_columns if c not in tmp.columns]
            if miss: st.error(f"Missing {len(miss)} column(s): {', '.join(miss[:4])}…")
            else: st.session_state.custom_db=tmp; lookup_db=tmp; st.success(f"✅ {len(tmp):,} customers loaded.")
        except Exception as e: st.error(f"Read error: {e}")
    if st.session_state.custom_db is not None:
        if st.button("🔄 Revert to Default DB",use_container_width=True): st.session_state.custom_db=None; st.rerun()
    st.divider()
    st.caption(f"📊 {len(lookup_db):,} customers in database")
    if st.button("🚪 Sign Out",use_container_width=True):
        for k,v in [("logged_in",False),("user_email",""),("user_name",""),("is_owner",False),("auth_step","login")]: st.session_state[k]=v
        st.rerun()

tab_list=["🔍 Single Scan","📊 Bulk Scan","🔔 Alert Settings","📋 Alert History"]
if st.session_state.is_owner: tab_list.append("👥 User Management")
all_tabs=st.tabs(tab_list)
tab1,tab2,tab3,tab4=all_tabs[0],all_tabs[1],all_tabs[2],all_tabs[3]
tab5=all_tabs[4] if st.session_state.is_owner else None

# TAB 1 — SINGLE SCAN
with tab1:
    if not run_single:
        st.info("👈 Enter a phone number in the sidebar and click **Analyse Customer** to begin.")
    elif not search_phone.strip():
        st.warning("Please enter a phone number in the sidebar.")
    else:
        clean=str(search_phone).strip()
        record=lookup_db[lookup_db["Phone_Number"].astype(str).str.strip()==clean].copy()
        if record.empty:
            st.error(f"❌ Phone number **{clean}** not found in the database.")
            st.info("Make sure the number format matches customer_lookup_database.csv")
        else:
            miss=[c for c in all_columns if c not in record.columns]
            if miss: st.error(f"❌ Database missing {len(miss)} model column(s): {', '.join(miss[:6])}"); st.stop()
            st.success("✅ Customer found!")
            st.markdown('<p class="sec-hdr">Customer Profile</p>', unsafe_allow_html=True)
            disp=record.copy()
            if "gender" in disp.columns: disp["gender"]=disp["gender"].replace({1:"Male",0:"Female"})
            show_cols=[c for c in [tenure_col,charge_col,"gender","Contract_Month-to-month","InternetService_Fiber optic","OnlineSecurity_No","TechSupport_No","Partner","Dependents","Cluster"] if c in disp.columns]
            st.dataframe(disp[show_cols],use_container_width=True); st.divider()
            inp=record[all_columns].copy()
            if "gender" in inp.columns: inp["gender"]=inp["gender"].replace({"Male":1,"Female":0}).astype(int)
            prob=float(model.predict_proba(inp)[0][1])
            cluster=int(record["Cluster"].values[0]) if "Cluster" in record.columns else 0
            profile,strategy=cluster_info(cluster); factor=top_factor(record.iloc[0])
            ts=datetime.now().strftime("%d %b %Y, %H:%M")
            c1,c2,c3=st.columns(3)
            with c1:
                st.markdown('<p class="sec-hdr">Churn Risk</p>', unsafe_allow_html=True)
                st.metric("Probability",f"{prob*100:.1f}%"); st.markdown(risk_badge(prob),unsafe_allow_html=True)
            with c2:
                st.markdown('<p class="sec-hdr">Segment</p>', unsafe_allow_html=True)
                st.info(f"Cluster {cluster} — {profile}"); st.caption(strategy)
            with c3:
                st.markdown('<p class="sec-hdr">Top Risk Factor</p>', unsafe_allow_html=True)
                st.error(factor)
            st.divider()
            if prob>=cfg["churn_threshold"]: st.warning(f"⚠️ **High Risk — {prob*100:.1f}%** exceeds your {threshold_pct}% threshold.")
            else: st.success(f"✅ **Low Risk — {prob*100:.1f}%** is below the {threshold_pct}% threshold.")
            html_b=tpl_single(clean,prob,cluster,profile,strategy,factor,ts)
            tg_b=tg_single(clean,prob,cluster,profile,strategy,factor,ts)
            subj=f"{'🚨' if prob>=cfg['churn_threshold'] else '📊'} Churn Scan | {clean} — {prob*100:.0f}% Risk"
            email_ok,email_msg=send_gmail(cfg,subj,html_b)
            tg_ok,tg_msg=send_telegram(cfg,tg_b)
            log_alert({"ts":ts,"channel":"Single Scan","customer_id":"SINGLE","phone":clean,"prob":round(prob,4),"status":"sent" if (email_ok or tg_ok) else "no channels configured","detail":f"{email_msg} | {tg_msg}"})
            st.markdown("**Notification Status:**")
            n1,n2=st.columns(2)
            with n1:
                if email_ok: st.success(f"📧 {email_msg}")
                elif cfg.get("emails"): st.error(f"📧 {email_msg}")
                else: st.info("📧 No email recipients — add in Alert Settings.")
            with n2:
                if tg_ok: st.success(f"💬 {tg_msg}")
                elif cfg.get("telegram_chat_ids"): st.error(f"💬 {tg_msg}")
                else: st.info("💬 No Telegram chats — add in Alert Settings.")

# TAB 2 — BULK SCAN
with tab2:
    st.markdown('<p class="sec-hdr">Bulk Customer Scan</p>', unsafe_allow_html=True)
    missing_cols=[c for c in all_columns if c not in lookup_db.columns]
    if missing_cols:
        st.error(f"❌ Active database missing **{len(missing_cols)}** model column(s):")
        st.code(", ".join(missing_cols))
        st.info("Upload the correct preprocessed CSV in the sidebar or revert to the default database.")
        with st.expander("📋 All required columns"): st.write(all_columns)
        st.stop()
    st.write(f"Ready to scan **{len(lookup_db):,}** customers · Threshold: **{threshold_pct}%**")
    bc1,bc2=st.columns([2,1])
    run_bulk=bc1.button("🚀 Run Full Scan",use_container_width=True,type="primary")
    send_after=bc2.checkbox("Send alerts after scan",value=True)
    if run_bulk:
        prog=st.progress(0,text="Initialising…"); results=[]; errors=[]; total=len(lookup_db)
        for idx,row in lookup_db.iterrows():
            try:
                inp=row[all_columns].copy().to_frame().T
                if "gender" in inp.columns: inp["gender"]=inp["gender"].replace({"Male":1,"Female":0}).astype(int)
                prob=float(model.predict_proba(inp)[0][1]); cluster=int(row.get("Cluster",0))
                profile,strategy=cluster_info(cluster); factor=top_factor(row)
                results.append({"Phone Number":str(row.get("Phone_Number","N/A")),"Churn %":round(prob*100,1),"Risk Level":risk_label(prob),"Cluster":cluster,"Segment":profile,"Top Risk Factor":factor,"Action":strategy,"_prob":prob,"_cluster":cluster,"_profile":profile,"_strategy":strategy,"_factor":factor})
            except Exception as e: errors.append({"Row":idx,"Phone":str(row.get("Phone_Number","?")),"Error":str(e)})
            done=len(results)+len(errors); prog.progress(done/total,text=f"Scanning… {done}/{total}")
        prog.empty()
        if errors:
            with st.expander(f"⚠️ {len(errors)} row(s) skipped"): st.dataframe(pd.DataFrame(errors),use_container_width=True)
        if not results:
            st.error("❌ No valid predictions returned. All rows failed.")
            st.info("Check that your CSV columns match the model's expected columns. See the debug expander above."); st.stop()
        df_r=pd.DataFrame(results); at_risk=df_r[df_r["_prob"]>=cfg["churn_threshold"]]; ts=datetime.now().strftime("%d %b %Y, %H:%M")
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Total Scanned",f"{len(df_r):,}"); m2.metric("At-Risk",f"{len(at_risk):,}",delta=f"{len(at_risk)/len(df_r)*100:.1f}%",delta_color="inverse")
        m3.metric("Critical (≥80%)",f"{len(df_r[df_r['_prob']>=.8]):,}"); m4.metric("Threshold",f"{threshold_pct}%")
        st.divider()
        DCOLS=["Phone Number","Churn %","Risk Level","Cluster","Segment","Top Risk Factor","Action"]
        st.markdown(f"### 🚨 {len(at_risk)} At-Risk Customers")
        if not at_risk.empty:
            st.dataframe(at_risk[DCOLS].sort_values("Churn %",ascending=False).reset_index(drop=True),use_container_width=True)
            st.download_button("⬇️ Download At-Risk CSV",at_risk[DCOLS].to_csv(index=False),"at_risk_customers.csv","text/csv")
            if send_after:
                rl=[{"phone":r["Phone Number"],"prob":r["_prob"],"cluster":r["_cluster"],"profile":r["_profile"],"strategy":r["_strategy"],"factor":r["_factor"]} for r in at_risk.to_dict("records")]
                html_b=tpl_bulk(rl,cfg["churn_threshold"],ts); subj_b=f"📊 Churn Report — {ts} | {len(at_risk)} At-Risk Customers"
                
                tg_s = (f"📊 <b>Bulk Scan — {ts}</b>\n──────────────────────\n🔍 Scanned: {len(df_r):,}\n🚨 At-Risk ({threshold_pct}%+): <b>{len(at_risk)}</b>\n🔴 Critical: {len(df_r[df_r['_prob']>=.8])}\n🟠 High: {len(df_r[(df_r['_prob']>=.6) & (df_r['_prob']<.8)])}")
                
                with st.spinner("Sending alerts…"):
                    email_ok,email_msg=send_gmail(cfg,subj_b,html_b); tg_ok,tg_msg=send_telegram(cfg,tg_s)
                a1,a2=st.columns(2)
                (a1.success if email_ok else a1.warning)(f"📧 {email_msg}"); (a2.success if tg_ok else a2.warning)(f"💬 {tg_msg}")
                log_alert({"ts":ts,"channel":"Bulk Scan","customer_id":"BULK","phone":f"{len(at_risk)} customers","prob":0,"status":"sent","detail":f"{email_msg} | {tg_msg}"})
        else: st.success("✅ All clear — no customers above threshold.")
        with st.expander("📄 Full Scan Results"): st.dataframe(df_r[DCOLS].sort_values("Churn %",ascending=False).reset_index(drop=True),use_container_width=True)

# TAB 3 — ALERT SETTINGS
with tab3:
    st.markdown('<p class="sec-hdr">Gmail Sender Configuration</p>', unsafe_allow_html=True)
    st.caption("This Gmail account sends all alert emails. Requires a Gmail App Password.")
    st.markdown("👉 [How to create a Gmail App Password](https://support.google.com/accounts/answer/185833)")
    g1,g2=st.columns(2)
    new_gs=g1.text_input("Sender Gmail",value=cfg.get("gmail_sender",""),placeholder="alerts@gmail.com")
    new_gp=g2.text_input("App Password",value=cfg.get("gmail_app_password",""),type="password",placeholder="xxxx xxxx xxxx xxxx")
    if st.button("💾 Save Gmail Config"):
        cfg["gmail_sender"]=new_gs.strip(); cfg["gmail_app_password"]=new_gp.strip(); save_config(cfg); st.success("✅ Saved.")
    st.divider()
    st.markdown('<p class="sec-hdr">Email Recipients</p>', unsafe_allow_html=True)
    st.caption("Everyone listed here receives alerts after every scan.")
    ne=st.text_input("Add Email",placeholder="team@company.com",key="add_em")
    if st.button("➕ Add Email"):
        if "@" in ne and ne.strip() not in cfg["emails"]:
            cfg["emails"].append(ne.strip()); save_config(cfg); st.success(f"✅ {ne.strip()} added."); st.rerun()
        elif ne.strip() in cfg["emails"]: st.warning("Already in the list.")
        else: st.error("Invalid email address.")
    for i,em in enumerate(cfg["emails"]):
        c1,c2=st.columns([6,1]); c1.write(f"✉️  {em}")
        if c2.button("🗑️",key=f"re{i}"): cfg["emails"].remove(em); save_config(cfg); st.rerun()
    if not cfg["emails"]: st.info("No recipients yet.")
    st.divider()
    st.markdown('<p class="sec-hdr">Telegram Bot</p>', unsafe_allow_html=True)
    st.markdown("1. Telegram → **@BotFather** → `/newbot`\n2. Copy **Bot Token** below\n3. Get **Chat ID** from [@userinfobot](https://t.me/userinfobot)")
    nt=st.text_input("Bot Token",value=cfg.get("telegram_bot_token",""),type="password",placeholder="123456789:ABCdef...")
    if st.button("💾 Save Token"): cfg["telegram_bot_token"]=nt.strip(); save_config(cfg); st.success("✅ Saved.")
    nc=st.text_input("Add Chat ID",placeholder="-1001234567890",key="add_cid")
    if st.button("➕ Add Chat"):
        if nc.strip() and nc.strip() not in cfg["telegram_chat_ids"]:
            cfg["telegram_chat_ids"].append(nc.strip()); save_config(cfg); st.success("✅ Added."); st.rerun()
    for i,cid in enumerate(cfg["telegram_chat_ids"]):
        c1,c2=st.columns([6,1]); c1.write(f"💬  {cid}")
        if c2.button("🗑️",key=f"rc{i}"): cfg["telegram_chat_ids"].remove(cid); save_config(cfg); st.rerun()
    if not cfg["telegram_chat_ids"]: st.info("No Telegram chats yet.")
    st.divider()
    st.markdown('<p class="sec-hdr">Test Alerts</p>', unsafe_allow_html=True)
    t1,t2=st.columns(2)
    if t1.button("🧪 Test Email",use_container_width=True):
        ok,msg=send_gmail(cfg,"✅ Test — Churn Intelligence",tpl_single("080XXXXXXXX",0.85,1,"At-Risk Starter","Offer Annual Contract discount.","Month-to-Month Contract",datetime.now().strftime("%d %b %Y, %H:%M")))
        (st.success if ok else st.error)(msg)
    if t2.button("🧪 Test Telegram",use_container_width=True):
        ok,msg=send_telegram(cfg,tg_single("080XXXXXXXX",0.85,1,"At-Risk Starter","Offer Annual Contract discount.","Month-to-Month Contract",datetime.now().strftime("%d %b %Y, %H:%M")))
        (st.success if ok else st.error)(msg)

# TAB 4 — ALERT HISTORY
with tab4:
    st.markdown('<p class="sec-hdr">Alert History</p>', unsafe_allow_html=True)
    history=load_history()
    if not history:
        st.info("No alerts logged yet. Run a Single Scan or Bulk Scan — history will appear here automatically.")
    else:
        df_h=pd.DataFrame(history[::-1])
        h1,h2,h3=st.columns(3)
        h1.metric("Total Logged",len(df_h)); h2.metric("Single Scans",len(df_h[df_h["channel"]=="Single Scan"])); h3.metric("Bulk Scans",len(df_h[df_h["channel"]=="Bulk Scan"]))
        st.divider()
        st.dataframe(df_h[["ts","channel","phone","prob","status","detail"]].rename(columns={"ts":"Time","channel":"Channel","phone":"Phone","prob":"Churn Prob","status":"Status","detail":"Detail"}),use_container_width=True)
        st.download_button("⬇️ Export CSV",df_h.to_csv(index=False),"alert_history.csv","text/csv")
        if st.button("🗑️ Clear History"): save_history([]); st.success("Cleared."); st.rerun()

# TAB 5 — USER MANAGEMENT
if tab5 is not None:
    with tab5:
        st.markdown('<p class="sec-hdr">User Management</p>', unsafe_allow_html=True)
        st.caption("Only you (the admin) can see this panel.")
        users=load_users()
        if not users: st.info("No registered users yet.")
        else:
            for email,u in list(users.items()):
                with st.container(border=True):
                    c1,c2,c3=st.columns([3,2,1])
                    c1.markdown(f"**{u.get('name','?')}**"); c1.caption(f"{email} · {u.get('company','?')} · {u.get('registered','?')}")
                    status=u.get("status","pending"); c2.write("🟢 Approved" if status=="approved" else "⏳ Pending")
                    if status=="pending":
                        c2.code(f"OTP: {u.get('otp','N/A')}")
                        if c3.button("✅",key=f"ap_{email}",help="Approve"): users[email]["status"]="approved"; save_users(users); st.success(f"✅ {email} approved."); st.rerun()
                    if c3.button("🗑️",key=f"rm_{email}",help="Remove"): del users[email]; save_users(users); st.rerun()
        st.divider()
        st.markdown('<p class="sec-hdr">Add User Manually</p>', unsafe_allow_html=True)
        mn=st.text_input("Name",key="man_n",placeholder="Jane Smith"); me=st.text_input("Email",key="man_e",placeholder="jane@company.com")
        mc=st.text_input("Company",key="man_c",placeholder="Acme Telecom"); mp=st.text_input("Password",key="man_p",type="password",placeholder="Temporary password")
        if st.button("➕ Add & Approve",type="primary"):
            if mn.strip() and me.strip() and mp.strip():
                users[me.strip()]={"name":mn.strip(),"company":mc.strip(),"password":mp.strip(),"status":"approved","otp":"","registered":datetime.now().strftime("%d %b %Y %H:%M")}
                save_users(users); st.success(f"✅ {mn.strip()} added and approved."); st.rerun()
            else: st.error("Please fill in Name, Email and Password.")