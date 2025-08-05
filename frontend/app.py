# frontend/app.py - SUPER EINFACH
import streamlit as st

st.title("🍳 NUGAMOTO Admin")
st.write("Hallo! Das ist deine erste Streamlit-App.")

# Einfacher Test
name = st.text_input("Wie heißt du?")
if name:
    st.write(f"Hallo {name}! 👋")

# Button-Test
if st.button("Klick mich!"):
    st.success("Button funktioniert! 🎉")