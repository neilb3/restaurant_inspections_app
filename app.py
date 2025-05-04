import streamlit as st

# 0) Page config — must be first Streamlit command
st.set_page_config(
    page_title="Restaurant Inspections App",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sqlite3
import pandas as pd
import hashlib

# 1) Database connection (cached)
@st.cache_resource
def get_connection():
    return sqlite3.connect("restaurant_inspections.db", check_same_thread=False)

conn = get_connection()

# 2) Auth helpers
def init_user_table():
    conn.execute("""
      CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
      )
    """)
    conn.commit()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def check_credentials(u: str, pw: str) -> bool:
    row = conn.execute("SELECT password FROM users WHERE username = ?", (u,)).fetchone()
    return bool(row and row[0] == hash_pw(pw))

init_user_table()

# 3) Auth screens (centered narrow)
def signup_page():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.header("🔐 Sign Up")
        u = st.text_input("Username", key="su_user")
        p = st.text_input("Password", type="password", key="su_pass")
        if st.button("Create account"):
            if not u or not p:
                st.error("Both fields required.")
            elif conn.execute("SELECT 1 FROM users WHERE username = ?", (u,)).fetchone():
                st.error("Username already taken.")
            else:
                conn.execute("INSERT INTO users(username,password) VALUES(?,?)", (u, hash_pw(p)))
                conn.commit()
                st.success("Account created! Switch to Log In.")

def login_page():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.header("🔑 Log In")
        u = st.text_input("Username", key="li_user")
        p = st.text_input("Password", type="password", key="li_pass")
        if st.button("Log In"):
            if check_credentials(u, p):
                st.session_state.logged_in = True
                st.session_state.user = u
                st.success(f"Welcome, {u}!")
            else:
                st.error("Invalid credentials.")

# 4) Session state init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# 5) Authentication guard
if not st.session_state.logged_in:
    st.sidebar.header("Account")
    choice = st.sidebar.radio("Select", ["Log In", "Sign Up"])
    if choice == "Sign Up":
        signup_page()
    else:
        login_page()
    st.stop()

# 6) Post-login sidebar
st.sidebar.write(f"👤 Logged in as **{st.session_state.user}**")
if st.sidebar.button("Log Out"):
    st.session_state.logged_in = False
    st.stop()

# 7) Main controls: table selector ABOVE action
st.sidebar.header("Controls")
tables = ["establishment", "employee", "inspection", "violation"]
selected_table = st.sidebar.selectbox("Select table", tables)
action = st.sidebar.selectbox("Action", ["Home", "Read", "Create", "Update", "Delete", "Show Visualizations"])

# 8) Home (centered)
if action == "Home":
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🍽️ Restaurant Inspection Management")
        st.markdown("**Rohan Bankala & Neil Bhutada**")
        st.subheader("Purpose & Motivation")
        st.write("""
        The purpose of this project is to design a comprehensive restaurant inspection management 
        system that enables regulatory bodies to efficiently monitor public health compliance across 
        food establishments. Health inspection data is often collected in unorganized systems that lack 
        relational structure, limiting analysis of patterns in violations, inspector performance, and 
        establishment risk levels. This project integrates a SQLite database with structured CSV datasets 
        to provide a foundation for querying, maintaining, and analyzing inspection records. Through 
        the addition of CRUD functionality and data visualizations, the system supports meaningful 
        insights into food safety trends and enhances data-driven decision-making for inspection 
        planning and public health strategy.
        """)
        st.subheader("Data Source")
        st.write("""
        The project uses a publicly available restaurant inspection dataset, composed of multiple 
        interconnected CSV files including establishment, employee, inspection, and violation data. These 
        files collectively contain critical information such as establishment demographics, inspector 
        assignments, inspection outcomes, and violation details. The structured nature of this dataset 
        supports relational modeling and is ideal for exploring patterns in food safety compliance, 
        inspector workloads, and risk-level distributions across geographic and organizational 
        segments.
        """)

# 9) Read (full-width)
elif action == "Read":
    st.header(f"All records in `{selected_table}`")
    df = pd.read_sql(f"SELECT * FROM {selected_table}", conn)
    st.dataframe(df, height=700, use_container_width=True)

# 10) Create / Update / Delete (centered)
elif action in ["Create", "Update", "Delete"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        df = pd.read_sql(f"SELECT * FROM {selected_table}", conn)
        pk = df.columns[0]

        if action == "Create":
            st.header(f"Create new record in `{selected_table}`")
            inputs = {}
            for col, dt in zip(df.columns, df.dtypes):
                if col == pk: continue
                if dt == "int64":
                    inputs[col] = st.number_input(col, step=1, value=0)
                elif dt == "float64":
                    inputs[col] = st.number_input(col, value=0.0)
                else:
                    inputs[col] = st.text_input(col)
            if st.button("Insert"):
                cols = ", ".join(inputs)
                qs   = ", ".join("?" for _ in inputs)
                conn.execute(
                    f"INSERT INTO {selected_table} ({cols}) VALUES ({qs})",
                    tuple(inputs.values())
                )
                conn.commit()
                st.success("✅ Record inserted!")

        elif action == "Update":
            st.header(f"Update record in `{selected_table}`")
            rid = st.selectbox(f"Choose {pk}", df[pk].tolist())
            record = df[df[pk] == rid].iloc[0]
            updates = {}
            for col, dt in zip(df.columns, df.dtypes):
                if col == pk: continue
                if dt == "int64":
                    updates[col] = st.number_input(col, int(record[col]), step=1)
                elif dt == "float64":
                    updates[col] = st.number_input(col, value=float(record[col]))
                else:
                    updates[col] = st.text_input(col, value=str(record[col]))
            if st.button("Save changes"):
                clause = ", ".join(f"{c}=?" for c in updates)
                conn.execute(
                    f"UPDATE {selected_table} SET {clause} WHERE {pk} = ?",
                    (*updates.values(), rid)
                )
                conn.commit()
                st.success("✅ Record updated!")

        else:  # Delete
            st.header(f"Delete record from `{selected_table}`")
            rid = st.selectbox(f"Choose {pk}", df[pk].tolist())
            if st.button("Delete"):
                conn.execute(
                    f"DELETE FROM {selected_table} WHERE {pk} = ?", (rid,)
                )
                conn.commit()
                st.success("✅ Record deleted!")

# 11) Show Visualizations (full-width)
elif action == "Show Visualizations":
    st.header("📊 Data Visualizations")

    # 1) Monthly Inspection Volume
    df1 = pd.read_sql(
        "SELECT inspection_date, COUNT(*) AS cnt FROM inspection GROUP BY inspection_date",
        conn
    )
    df1["inspection_date"] = pd.to_datetime(df1["inspection_date"])
    df1m = df1.set_index("inspection_date").resample("M").sum().reset_index()
    spec1 = {
      "mark": {"type": "line", "point": True, "tooltip": True},
      "encoding": {
        "x": {"field": "inspection_date", "type": "temporal", "title": "Month"},
        "y": {"field": "cnt", "type": "quantitative", "title": "Inspections"}
      }
    }
    st.subheader("1. Monthly Inspection Volume")
    st.vega_lite_chart(df1m, spec1, use_container_width=True)

    # 2) Top 10 Violation Types
    df2 = pd.read_sql(
        "SELECT point_id, COUNT(*) AS cnt FROM violation GROUP BY point_id ORDER BY cnt DESC LIMIT 10",
        conn
    )
    spec2 = {
      "mark": {"type": "bar", "tooltip": True},
      "encoding": {
        "x": {"field": "point_id", "type": "nominal", "title": "Violation Code"},
        "y": {"field": "cnt", "type": "quantitative", "title": "Count"},
        "color": {"field": "cnt", "type": "quantitative"}
      }
    }
    st.subheader("2. Top 10 Violation Types")
    st.vega_lite_chart(df2, spec2, use_container_width=True)

    # 3) Top 10 Active Inspectors
    df3 = pd.read_sql(
        "SELECT employee_id, COUNT(*) AS cnt FROM inspection GROUP BY employee_id ORDER BY cnt DESC LIMIT 10",
        conn
    )
    spec3 = {
      "mark": {"type": "bar", "tooltip": True},
      "encoding": {
        "x": {"field": "employee_id", "type": "nominal", "title": "Inspector ID"},
        "y": {"field": "cnt", "type": "quantitative", "title": "Inspections"},
        "color": {"field": "cnt", "type": "quantitative"}
      }
    }
    st.subheader("3. Top 10 Active Inspectors")
    st.vega_lite_chart(df3, spec3, use_container_width=True)

    # 4) Top 10 Establishments by Total Fines
    df4 = pd.read_sql(
        "SELECT license_no, SUM(fine) AS total FROM violation "
        "JOIN inspection USING(inspection_id) GROUP BY license_no "
        "ORDER BY total DESC LIMIT 10",
        conn
    )
    spec4 = {
      "mark": {"type": "bar", "tooltip": True},
      "encoding": {
        "x": {"field": "license_no", "type": "nominal", "title": "License No"},
        "y": {"field": "total", "type": "quantitative", "title": "Total Fines ($)"},
        "color": {"field": "total", "type": "quantitative"}
      }
    }
    st.subheader("4. Top 10 Establishments by Total Fines")
    st.vega_lite_chart(df4, spec4, use_container_width=True)

    # 5) Risk Level Distribution
    df5 = pd.read_sql(
        "SELECT risk_level, COUNT(*) AS cnt FROM establishment GROUP BY risk_level",
        conn
    )
    df5["risk_level"] = df5["risk_level"].astype(str)
    spec5 = {
      "mark": {"type": "arc", "innerRadius": 50, "tooltip": True},
      "encoding": {
        "theta": {"field": "cnt", "type": "quantitative"},
        "color": {"field": "risk_level", "type": "nominal"},
        "tooltip": [
            {"field": "risk_level", "type": "nominal"},
            {"field": "cnt", "type": "quantitative"}
        ]
      }
    }
    st.subheader("5. Risk Level Distribution")
    st.vega_lite_chart(df5, spec5, use_container_width=True)
