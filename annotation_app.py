import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os

# ------------------------------------------------------------
# Настройка страницы
# ------------------------------------------------------------
st.set_page_config(
    page_title="Разметка ТТХ БПЛА",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("✈️ Разметка данных БПЛА (агентный поиск ТТХ и сегментация)")
st.markdown("Инструмент для верификации, корректировки и ручной сегментации беспилотных платформ.")

# ------------------------------------------------------------
# Инициализация состояния сессии
# ------------------------------------------------------------
if 'data' not in st.session_state:
    st.session_state.data = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'annotated_indices' not in st.session_state:
    st.session_state.annotated_indices = set()
if 'output_file' not in st.session_state:
    st.session_state.output_file = "annotated_uav_data.csv"
if 'original_file_name' not in st.session_state:
    st.session_state.original_file_name = None

# ------------------------------------------------------------
# Функция приведения типов для служебных колонок
# ------------------------------------------------------------
def fix_annotation_columns(df):
    """Приводит колонки Segment, Comment к строковому типу, Verified к bool."""
    if 'Segment' in df.columns:
        df['Segment'] = df['Segment'].astype(str)
    else:
        df['Segment'] = ""
    if 'Comment' in df.columns:
        df['Comment'] = df['Comment'].astype(str)
    else:
        df['Comment'] = ""
    if 'Verified' in df.columns:
        df['Verified'] = df['Verified'].astype(bool)
    else:
        df['Verified'] = False
    return df

# ------------------------------------------------------------
# Функция загрузки размеченных данных (если файл существует)
# ------------------------------------------------------------
def load_annotated_data(filepath):
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df = fix_annotation_columns(df)
        annotated = set(df[df['Verified'] == True].index.tolist())
        current = 0
        while current in annotated and current < len(df):
            current += 1
        return df, annotated, current
    return None, set(), 0

# ------------------------------------------------------------
# Боковая панель: загрузка данных и управление
# ------------------------------------------------------------
with st.sidebar:
    st.header("📂 Управление")

    uploaded_file = st.file_uploader("Загрузить исходный CSV (ТТХ БПЛА)", type=["csv"])
    if uploaded_file is not None:
        base_name = os.path.splitext(uploaded_file.name)[0]
        st.session_state.original_file_name = base_name
        default_output = f"{base_name}_annotated.csv"
        st.session_state.output_file = default_output

        df_existing, ann_set, curr_idx = load_annotated_data(default_output)
        if df_existing is not None:
            st.session_state.data = df_existing
            st.session_state.annotated_indices = ann_set
            st.session_state.current_index = curr_idx
            st.success(f"Загружен существующий размеченный файл: {len(df_existing)} записей, размечено {len(ann_set)}")
        else:
            df = pd.read_csv(uploaded_file)
            if 'Segment' not in df.columns:
                df['Segment'] = ""
            if 'Comment' not in df.columns:
                df['Comment'] = ""
            if 'Verified' not in df.columns:
                df['Verified'] = False
            df = fix_annotation_columns(df)
            st.session_state.data = df
            st.session_state.annotated_indices = set()
            st.session_state.current_index = 0
            st.success(f"Загружено {len(df)} записей (новая разметка)")

    if st.session_state.data is not None:
        total = len(st.session_state.data)
        done = len(st.session_state.annotated_indices)
        st.metric("Прогресс разметки", f"{done} / {total} ({100*done/total:.1f}%)")
        
        output_name = st.text_input("Имя файла для сохранения", value=st.session_state.output_file)
        st.session_state.output_file = output_name
        
        if st.button("💾 Принудительно сохранить всё"):
            st.session_state.data.to_csv(st.session_state.output_file, index=False)
            st.success(f"Сохранено в {st.session_state.output_file}")
        
        if st.button("🔄 Сбросить разметку (начать заново)"):
            df = st.session_state.data
            df['Segment'] = ""
            df['Comment'] = ""
            df['Verified'] = False
            df = fix_annotation_columns(df)
            st.session_state.annotated_indices = set()
            st.session_state.current_index = 0
            df.to_csv(st.session_state.output_file, index=False)
            st.rerun()

# ------------------------------------------------------------
# Основная область – разметка текущей записи
# ------------------------------------------------------------
if st.session_state.data is not None:
    df = st.session_state.data
    total_rows = len(df)

    while st.session_state.current_index < total_rows and st.session_state.current_index in st.session_state.annotated_indices:
        st.session_state.current_index += 1

    if st.session_state.current_index >= total_rows:
        st.success("✅ Все записи размечены! Отличная работа.")
        if st.button("📥 Скачать размеченные данные (CSV)"):
            df.to_csv(st.session_state.output_file, index=False)
            with open(st.session_state.output_file, "rb") as f:
                st.download_button("Скачать CSV", f, file_name=st.session_state.output_file)
    else:
        idx = st.session_state.current_index
        row = df.iloc[idx].copy()

        st.subheader(f"Запись {idx+1} из {total_rows}")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Исходные данные (можно редактировать)**")
            editable_cols = [c for c in df.columns if c not in ['Segment', 'Comment', 'Verified']]
            edited = {}
            for col in editable_cols:
                if col in ['Weight_g', 'Flight_Time_min', 'Actual_Flight_Time_min', 
                           'Range_km', 'Camera_MP', 'Price_USD', 'Max_Speed_ms']:
                    try:
                        val = float(row[col]) if pd.notna(row[col]) else 0.0
                    except (ValueError, TypeError):
                        val = 0.0
                    edited[col] = st.number_input(col, value=val,
                                                  format="%.2f" if '.' in str(val) else "%.0f")
                else:
                    edited[col] = st.text_input(col, value=str(row[col]) if pd.notna(row[col]) else "")

        with col2:
            st.markdown("**Ручная сегментация и примечания**")
            segment_options = [
                "Легкий потребительский (<250г)",
                "Потребительский (250-900г)",
                "Профессиональный (900-4000г)",
                "Промышленный (4-25кг)",
                "Тяжелый промышленный (>25кг)",
                "FPV/гоночный",
                "Самолётного типа",
                "Гибридный/VTOL",
                "Другое"
            ]
            current_seg = row['Segment']
            if current_seg not in segment_options:
                current_seg = segment_options[0]
            segment = st.selectbox("Сегмент (кластер)", segment_options, index=segment_options.index(current_seg))
            comment = st.text_area("Комментарий разметчика", value=row['Comment'] if pd.notna(row['Comment']) else "")
            verified = st.checkbox("✅ Данные проверены и верны", value=row['Verified'] if pd.notna(row['Verified']) else False)

        if st.button("✔️ Сохранить разметку для этой модели"):
            for col, val in edited.items():
                df.at[idx, col] = val
            df.at[idx, 'Segment'] = segment
            df.at[idx, 'Comment'] = comment
            df.at[idx, 'Verified'] = verified

            st.session_state.annotated_indices.add(idx)
            st.session_state.current_index += 1

            df.to_csv(st.session_state.output_file, index=False)
            st.success(f"Сохранено. Размечено {len(st.session_state.annotated_indices)} записей.")
            st.rerun()

        st.markdown("---")
        st.caption(f"Размечено записей: {len(st.session_state.annotated_indices)}. Текущая позиция: {st.session_state.current_index+1}")
else:
    st.info("👈 Загрузите CSV‑файл с ТТХ БПЛА в боковой панели, чтобы начать разметку.")