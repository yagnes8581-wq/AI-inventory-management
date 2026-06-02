import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3
import time
from datetime import datetime
import hashlib

# --- PAGE CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Inventory Analytics", page_icon="📦", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
        }
        
        [data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.8) !important;
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        div[role="radiogroup"] > label > div:first-of-type { display: none !important; }
        div[role="radiogroup"] > label { 
            padding: 12px 20px !important; 
            background: rgba(255, 255, 255, 0.03); 
            border-radius: 12px !important; 
            margin-bottom: 8px; 
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid transparent;
        }
        div[role="radiogroup"] > label:hover { 
            background: rgba(255, 255, 255, 0.08) !important; 
            transform: translateX(5px);
            border-color: rgba(255,255,255,0.1);
        }
        div[role="radiogroup"] > label p { font-size: 15px !important; font-weight: 500 !important; margin: 0 !important; color: #e2e8f0; }
        
        [data-testid="metric-container"] {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            backdrop-filter: blur(5px);
        }
        [data-testid="metric-container"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(96, 165, 250, 0.3);
        }
        [data-testid="metric-container"] label {
            color: #94a3b8 !important;
            font-size: 14px !important;
        }
        [data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-weight: 700 !important;
        }
        
        .stButton>button {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
        }
        .stButton>button:hover {
            box-shadow: 0 8px 15px -3px rgba(59, 130, 246, 0.4);
            transform: translateY(-2px);
            color: white;
        }
        
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800 !important;
            letter-spacing: -0.5px;
        }
        
        .stTextInput>div>div>input, .stNumberInput>div>div>input {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #f8fafc;
        }
        .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 1px #3b82f6;
        }
        
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_level' not in st.session_state:
    st.session_state.user_level = None
if 'username' not in st.session_state:
    st.session_state.username = None

