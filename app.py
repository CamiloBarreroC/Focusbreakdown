import sqlite3
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 1. CONFIGURACIÓN Y BASE DE DATOS (SQLite)
# ---------------------------------------------------------


def get_connection():
    return sqlite3.connect("futbol_analytics.db")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de partidos (Con fecha y URL obligatoria de Drive)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            formato TEXT,
            equipo_local TEXT,
            equipo_visitante TEXT,
            url_drive TEXT
        )
    """)

    # Tabla de jugadores (Vinculados al partido y equipo)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_partido INTEGER,
            equipo TEXT,
            nombre TEXT,
            dorsal INTEGER,
            posicion TEXT,
            minuto_entrada INTEGER,
            minuto_salida INTEGER,
            FOREIGN KEY (id_partido) REFERENCES partidos (id)
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------
# 2. INTERFAZ EN STREAMLIT
# ---------------------------------------------------------
st.set_page_config(page_title="Futbol Analytics Hub", layout="wide")
st.title("⚽ Plataforma de Gestión de Partidos")

tabs = st.tabs(
    ["1. Registrar Partido", "2. Cargar Alineación", "3. Base de Datos"]
)

# --- PESTAÑA 1: REGISTRAR PARTIDO ---
with tabs[0]:
    st.header("Configuración del Partido")
    with st.form("form_partido"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_partido = st.date_input("Fecha del Partido")
            formato = st.selectbox(
                "Formato de juego",
                ["Futbol 5", "Futbol 7", "Futbol 9", "Futbol 11"],
            )
            url_drive = st.text_input(
                "Enlace del Video en Google Drive (*Obligatorio*)"
            )
        with col2:
            equipo_local = st.text_input("Nombre Equipo Local", "Equipo A")
            equipo_visitante = st.text_input("Nombre Equipo Visitante", "Equipo B")

        guardar_partido = st.form_submit_button("Crear Partido")

        if guardar_partido:
            # Validar que el enlace de Drive no esté vacío
            if not url_drive.strip():
                st.error(
                    "❌ Debes ingresar el enlace del video en Google Drive para poder procesar el partido."
                )
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO partidos (fecha, formato, equipo_local, equipo_visitante, url_drive) VALUES (?, ?, ?, ?, ?)",
                    (
                        str(fecha_partido),
                        formato,
                        equipo_local,
                        equipo_visitante,
                        url_drive,
                    ),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"Partido entre {equipo_local} y {equipo_visitante} guardado con éxito y listo para análisis."
                )

# --- PESTAÑA 2: ALINEACIÓN Y CAMBIOS ---
with tabs[1]:
    st.header("Cargar Jugadores")

    conn = get_connection()
    df_partidos = pd.read_sql(
        "SELECT id, fecha, equipo_local, equipo_visitante, formato FROM partidos",
        conn,
    )

    if df_partidos.empty:
        st.warning("Primero debes registrar un partido en la pestaña 1.")
    else:
        # Selector dinámico de partidos
        opciones_partido = {
            row[
                "id"
            ]: f"{row['fecha']} | {row['equipo_local']} vs {row['equipo_visitante']} ({row['formato']})"
            for _, row in df_partidos.iterrows()
        }
        partido_sel_id = st.selectbox(
            "1. Selecciona el partido:",
            options=list(opciones_partido.keys()),
            format_func=lambda x: opciones_partido[x],
        )

        # Cargar los equipos correspondientes al partido elegido
        partido_actual = df_partidos[
            df_partidos["id"] == partido_sel_id
        ].iloc[0]
        equipos_disponibles = [
            partido_actual["equipo_local"],
            partido_actual["equipo_visitante"],
        ]

        st.divider()
        st.subheader("2. Añadir Jugador")
        with st.form("form_jugador"):
            equipo_seleccionado = st.radio(
                "¿A qué equipo pertenece el jugador?",
                equipos_disponibles,
                horizontal=True,
            )

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                es_no_name = st.checkbox("Solo tengo el número (No Name)")
                nombre_input = st.text_input(
                    "Nombre del jugador", disabled=es_no_name
                )
                nombre_final = (
                    "No Name"
                    if es_no_name or not nombre_input.strip()
                    else nombre_input
                )

            with col_b:
                dorsal = st.number_input(
                    "Número (Dorsal)", min_value=1, max_value=99, value=10
                )
                posicion = st.selectbox(
                    "Posición", ["Portero", "Defensa", "Medio", "Delantero"]
                )

            with col_c:
                minuto_entrada = st.number_input(
                    "Minuto entra", min_value=0, max_value=120, value=0
                )
                es_cambiado = st.checkbox("¿Salió de cambio?")
                minuto_salida = (
                    st.number_input(
                        "Minuto sale", min_value=1, max_value=120, value=90
                    )
                    if es_cambiado
                    else None
                )

            guardar_jugador = st.form_submit_button("Guardar Jugador")

            if guardar_jugador:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jugadores (id_partido, equipo, nombre, dorsal, posicion, minuto_entrada, minuto_salida) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        partido_sel_id,
                        equipo_seleccionado,
                        nombre_final,
                        dorsal,
                        posicion,
                        minuto_entrada,
                        minuto_salida,
                    ),
                )
                conn.commit()
                st.success(
                    f"Jugador #{dorsal} ({nombre_final}) agregado al equipo: {equipo_seleccionado}."
                )

    conn.close()

# --- PESTAÑA 3: VER BASE DE DATOS ---
with tabs[2]:
    st.header("Registros Actuales")
    conn = get_connection()

    st.subheader("Partidos")
    partidos_df = pd.read_sql("SELECT * FROM partidos", conn)
    st.dataframe(partidos_df, use_container_width=True)

    st.subheader("Jugadores Cargados")
    jugadores_df = pd.read_sql(
        """
        SELECT j.id, p.fecha, j.equipo, j.dorsal, j.nombre, j.posicion, j.minuto_entrada, j.minuto_salida 
        FROM jugadores j 
        JOIN partidos p ON j.id_partido = p.id
        ORDER BY p.fecha DESC, j.equipo ASC, j.dorsal ASC
    """,
        conn,
    )
    st.dataframe(jugadores_df, use_container_width=True)

    conn.close()
    