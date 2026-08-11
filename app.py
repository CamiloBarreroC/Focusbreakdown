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

    # Tabla de partidos
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

    # Tabla de jugadores
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

    # --- MIGRACIÓN AUTOMÁTICA DE ESQUEMA ---
    cursor.execute("PRAGMA table_info(jugadores)")
    columnas = [col[1] for col in cursor.fetchall()]
    if "estado_validacion" not in columnas:
        cursor.execute(
            "ALTER TABLE jugadores ADD COLUMN estado_validacion TEXT DEFAULT 'Confirmado'"
        )

    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------
# 2. INTERFAZ EN STREAMLIT
# ---------------------------------------------------------
st.set_page_config(
    page_title="Futbol Analytics Hub", layout="wide", page_icon="⚽"
)
st.title("⚽ Plataforma de Gestión y Análisis en Vivo")

tabs = st.tabs([
    "1. Registrar Partido",
    "2. Validar y Editar Plantilla (IA)",
    "3. Registro de Cambios en Vivo",
    "4. Base de Datos General",
])

# =========================================================
# --- PESTAÑA 1: REGISTRAR PARTIDO ---
# =========================================================
with tabs[0]:
    st.header("Configuración Inicial del Partido")
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
                    f"Partido entre {equipo_local} y {equipo_visitante} creado correctamente."
                )

