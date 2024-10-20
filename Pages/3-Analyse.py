import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
import numpy as np 
from datetime import datetime, timedelta
import pytz
import ta
from Scripts.mp_support_resist import *

def fetch_stock_data(ticker : str, duration : int, interval : str):
    # Obtenir la date actuelle
    end_date = datetime.today()

    # Calculer la date de début
    start_date = end_date - timedelta(days=duration) if duration else None

    # Télécharger les données
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval)

    return data

def fetch_stock_data(ticker : str, duration : int, interval : str):
    # Obtenir la date actuelle
    end_date = datetime.today()

    # Calculer la date de début
    start_date = end_date - timedelta(days=duration) if duration else None

    # Télécharger les données
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval)

    return data


def process_data(data: pd.DataFrame):
    # Convertir l'index en DatetimeIndex si nécessaire
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    # S'assurer que les informations de fuseau horaire sont bien présentes
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize("UTC")

    # Réinitialiser l'index pour que la colonne de date soit accessible comme colonne ordinaire
    data.reset_index(inplace=True)
    
    # Renommer la colonne 'Date' en 'Datetime' (si applicable)
    if 'Date' in data.columns:
        data.rename(columns={"Date": "Datetime"}, inplace=True)

    return data

def calculate_metrics(data: pd.DataFrame):
    last_close = data["Close"].iloc[-1]
    prev_close = data["Close"].iloc[0]

    change = last_close - prev_close
    pct_change = (change / prev_close) * 100

    high = data["High"].max()
    low = data["Low"].min()
    volume = data["Volume"].sum()
    
    return last_close, change, pct_change, high, low, volume

def support_resistance(data: pd.DataFrame, lookback : int):

    levels = support_resistance_levels(data, lookback, first_w=1.0, atr_mult=3.0)

    data['sr_signal'] = sr_penetration_signal(data, levels)
    data['log_ret'] = np.log(data['Close']).diff().shift(-1)
    data['sr_return'] = data['sr_signal'] * data['log_ret']

    long_trades, short_trades = get_trades_from_signal(data, data['sr_signal'].to_numpy())

    return data, long_trades, short_trades


st.set_page_config(layout = "wide")
st.title("Analyse technique de la bourse")

st.sidebar.header("Paramètres des variables")
df = pd.read_excel("./Python/Data/Cac40.xlsx")

society = st.sidebar.selectbox("Entreprise", df["Nom Entreprise"])
time_period = st.sidebar.selectbox("Période", ["1d","5d","1mo","3mo","6mo","1y","2y","max"])
chart_type = st.sidebar.selectbox("Type de graph.", ["Candlestick", "Line"])
indicators = st.sidebar.multiselect("Indicateurs", ["Support & Résistance", "RSI", "DMI", "SMA_20", "Bande de Bollinger"])

# Mapping des périodes à la durée en jours et aux intervalles
period_mapping = {
    "1d": (1, "1m"),
    "5d": (5, "30m"),
    "1mo": (30, "1d"),
    "3mo": (90, "1d"),
    "6mo": (190, "1d"),
    "1y": (365, "1d"),
    "2y": (730, "5d"),
    "max": (None, "1wk") 
}

try:
    duration, interval = period_mapping[time_period]

    ticker = df[df["Nom Entreprise"] == society]["Symbol"].iloc[0]
    
    data = fetch_stock_data(ticker, duration, interval)
    data = process_data(data)
    
    last_close, change, pct_change, high, low, volume = calculate_metrics(data)

    st.metric(label=f"{society} Prix de clôture", value=f"{last_close:.2f} EUR", delta=f"{change:.2f}€ ({pct_change:.2f}%)")

    col1, col2, col3 = st.columns(3)
    col1.metric("High", f"{high:.2f} EUR") 
    col2.metric("Low", f"{low:.2f} EUR")
    col3.metric("Volume", f"{volume:,}")

    # Créer le graphique avec Plotly
    fig = go.Figure()

    if chart_type == "Candlestick":
        # Ajouter le graphique de chandeliers
        fig.add_trace(go.Candlestick(
            x=data.Datetime,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='Candlestick'
        ))
    else:
        fig = px.line(data, x="Datetime", y="Close", title=f"{society} {time_period.upper()} chart")

    if time_period in ["1d","5d"]:
        fig.update_xaxes(
            rangeslider_visible=True,
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  
                dict(bounds=[17.5, 9], pattern="hour"),  
            ]
        )
        
    elif time_period not in ["1d", "5d", "max"]:
        fig.update_xaxes(
            rangeslider_visible=True,
            rangebreaks=[
                dict(bounds=["sat", "mon"]) 
            ]
        )

    # Mettre à jour la mise en page
    fig.update_layout(
        title="Trades Long/Short",
        xaxis_title="Date",
        yaxis_title="Price (EUR)",
        height=600
    )

    for indicator in indicators:
        if indicator == "Support & Résistance":
            data, long_trades, short_trades = support_resistance(data, lookback=30)
            # Ajouter les signaux de support (1) et résistance (-1)
            filtered_sr_signal = filter_consecutive_value(data, "sr_signal")

            support_signals = np.where(filtered_sr_signal == 1, data['Close'], np.nan)
            resistance_signals = np.where(filtered_sr_signal == -1, data['Close'], np.nan)

            # Tracer les points de support avec des marqueurs verts
            fig.add_trace(go.Scatter(
                x=data['Datetime'],
                y=support_signals,
                mode='markers',
                marker=dict(symbol='triangle-up', color='green', size=10),
                name='Support'
            ))

            # Tracer les points de résistance avec des marqueurs rouges
            fig.add_trace(go.Scatter(
                x=data['Datetime'],
                y=resistance_signals,
                mode='markers',
                marker=dict(symbol='triangle-down', color='red', size=10),
                name='Resistance'
            ))

        # RSI (Relative Strength Index)
        elif indicator == "RSI":
            pass

        # DMI (Directional Movement Index)
        elif indicator == "DMI":
            pass

        # SMA_20 (Simple Moving Average)
        elif indicator == "SMA_20":
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=data['Datetime'],
                y=data['SMA_20'],
                mode='lines',
                line=dict(color='purple'),
                name='SMA 20'
            ))

        # Bande de Bollinger
        elif indicator == "Bande de Bollinger":
            pass

    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Données historiques")
    st.dataframe(data[["Datetime", "Open", "High", "Low", "Close", "Volume"]])

except Exception as e:
    # Afficher l'erreur avec le message détaillé
    st.error(f"**Erreur : {str(e)}**. Vérifiez votre connexion internet ou l'existence des données.")

st.sidebar.subheader("À propos")
st.sidebar.info("Ce Dashboard fournit des outils d'analyses techniques dans le marché d'actions. \
                C'est une recherche en partie sur le moment où l'on achète (Long trade) ou lorsqu'on vend (Short trade).")

