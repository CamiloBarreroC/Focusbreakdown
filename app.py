import sqlite3
import pandas as pd
import streamlit as st
import re

# ---------------------------------------------------------
# 1. CONFIGURACIÓN Y BASE DE DATOS (SQLite)
# ---------------------------------------------------------

def get_connection():
    return sqlite3.connect("futbol_analytics.db")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

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
            estado_validacion TEXT DEFAULT 'Confirmado',
            FOREIGN KEY (id_partido) REFERENCES partidos (id)
        )
    """)

    cursor.execute("PRAGMA table_info(jugadores)")
    columnas = [col[1] for col in cursor.fetchall()]
    if "estado_validacion" not in columnas:
        cursor.execute("ALTER TABLE jugadores ADD COLUMN estado_validacion TEXT DEFAULT 'Confirmado'")

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# FUNCIONES AUXILIARES (Para Google Drive)
# ---------------------------------------------------------
def convertir_url_drive_a_embed(url):
    """
    Convierte una URL normal de Google Drive en una URL de vista previa (embed)
    para poder mostrarla en el reproductor de Streamlit.
    """
    if not url:
        return None
    
    # Busca el ID del video en la URL
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        video_id = match.group(1)
        return f"https://drive.google.com/file/d/{video_id}/preview"
    return None

# ---------------------------------------------------------
# 2. INTERFAZ EN STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Futbol Analytics Hub", layout="wide", page_icon="⚽"
)
st.title("⚽ Plataforma de Gestión y Análisis en Vivo")

tabs = st.tabs([
    "1. Registrar Partido",
    "2. Validar y Editar Plantilla",
    "3. Registro de Cambios en Vivo",
    "4. Base de Datos",
    "🎥 5. Analista de Video (IA)" # <--- NUEVA PESTAÑA
])

# =========================================================
# --- PESTAÑA 1, 2, 3 y 4 (Se mantienen iguales) ---
# =========================================================

# --- PESTAÑA 1 ---
with tabs[0]:
    st.header("Configuración Inicial del Partido")
    with st.form("form_partido"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_partido = st.date_input("Fecha del Partido")
            formato = st.selectbox("Formato de juego", ["Futbol 5", "Futbol 7", "Futbol 9", "Futbol 11"])
            url_drive = st.text_input("Enlace del Video en Google Drive (*Obligatorio*)")
        with col2:
            equipo_local = st.text_input("Nombre Equipo Local", "Equipo A")
            equipo_visitante = st.text_input("Nombre Equipo Visitante", "Equipo B")

        if st.form_submit_button("Crear Partido"):
            if not url_drive.strip():
                st.error("❌ Debes ingresar el enlace del video en Google Drive.")
            else:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO partidos (fecha, formato, equipo_local, equipo_visitante, url_drive) VALUES (?, ?, ?, ?, ?)",
                    (str(fecha_partido), formato, equipo_local, equipo_visitante, url_drive)
                )
                conn.commit()
                conn.close()
                st.success(f"Partido {equipo_local} vs {equipo_visitante} creado correctamente.")

# --- PESTAÑA 2 ---
with tabs[1]:
    st.header("Edición y Validación de Jugadores (Asistido por IA)")
    conn = get_connection()
    df_partidos = pd.read_sql("SELECT * FROM partidos", conn)

    if not df_partidos.empty:
        opciones_partido = {r["id"]: f"{r['fecha']} | {r['equipo_local']} vs {r['equipo_visitante']}" for _, r in df_partidos.iterrows()}
        partido_sel_id = st.selectbox("Selecciona el Partido:", options=list(opciones_partido.keys()), format_func=lambda x: opciones_partido[x], key="sel_p2")
        partido_actual = df_partidos[df_partidos["id"] == partido_sel_id].iloc[0]
        equipos_disponibles = [partido_actual["equipo_local"], partido_actual["equipo_visitante"]]

        with st.expander("➕ Añadir Jugador Manual o Sugerido", expanded=False):
            with st.form("form_nuevo_jugador"):
                col_e, col_a, col_b = st.columns(3)
                with col_e:
                    equipo_sel = st.radio("Equipo", equipos_disponibles, horizontal=True)
                    origen = st.selectbox("Estado IA", ["Confirmado", "Sugerido por IA", "Por Verificar"])
                with col_a:
                    es_no_name = st.checkbox("Solo tengo el número (No Name)")
                    nombre_in = st.text_input("Nombre del Jugador", disabled=es_no_name)
                    nombre_final = "No Name" if es_no_name or not nombre_in.strip() else nombre_in
                    dorsal_in = st.number_input("Dorsal / Número", min_value=1, max_value=99, value=10)
                with col_b:
                    posicion_in = st.selectbox("Posición", ["Portero", "Defensa", "Medio", "Delantero"])
                    min_ent = st.number_input("Minuto Entrada", min_value=0, max_value=120, value=0)
                    min_sal = st.number_input("Minuto Salida", min_value=1, max_value=120, value=90)
                
                if st.form_submit_button("Guardar"):
                    conn.execute(
                        "INSERT INTO jugadores (id_partido, equipo, nombre, dorsal, posicion, minuto_entrada, minuto_salida, estado_validacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (partido_sel_id, equipo_sel, nombre_final, dorsal_in, posicion_in, min_ent, min_sal, origen)
                    )
                    conn.commit()
                    st.success("Guardado.")
                    st.rerun()

        st.divider()
        st.subheader("📋 Tabla de Plantilla Editable")
        jugadores_df = pd.read_sql("SELECT id, equipo, dorsal, nombre, posicion, minuto_entrada, minuto_salida, estado_validacion FROM jugadores WHERE id_partido = ? ORDER BY equipo, dorsal", conn, params=(int(partido_sel_id),))

        if not jugadores_df.empty:
            edited_df = st.data_editor(
                jugadores_df, key="editor", num_rows="dynamic", use_container_width=True,
                column_config={"id": st.column_config.NumberColumn("ID", disabled=True), "equipo": st.column_config.SelectboxColumn("Equipo", options=equipos_disponibles), "estado_validacion": st.column_config.SelectboxColumn("Estado", options=["Confirmado", "Sugerido por IA", "Por Verificar"])}
            )
            if st.button("💾 Guardar Cambios"):
                cursor = conn.cursor()
                for _, r in edited_df.iterrows():
                    cursor.execute("UPDATE jugadores SET equipo=?, dorsal=?, nombre=?, posicion=?, minuto_entrada=?, minuto_salida=?, estado_validacion=? WHERE id=?", (r["equipo"], int(r["dorsal"]), r["nombre"], r["posicion"], int(r["minuto_entrada"]), int(r["minuto_salida"]), r["estado_validacion"], int(r["id"])))
                conn.commit()
                st.success("Actualizado")
                st.rerun()
    conn.close()

# --- PESTAÑA 3 ---
with tabs[2]:
    st.header("🔄 Control Dinámico de Sustituciones")
    conn = get_connection()
    df_partidos = pd.read_sql("SELECT * FROM partidos", conn)
    if not df_partidos.empty:
        opciones_p3 = {r["id"]: f"{r['fecha']} | {r['equipo_local']} vs {r['equipo_visitante']}" for _, r in df_partidos.iterrows()}
        p_cambio_id = st.selectbox("Selecciona Partido:", options=list(opciones_p3.keys()), format_func=lambda x: opciones_p3[x], key="sel_p3")
        minuto_cambio = st.number_input("⏱️ Minuto del Cambio", min_value=1, max_value=120, value=60)
        
        col_sale, col_entra = st.columns(2)
        jug_activos = pd.read_sql("SELECT id, equipo, dorsal, nombre, posicion FROM jugadores WHERE id_partido=? AND (minuto_salida >= ? OR minuto_salida IS NULL)", conn, params=(int(p_cambio_id), int(minuto_cambio)))
        
        with col_sale:
            st.subheader("🔴 SALE")
            if not jug_activos.empty:
                opc_sale = {r["id"]: f"[{r['equipo']}] #{r['dorsal']} - {r['nombre']}" for _, r in jug_activos.iterrows()}
                jug_sale_id = st.selectbox("Jugador que sale:", options=list(opc_sale.keys()), format_func=lambda x: opc_sale[x])
            else:
                jug_sale_id = None
                
        with col_entra:
            st.subheader("🟢 ENTRA")
            p_actual = df_partidos[df_partidos["id"]==p_cambio_id].iloc[0]
            eq_entra = st.radio("Equipo:", [p_actual["equipo_local"], p_actual["equipo_visitante"]], horizontal=True)
            noname_e = st.checkbox("Solo número (No Name)", key="nn_e")
            nom_entra = st.text_input("Nombre", disabled=noname_e)
            nom_final_e = "No Name" if noname_e or not nom_entra.strip() else nom_entra
            dorsal_e = st.number_input("Dorsal", min_value=1, value=14)
            pos_e = st.selectbox("Posición", ["Portero", "Defensa", "Medio", "Delantero"])
            
        if st.button("⚡ Registrar Sustitución", use_container_width=True) and jug_sale_id:
            cursor = conn.cursor()
            cursor.execute("UPDATE jugadores SET minuto_salida=? WHERE id=?", (int(minuto_cambio), int(jug_sale_id)))
            cursor.execute("INSERT INTO jugadores (id_partido, equipo, nombre, dorsal, posicion, minuto_entrada, minuto_salida) VALUES (?,?,?,?,?,?,90)", (int(p_cambio_id), eq_entra, nom_final_e, int(dorsal_e), pos_e, int(minuto_cambio)))
            conn.commit()
            st.success("Cambio registrado.")
            st.rerun()
    conn.close()

# --- PESTAÑA 4 ---
with tabs[3]:
    st.header("📊 Resumen de Base de Datos")
    conn = get_connection()
    st.dataframe(pd.read_sql("SELECT * FROM partidos", conn), use_container_width=True)
    st.dataframe(pd.read_sql("SELECT * FROM jugadores", conn), use_container_width=True)
    conn.close()

# =========================================================
# --- PESTAÑA 5: ANALISTA DE VIDEO E IA ---
# =========================================================
with tabs[4]:
    st.header("🎥 Analista de Video e IA")
    
    conn = get_connection()
    df_partidos = pd.read_sql("SELECT id, fecha, equipo_local, equipo_visitante, url_drive FROM partidos", conn)
    
    if df_partidos.empty:
        st.warning("No hay partidos registrados. Ve a la Pestaña 1.")
    else:
        # 1. Selector de Partido
        opciones_video = {
            r["id"]: f"{r['equipo_local']} vs {r['equipo_visitante']} ({r['fecha']})" 
            for _, r in df_partidos.iterrows()
        }
        partido_vid_id = st.selectbox(
            "Selecciona el partido para visualizar:",
            options=list(opciones_video.keys()),
            format_func=lambda x: opciones_video[x],
            key="sel_video"
        )
        
        url_original = df_partidos[df_partidos["id"] == partido_vid_id].iloc[0]["url_drive"]
        url_embed = convertir_url_drive_a_embed(url_original)
        
        st.divider()

        # 2. Maquetación del Reproductor y el Panel de IA
        col_video, col_panel = st.columns([2, 1]) # El video ocupa 2/3, el panel 1/3 de la pantalla
        
        with col_video:
            st.subheader("📺 Reproductor de Partido")
            if url_embed:
                # Incrustar el iframe de Google Drive
                st.components.v1.iframe(url_embed, height=450)
                st.caption(f"🔗 URL Original conectada: {url_original}")
            else:
                st.error("❌ El enlace de Google Drive guardado no tiene un formato válido.")
                
        with col_panel:
            st.subheader("🧠 Panel de Control IA")
            st.info("Módulo preparado para conectar al backend de Visión por Computadora.")
            
            # Botones de simulación de Análisis
            if st.button("🚀 Iniciar Tracking IA (Detección)", use_container_width=True):
                with st.spinner("Conectando con el modelo de visión..."):
                    import time
                    time.sleep(2) # Simula tiempo de carga
                    st.success("✅ Modelo conectado. Tracking activo sobre el video.")
            
            # Contenedores de métricas en vivo (Placeholders)
            st.markdown("### Métricas en Vivo")
            col_m1, col_m2 = st.columns(2)
            col_m1.metric(label="Jugadores Detectados", value="22", delta="+2 en banca")
            col_m2.metric(label="Precisión del Modelo", value="94.5%")
            
            st.markdown("### Herramientas de Análisis")
            st.checkbox("🟢 Mostrar IDs y Dorsales (Bounding Boxes)")
            st.checkbox("🔥 Generar Mapa de Calor en Vivo")
            st.checkbox("🏃 Mostrar Distancia Recorrida")
            
            st.divider()
            st.button("📥 Exportar Reporte de Tracking (.CSV)", use_container_width=True)

    conn.close()
