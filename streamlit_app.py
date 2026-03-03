import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="PeruLabTech Smart Parking", layout="centered")

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
}
.big-title {
    font-size: 28px;
    font-weight: 700;
}
.kpi-card {
    padding: 15px;
    border-radius: 12px;
    background: #f8f9fa;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>🚀