# =========================================================
# --- PESTAÑA 2: VALIDAR Y EDITAR PLANTILLA ---
# =========================================================
with tabs[1]:
    st.header("Edición y Validación de Jugadores (Asistido por IA)")

    conn = get_connection()
    df_partidos = pd.read_sql(
        "SELECT id, fecha, equipo_local, equipo_visitante, formato FROM partidos",
        conn,
    )

    if df_partidos.empty:
        st.warning("Primero debes registrar un partido en la Pestaña 1.")
    else:
        opciones_partido = {
            row[
                "id"
            ]: f"{row['fecha']} | {row['equipo_local']} vs {row['equipo_visitante']} ({row['formato']})"
            for _, row in df_partidos.iterrows()
        }
        partido_sel_id = st.selectbox(
            "Selecciona el Partido a Gestionar:",
            options=list(opciones_partido.keys()),
            format_func=lambda x: opciones_partido[x],
            key="sel_p2",
        )

        partido_actual = df_partidos[
            df_partidos["id"] == partido_sel_id
        ].iloc[0]
        equipos_disponibles = [
            partido_actual["equipo_local"],
            partido_actual["equipo_visitante"],
        ]

        with st.expander(
            "➕ Añadir Jugador Manual o Sugerido por IA", expanded=False
        ):
            with st.form("form_nuevo_jugador"):
                col_e, col_a, col_b = st.columns(3)
                with col_e:
                    equipo_sel = st.radio(
                        "Equipo", equipos_disponibles, horizontal=True
                    )
                    origen = st.selectbox(
                        "Origen / Estado IA",
                        ["Confirmado", "Sugerido por IA", "Por Verificar"],
                    )

                with col_a:
                    es_no_name = st.checkbox("Solo tengo el número (No Name)")
                    nombre_in = st.text_input(
                        "Nombre del Jugador", disabled=es_no_name
                    )
                    nombre_final = (
                        "No Name"
                        if es_no_name or not nombre_in.strip()
                        else nombre_in
                    )
                    dorsal_in = st.number_input(
                        "Dorsal / Número", min_value=1, max_value=99, value=10
                    )

                with col_b:
                    posicion_in = st.selectbox(
                        "Posición",
                        ["Portero", "Defensa", "Medio", "Delantero"],
                    )
                    min_ent = st.number_input(
                        "Minuto Entrada", min_value=0, max_value=120, value=0
                    )
                    min_sal = st.number_input(
                        "Minuto Salida", min_value=1, max_value=120, value=90
                    )

                if st.form_submit_button("Guardar en Plantilla"):
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO jugadores (id_partido, equipo, nombre, dorsal, posicion, minuto_entrada, minuto_salida, estado_validacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            partido_sel_id,
                            equipo_sel,
                            nombre_final,
                            dorsal_in,
                            posicion_in,
                            min_ent,
                            min_sal,
                            origen,
                        ),
                    )
                    conn.commit()
                    st.success(f"Jugador #{dorsal_in} guardado correctamente.")
                    st.rerun()

        st.divider()

        st.subheader("📋 Tabla de Plantilla Editable")
        st.caption(
            "Puedes hacer doble clic en cualquier celda para corregir dorsales, nombres, posiciones o estados directamente."
        )

        jugadores_df = pd.read_sql(
            """
            SELECT id, equipo, dorsal, nombre, posicion, minuto_entrada, minuto_salida, estado_validacion 
            FROM jugadores 
            WHERE id_partido = ?
            ORDER BY equipo ASC, dorsal ASC
        """,
            conn,
            params=(int(partido_sel_id),),
        )

        if jugadores_df.empty:
            st.info("No hay jugadores cargados para este partido.")
        else:
            edited_df = st.data_editor(
                jugadores_df,
                key="editor_jugadores",
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "equipo": st.column_config.SelectboxColumn(
                        "Equipo", options=equipos_disponibles, required=True
                    ),
                    "dorsal": st.column_config.NumberColumn(
                        "Dorsal", min_value=1, max_value=99, required=True
                    ),
                    "nombre": st.column_config.TextColumn(
                        "Nombre / Identificador"
                    ),
                    "posicion": st.column_config.SelectboxColumn(
                        "Posición",
                        options=["Portero", "Defensa", "Medio", "Delantero"],
                    ),
                    "minuto_entrada": st.column_config.NumberColumn(
                        "Min. Entra", min_value=0, max_value=120
                    ),
                    "minuto_salida": st.column_config.NumberColumn(
                        "Min. Sale", min_value=1, max_value=120
                    ),
                    "estado_validacion": st.column_config.SelectboxColumn(
                        "Estado IA / Verificación",
                        options=[
                            "Confirmado",
                            "Sugerido por IA",
                            "Por Verificar",
                        ],
                    ),
                },
            )

            if st.button("💾 Guardar Cambios Editados en la Tabla"):
                cursor = conn.cursor()
                for _, row in edited_df.iterrows():
                    cursor.execute(
                        """
                        UPDATE jugadores 
                        SET equipo = ?, dorsal = ?, nombre = ?, posicion = ?, minuto_entrada = ?, minuto_salida = ?, estado_validacion = ?
                        WHERE id = ?
                    """,
                        (
                            row["equipo"],
                            int(row["dorsal"]),
                            row["nombre"],
                            row["posicion"],
                            int(row["minuto_entrada"]),
                            int(row["minuto_salida"]),
                            row["estado_validacion"],
                            int(row["id"]),
                        ),
                    )
                conn.commit()
                st.success("¡Base de datos actualizada con éxito!")
                st.rerun()

    conn.close()