# --- SECURITY UTILS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- DATABASE SETUP ---
DB_NAME = 'inventory_erp_secure.db' 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (Product_ID TEXT PRIMARY KEY, Category TEXT, Unit_Cost REAL, Current_Stock INTEGER, Lead_Time_Days INTEGER, Base_Monthly_Demand INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historical_sales (Product_ID TEXT, Month INTEGER, Units_Sold INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (Supplier_ID TEXT PRIMARY KEY, Name TEXT, Reliability_Score REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (Order_ID TEXT PRIMARY KEY, Product_ID TEXT, Supplier_ID TEXT, Quantity INTEGER, Status TEXT, Order_Date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (Username TEXT PRIMARY KEY, Password_Hash TEXT, Role TEXT)''')
    
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        # Master Admin Account
        admin_pass = hash_password("admin123")
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", admin_pass, "Admin"))
        
        # Seed default inventory
        np.random.seed(42)
        inv_data = [(f'PROD_{i:03d}', np.random.choice(['Electronics', 'Apparel', 'Groceries', 'Home Decor']), round(np.random.uniform(5, 100), 2), int(np.random.randint(5, 150)), int(np.random.randint(3, 15)), int(np.random.randint(50, 300))) for i in range(1, 51)]
        c.executemany('INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?)', inv_data)
        
        hist_data = []
        for row in inv_data:
            prod_id = row[0]
            base_sales = row[5]
            for month in range(1, 7):
                fluctuation = int(base_sales * np.random.uniform(0.8, 1.2))
                hist_data.append((prod_id, month, fluctuation))
        c.executemany('INSERT INTO historical_sales VALUES (?, ?, ?)', hist_data)
        
        suppliers_data = [('SUP_01', 'Global Tech Distributors', 98.5), ('SUP_02', 'Prime Apparel Co.', 85.0), ('SUP_03', 'Fresh Farms Wholesale', 92.3), ('SUP_04', 'Urban Living Decor', 88.7)]
        c.executemany('INSERT INTO suppliers VALUES (?, ?, ?)', suppliers_data)
        
    conn.commit()
    conn.close()

init_db()

# --- PREDICTIVE ANALYTICS ENGINE ---
def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    sales_df = pd.read_sql_query("SELECT * FROM historical_sales", conn)
    conn.close()
    
    # Empty state handler just in case the database is wiped clean
    if df.empty:
        return pd.DataFrame(columns=['Product_ID', 'Category', 'Unit_Cost', 'Current_Stock', 'Lead_Time_Days', 'Base_Monthly_Demand', 'Predicted_Next_Month_Demand', 'Predicted_Revenue', 'Cumulative_Revenue', 'Revenue_Percentage', 'ABC_Class', 'Daily_Demand_Forecast', 'Safety_Stock', 'Reorder_Point', 'Status', 'Priority_Level'])
    
    predictions = []
    for index, row in df.iterrows():
        prod_id = row['Product_ID']
        prod_sales = sales_df[sales_df['Product_ID'] == prod_id].sort_values('Month')
        if prod_sales.empty:
            # Defensive programming: If a new item is uploaded via CSV and has no history, use its base demand
            predictions.append(row['Base_Monthly_Demand'])
        else:
            ema = prod_sales['Units_Sold'].ewm(span=3, adjust=False).mean().iloc[-1]
            predictions.append(int(ema))
        
    df['Predicted_Next_Month_Demand'] = predictions
    df['Predicted_Revenue'] = df['Unit_Cost'] * df['Predicted_Next_Month_Demand']
    df = df.sort_values(by='Predicted_Revenue', ascending=False).reset_index(drop=True)
    df['Cumulative_Revenue'] = df['Predicted_Revenue'].cumsum()
    df['Revenue_Percentage'] = (df['Cumulative_Revenue'] / df['Predicted_Revenue'].sum()) * 100
    df['ABC_Class'] = df['Revenue_Percentage'].apply(lambda x: 'Class A' if x <= 80 else ('Class B' if x <= 95 else 'Class C'))
    df['Daily_Demand_Forecast'] = df['Predicted_Next_Month_Demand'] / 30
    df['Safety_Stock'] = np.round(df['Daily_Demand_Forecast'] * 3).astype(int)
    df['Reorder_Point'] = np.round((df['Daily_Demand_Forecast'] * df['Lead_Time_Days']) + df['Safety_Stock']).astype(int)
    df['Status'] = np.where(df['Current_Stock'] <= df['Reorder_Point'], 'Reorder Required', 'Stock OK')
    
    def get_priority_badge(abc_class):
        if abc_class == 'Class A': return '🅰️ High Priority'
        elif abc_class == 'Class B': return '🅱️ Moderate'
        else: return '🅲️ Low Priority'
    df.insert(0, 'Priority_Level', df['ABC_Class'].apply(get_priority_badge))
    
    return df

df = load_data()

# ==========================================
# 🚀 SECURE LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<div style='text-align: center; padding-top: 8vh; padding-bottom: 2vh;'><h1 style='font-size: 4rem; font-weight: 800; margin-bottom: 0;'>Enterprise Inventory System</h1><p style='color: #94a3b8; font-size: 1.2rem; margin-top: 10px;'>Authorized Personnel Only</p></div>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("Secure Login")
            input_username = st.text_input("Username")
            input_password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Log In", use_container_width=True)
            
            if submit_login:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT Password_Hash, Role FROM users WHERE Username = ?", (input_username,))
                result = c.fetchone()
                conn.close()
                
                if result:
                    db_password_hash = result[0]
                    user_role = result[1]
                    if hash_password(input_password) == db_password_hash:
                        st.session_state.logged_in = True
                        st.session_state.user_level = user_role
                        st.session_state.username = input_username
                        st.rerun()
                    else:
                        st.error("❌ Incorrect Password.")
                else:
                    st.error("❌ Username not found.")

# ==========================================
# 📊 MAIN APPLICATION
# ==========================================
else:
    st.sidebar.title("📦 Navigation")
    
    menu_options = ["Dashboard Overview", "Inventory Database", "Manage Stock", "🚚 Supply Chain & Orders"]
    if st.session_state.user_level == 'Admin':
        menu_options.append("🔐 Admin Console")
        
    menu = st.sidebar.radio("", menu_options)
    st.sidebar.markdown("---")
    
    if st.session_state.user_level in ['Experienced', 'Admin']:
        with st.sidebar.expander("ℹ️ Help & Guide"):
            st.markdown("**Class A:** Top 80% Revenue.\n**Class B:** Next 15% Revenue.\n**Class C:** Bottom 5% Revenue.")
            
    st.sidebar.caption(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_level})")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_level = None
        st.session_state.username = None
        st.rerun()

    # --- DASHBOARD VIEW ---
    if menu == "Dashboard Overview":
        st.title("📊 AI-Powered Inventory Dashboard")
        st.caption("Powered by Exponential Smoothing Demand Forecasting")
        
        if not df.empty:
            out_of_stock = df[df['Current_Stock'] <= 0]
            if not out_of_stock.empty:
                class_a_stockouts = out_of_stock[out_of_stock['ABC_Class'] == 'Class A']
                if not class_a_stockouts.empty:
                    st.error(f"🚨 CRITICAL REVENUE LOSS: {len(class_a_stockouts)} Class A item(s) are completely out of stock! Restock immediately.", icon="🚨")
                else:
                    st.warning(f"⚠️ Warning: {len(out_of_stock)} item(s) have zero stock remaining.", icon="⚠️")
            
            if st.session_state.user_level == 'Novice':
                with st.expander("ℹ️ How to read this dashboard", expanded=True):
                    st.markdown("**1. Action Required:** If > 0, check the Priority Reorder List below.\n**2. ABC Classification:** 🅰️ Class A = High Priority (Never hit 0). 🅱️ Class B = Moderate. 🅲️ Class C = Low Priority.")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Products", len(df))
            col2.metric("Predicted Revenue (30 Days)", f"₹{df['Predicted_Revenue'].sum():,.2f}")
            col3.metric("Action Required", len(df[df['Status'] == 'Reorder Required']))
            col4.metric("Class A Items", len(df[df['ABC_Class'] == 'Class A']))
            
            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                fig_bar = px.bar(df.groupby('ABC_Class')['Predicted_Revenue'].sum().reset_index(), x='ABC_Class', y='Predicted_Revenue', color='ABC_Class', color_discrete_sequence=['#60A5FA', '#34D399', '#F87171'], title="Predicted Revenue by Class")
                fig_bar.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Inter', color='#e2e8f0'), title_font=dict(size=18, family='Inter', color='#f8fafc'), margin=dict(t=50, l=0, r=0, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
            with col_chart2:
                fig_pie = px.pie(df['Status'].value_counts().reset_index(), names='Status', values='count', hole=0.6, color='Status', color_discrete_map={'Stock OK': '#34D399', 'Reorder Required': '#F87171'}, title="Current Stock Health")
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Inter', color='#e2e8f0'), title_font=dict(size=18, family='Inter', color='#f8fafc'), margin=dict(t=50, l=0, r=0, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("⚠️ Priority Reorder List")
            st.dataframe(df[df['Status'] == 'Reorder Required'][['Product_ID', 'Category', 'Priority_Level', 'Current_Stock', 'Predicted_Next_Month_Demand', 'Reorder_Point']], use_container_width=True, hide_index=True)
        else:
            st.info("Database is currently empty. Please ask an Admin to upload inventory data.")

    # --- INVENTORY DATABASE VIEW ---
    elif menu == "Inventory Database":
        st.title("🗄️ Master Inventory Database")
        if not df.empty:
            display_cols = ['Product_ID', 'Category', 'Priority_Level', 'Current_Stock', 'Reorder_Point', 'Predicted_Next_Month_Demand', 'Unit_Cost']
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No data available.")

    # --- MANAGE STOCK (SEARCHABLE) ---
    elif menu == "Manage Stock":
        st.title("🔄 Manage Inventory Levels")
        if not df.empty:
            search_query = st.text_input("🔍 Search by Product ID or Category")
            if search_query:
                filtered_df = df[df['Product_ID'].str.contains(search_query, case=False) | df['Category'].str.contains(search_query, case=False)]
            else:
                filtered_df = df
                
            if filtered_df.empty:
                st.warning("No products found matching your search.")
            else:
                with st.form("update_stock_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        product_to_update = st.selectbox("Select Product ID", filtered_df['Product_ID'].sort_values())
                    with col2:
                        current_val = int(df[df['Product_ID'] == product_to_update]['Current_Stock'].iloc[0])
                        new_stock = st.number_input("New Stock Level", min_value=0, step=1, value=current_val)
                        
                    if st.form_submit_button(label="Update inventory"):
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("UPDATE inventory SET Current_Stock = ? WHERE Product_ID = ?", (new_stock, product_to_update))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Inventory successfully updated! {product_to_update} is now set to {new_stock} units.")
                        time.sleep(1.5)
                        st.rerun()
        else:
            st.info("No products available to update.")

    # --- SUPPLY CHAIN & ORDERS ---
    elif menu == "🚚 Supply Chain & Orders":
        st.title("🚚 Supply Chain & Order Management")
        if not df.empty:
            conn = sqlite3.connect(DB_NAME)
            suppliers_df = pd.read_sql_query("SELECT * FROM suppliers", conn)
            
            st.subheader("Generate Purchase Order")
            reorder_items = df[df['Status'] == 'Reorder Required']
            if reorder_items.empty:
                st.success("All stock is healthy! No purchase orders required at this time.")
            else:
                with st.form("po_form"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        selected_item = st.selectbox("Select Item to Order", reorder_items['Product_ID'])
                    with col2:
                        selected_supplier = st.selectbox("Select Supplier", suppliers_df['Name'])
                    with col3:
                        suggested_qty = int(reorder_items[reorder_items['Product_ID'] == selected_item]['Predicted_Next_Month_Demand'].iloc[0])
                        order_qty = st.number_input("Order Quantity", min_value=1, value=suggested_qty)
                    
                    if st.form_submit_button("Submit Purchase Order"):
                        order_id = f"PO-{int(time.time())}" 
                        supplier_id = suppliers_df[suppliers_df['Name'] == selected_supplier]['Supplier_ID'].iloc[0]
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        c = conn.cursor()
                        c.execute("INSERT INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?)", (order_id, selected_item, supplier_id, order_qty, "Pending", current_time))
                        conn.commit()
                        st.success(f"✅ Purchase Order {order_id} generated successfully!")
                        time.sleep(1)
                        st.rerun()

            st.markdown("---")
            st.subheader("Active Orders")
            orders_df = pd.read_sql_query("SELECT * FROM purchase_orders", conn)
            
            if not orders_df.empty:
                st.dataframe(orders_df, use_container_width=True, hide_index=True)
                
                st.markdown("### Process Deliveries")
                with st.form("receive_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        active_orders = orders_df[orders_df['Status'] != 'Received']['Order_ID']
                        if not active_orders.empty:
                            order_to_update = st.selectbox("Select Order to Update", active_orders)
                        else:
                            st.info("No pending or shipped orders.")
                            order_to_update = None
                    with col2:
                        new_status = st.selectbox("Update Status To:", ["Shipped", "Received"])
                        
                    if st.form_submit_button("Update Status") and order_to_update:
                        c = conn.cursor()
                        c.execute("UPDATE purchase_orders SET Status = ? WHERE Order_ID = ?", (new_status, order_to_update))
                        
                        if new_status == "Received":
                            received_item = orders_df[orders_df['Order_ID'] == order_to_update]['Product_ID'].iloc[0]
                            received_qty = int(orders_df[orders_df['Order_ID'] == order_to_update]['Quantity'].iloc[0])
                            c.execute("UPDATE inventory SET Current_Stock = Current_Stock + ? WHERE Product_ID = ?", (received_qty, received_item))
                            st.success(f"📦 Order Received! Added {received_qty} units of {received_item} to database.")
                        else:
                            st.success(f"🚚 Order {order_to_update} status updated to {new_status}.")
                        
                        conn.commit()
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.info("No active purchase orders found in the system.")
            conn.close()
        else:
            st.info("Please set up inventory data first.")

    # --- 🔐 ADMIN CONSOLE (USERS & DATA MIGRATION) ---
    elif menu == "🔐 Admin Console" and st.session_state.user_level == 'Admin':
        st.title("🔐 Admin Console")
        
        tab1, tab2 = st.tabs(["👥 User Management", "📥 Data Migration"])
        
        # TAB 1: User Management
        with tab1:
            st.markdown("Create and manage employee access. Passwords are cryptographically secured using SHA-256.")
            conn = sqlite3.connect(DB_NAME)
            users_df = pd.read_sql_query("SELECT Username, Role FROM users", conn)
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            st.subheader("Grant Access to New User")
            with st.form("add_user_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_username = st.text_input("New Username (No spaces)")
                with col2:
                    new_password = st.text_input("Temporary Password", type="password")
                with col3:
                    new_role = st.selectbox("Account Role", ["Novice", "Experienced", "Admin"])
                    
                if st.form_submit_button("Create User Account"):
                    if new_username and new_password:
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE Username = ?", (new_username,))
                        if c.fetchone():
                            st.error("❌ Username already exists.")
                        else:
                            secure_hash = hash_password(new_password)
                            c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_username, secure_hash, new_role))
                            conn.commit()
                            st.success(f"✅ User '{new_username}' created successfully!")
                            time.sleep(1.5)
                            st.rerun()
                    else:
                        st.warning("Please fill out all fields.")
            conn.close()
            
        # TAB 2: CSV Data Migration
        with tab2:
            st.markdown("### Bulk Upload Inventory")
            st.markdown("Onboard a new client by uploading their existing inventory via CSV.")
            
            # Generate the template for download
            template_df = pd.DataFrame(columns=['Product_ID', 'Category', 'Unit_Cost', 'Current_Stock', 'Lead_Time_Days', 'Base_Monthly_Demand'])
            st.download_button(
                label="📄 Download Blank CSV Template",
                data=template_df.to_csv(index=False).encode('utf-8'),
                file_name='inventory_template.csv',
                mime='text/csv'
            )
            
            st.markdown("---")
            uploaded_file = st.file_uploader("Upload Completed CSV Template", type=['csv'])
            
            if uploaded_file is not None:
                try:
                    new_inventory_df = pd.read_csv(uploaded_file)
                    
                    # Basic validation
                    if list(new_inventory_df.columns) == list(template_df.columns):
                        if st.button("🚀 Execute Database Injection"):
                            conn = sqlite3.connect(DB_NAME)
                            new_inventory_df.to_sql('inventory', conn, if_exists='append', index=False)
                            conn.commit()
                            conn.close()
                            st.success(f"✅ Successfully imported {len(new_inventory_df)} new products into the database!")
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.error("❌ Column mismatch. Please use the exact template provided above.")
                except Exception as e:
                    st.error(f"Error reading file: {e}")