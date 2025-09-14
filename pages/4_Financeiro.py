import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from db_management import (
    get_all_rentals, 
    get_all_customers, 
    get_all_equipments, 
    is_authenticated, 
    logout,
    update_rental_in_db
)

st.set_page_config(page_title="ConcRental - Financeiro", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("Financeiro")

# --- Load Data from DB ---
user_id = st.session_state.user_id
rentals_df = get_all_rentals(user_id)
customers_df = get_all_customers(user_id)
equipment_df = get_all_equipments(user_id)

# --- KPIs Section ---
st.header("Visão Geral Financeira")

if rentals_df.empty:
    st.info("Nenhum dado financeiro para exibir. Crie um aluguel para começar.")
else:
    rentals_df['end_date'] = pd.to_datetime(rentals_df['end_date'])
    rentals_df['start_date'] = pd.to_datetime(rentals_df['start_date'])
    
    today = datetime.now()

    caixa_df = rentals_df[rentals_df['payment_status'] != 'Em Aberto']
    receber_df = rentals_df[rentals_df['payment_status'] == 'Em Aberto']

    caixa_mes = caixa_df[caixa_df['end_date'].dt.month == today.month]['valor'].sum()
    receber_mes = receber_df[receber_df['end_date'].dt.month == today.month]['valor'].sum()

    caixa_ano = caixa_df[caixa_df['end_date'].dt.year == today.year]['valor'].sum()
    receber_ano = receber_df[receber_df['end_date'].dt.year == today.year]['valor'].sum()

    caixa_total = caixa_df['valor'].sum()
    receber_total = receber_df['valor'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Caixa (Este Mês)", f"R$ {caixa_mes:.2f}")
    col2.metric("Caixa (Este Ano)", f"R$ {caixa_ano:.2f}")
    col3.metric("Caixa (Total)", f"R$ {caixa_total:.2f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("A Receber (Este Mês)", f"R$ {receber_mes:.2f}")
    col2.metric("A Receber (Este Ano)", f"R$ {receber_ano:.2f}")
    col3.metric("A Receber (Total)", f"R$ {receber_total:.2f}")

st.divider()

# --- Detailed List Section ---
st.header("Todos os Lançamentos")

if rentals_df.empty or customers_df.empty or equipment_df.empty:
    st.info("Nenhum lançamento para exibir.")
else:
    all_rentals_merged = rentals_df.merge(customers_df, on="customer_id").merge(equipment_df, on="equipment_id")

    for index, row in all_rentals_merged.iterrows():
        border_color = "#FF4B4B" if row['payment_status'] == 'Em Aberto' else "#28A745"
        
        with st.container():
            st.markdown(f"<div style='border-left: 5px solid {border_color}; padding-left: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**Cliente:** {row['full_name']}")
                st.markdown(f"**Equipamento:** {row['name']}")
                st.caption(f"Período: {pd.to_datetime(row['start_date']).strftime('%d/%m')} a {pd.to_datetime(row['end_date']).strftime('%d/%m/%Y')}")
            
            with c2:
                st.markdown(f"**Valor**")
                st.markdown(f"R$ {row['valor']:.2f}")

            with c3:
                payment_options = ["Em Aberto", "Cartão", "Dinheiro", "Parcelado", "Pix"]
                selected_payment = st.selectbox(
                    "Status Pagamento", 
                    options=payment_options, 
                    index=payment_options.index(row['payment_status']),
                    key=f"payment_finance_{row['rental_id']}",
                    label_visibility="collapsed"
                )
                if selected_payment != row['payment_status']:
                    update_rental_in_db(row['rental_id'], 'payment_status', selected_payment)
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)