# =========================================================
# --- PESTAÑA 3: REGISTRO DE CAMBIOS EN VIVO ---
# =========================================================
with tabs[2]:
    st.header("🔄 Control Dinámico de Sustituciones (Durante Análisis)")
    st.caption(
        "Utiliza este módulo a medida que el video avanza para marcar cambios en tiempo real."
    )

    conn = get_connection()
    df_partidos = pd.read_sql(
        "SELECT id, fecha, equipo_local, equipo_visitante, formato FROM partidos",
        conn,
    )

    if df_partidos.empty:
        st.warning("Primero debes registrar un partido en la Pestaña 1.")
    else:
        opciones_partido_v2 = {
            row[
                "id"
            ]: f"{row['fecha']} | {row['equipo_local']} vs {row['equipo_visitante']}"
            for _, row in df_partidos.iterrows()
        }
        partido_cambio_id = st.selectbox(
            "Selecciona el Partido en Análisis:",
            options=list(opciones_partido_v2.keys()),
            format_func=lambda x: opciones_partido_v2[x],
            key="sel_p3",
        )

        minuto_cambio_actual = st.number_input(
            "⏱️ Minuto Actual del Cambio", min_value=1, max_value=120, value=60
        )

        col_sale, col_entra = st.columns(2)

        jugadores_activos = pd.read_sql(
            """
            SELECT id, equipo, dorsal, nombre, posicion 
            FROM jugadores 
            WHERE id_partido = ? AND (minuto_salida >= ? OR minuto_salida IS NULL)
            ORDER BY equipo, dorsal
        """,
            conn,
            params=(int(partido_cambio_id), int(minuto_cambio_actual)),
        )

        with col_sale:
            st.subheader("🔴 Jugador que SALE")
            if jugadores_activos.empty:
                st.info("No hay jugadores disponibles en cancha.")
                jugador_sale_id = None
            else:
                opc_sale = {
                    row[
                        "id"
                    ]: f"[{row['equipo']}] #{row['dorsal']} - {row['nombre']} ({row['posicion']})"
                    for _, row in jugadores_activos.iterrows()
                }
                jugador_sale_id = st.selectbox(
                    "Selecciona el jugador que abandona la cancha:",
                    options=list(opc_sale.keys()),
                    format_func=lambda x: opc_sale[x],
                )

        with col_entra:
            st.subheader("🟢 Jugador que ENTRA")
            partido_actual_cambio = df_partidos[
                df_partidos["id"] == partido_cambio_id
            ].iloc[0]
            eq_entra = st.radio(
                "Equipo del jugador que ingresa:",
                [
                    partido_actual_cambio["equipo_local"],
                    partido_actual_cambio["equipo_visitante"],
                ],
                horizontal=True,
            )

            es_no_name_e = st.checkbox(
                "Es un 'No Name' (Solo número)", key="noname_entra"
            )
            nombre_entra_in = st.text_input(
                "Nombre Jugador Entrante",
                disabled=es_no_name_e,
                key="name_entra",
            )
            nombre_entra_final = (
                "No Name"
                if es_no_name_e or not nombre_entra_in.strip()
                else nombre_entra_in
            )

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                dorsal_entra = st.number_input(
                    "Dorsal Entrante",
                    min_value=1,
                    max_value=99,
                    value=14,
                    key="dorsal_e",
                )
            with col_e2:
                pos_entra = st.selectbox(
                    "Posición a asumir",
                    ["Portero", "Defensa", "Medio", "Delantero"],
                    key="pos_e",
                )

        st.divider()
        if st.button(
            "⚡ Registrar Sustitución Ahora", use_container_width=True
        ):
            if jugador_sale_id:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE jugadores SET minuto_salida = ? WHERE id = ?",
                    (int(minuto_cambio_actual), int(jugador_sale_id)),
                )
                cursor.execute(
                    """
                    INSERT INTO jugadores (id_partido, equipo, nombre, dorsal, posicion, minuto_entrada, minuto_salida, estado_validacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmado')
                """,
                    (
                        int(partido_cambio_id),
                        eq_entra,
                        nombre_entra_final,
                        int(dorsal_entra),
                        pos_entra,
                        int(minuto_cambio_actual),
                        90,
                    ),
                )
                conn.commit()
                st.success(
                    f"¡Sustitución efectuada en el minuto {minuto_cambio_actual}!"
                )
                st.rerun()

    conn.close()

# =========================================================
# --- PESTAÑA 4: BASE DE DATOS GENERAL ---
# =========================================================
with tabs[3]:
    st.header("📊 Resumen de Base de Datos")
    conn = get_connection()

    st.subheader("Lista de Partidos Registrados")
    partidos_df = pd.read_sql("SELECT * FROM partidos", conn)
    st.dataframe(partidos_df, use_container_width=True)

    st.subheader("Historial Completo de Jugadores y Tiempos de Juego")
    jugadores_df = pd.read_sql(
        """
        SELECT j.id, p.fecha, j.equipo, j.dorsal, j.nombre, j.posicion, j.minuto_entrada, j.minuto_salida, j.estado_validacion 
        FROM jugadores j 
        JOIN partidos p ON j.id_partido = p.id
        ORDER BY p.fecha DESC, j.equipo ASC, j.dorsal ASC
    """,
        conn,
    )
    st.dataframe(jugadores_df, use_container_width=True)

    conn.close()
