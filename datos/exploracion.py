import pandas as pd

# 1. LECTURA (lo que ya resolviste: separador, tildes, decimales)
df = pd.read_csv("flujo_vehicular.csv", sep=";", encoding="latin-1",
                 decimal=",", low_memory=False)

# 2. LIMPIEZA: sacar las filas totalmente vacías
print("Filas antes:", len(df))
df = df.dropna(how="all")
print("Filas después:", len(df))

# 3. RENOMBRAR columnas: sin espacios ni tildes, que después Supabase las pide así
df = df.rename(columns={
    "Día, Mes, Año de H_Fecha": "fecha",
    "Hora de H_Fecha": "hora",
    "Aut Nombre": "autopista",
    "Disp Nombre": "dispositivo",
    "Disp Ubicacion": "ubicacion",
    "Seccion Sentido": "sentido",
    "Disp Lat": "lat",
    "Disp Lng": "lng",
    "H_Cant_Veh": "vehiculos",
})

# 4a. Diagnóstico: cuántas fechas hay de cada tipo
es_serial = df["fecha"].str.fullmatch(r"\d+", na=False)   # True si son solo dígitos
print("Fechas tipo número serial:", es_serial.sum())
print("Fechas tipo texto:", (~es_serial).sum())
print("Ejemplos de texto:", df.loc[~es_serial, "fecha"].unique()[:15])
print("Ejemplos de serial:", df.loc[es_serial, "fecha"].unique()[:15])

# 4b. Conversión: cada tipo con su método, y se vuelven a juntar
fecha_texto = pd.to_datetime(df.loc[~es_serial, "fecha"], format="%d/%m/%Y")
fecha_serial = pd.to_datetime(df.loc[es_serial, "fecha"].astype(int),
                              unit="D", origin="1899-12-30")
df["fecha"] = pd.concat([fecha_texto, fecha_serial]).sort_index()

print("Rango de fechas:", df["fecha"].min(), "a", df["fecha"].max())
print("Días distintos:", df["fecha"].nunique())

# 5. EXPLORACIÓN
print("Autopistas:", df["autopista"].unique())
print("Dispositivos distintos:", df["dispositivo"].nunique())
print("Sentidos:", df["sentido"].unique())
print("Celdas vacías por columna:\n", df.isna().sum())

# 6. TABLA DE DISPOSITIVOS: una fila por dispositivo con su ubicación
dispositivos = df[["autopista", "dispositivo", "lat", "lng"]].drop_duplicates()
print("Filas en la tabla de dispositivos:", len(dispositivos))
print("Dispositivos con más de una ubicación:", dispositivos["dispositivo"].duplicated().sum())

# 7. RESUMEN POR SENTIDO: sirve para entender qué significan A, B y R
print(df.groupby("sentido")["vehiculos"].agg(["count", "sum", "mean"]))

# 8. RESUMEN POR DISPOSITIVO Y SENTIDO: de 57.088 filas a muy pocas
resumen = df.groupby(["autopista", "dispositivo", "sentido", "lat", "lng"], as_index=False).agg(
    total=("vehiculos", "sum"),
    promedio_hora=("vehiculos", "mean"),
)
print("Filas del resumen:", len(resumen))

# 9. GUARDAR para mirarlos en un mapa o en Excel/Power BI
dispositivos.to_csv("dispositivos.csv", index=False, encoding="utf-8")
resumen.to_csv("resumen.csv", index=False, encoding="utf-8")

import plotly.express as px

# 10. MAPA con etiquetas (abrir mapa_dispositivos.html en el navegador)
fig = px.scatter_map(dispositivos, lat="lat", lon="lng",
                     hover_name="dispositivo", text="dispositivo",
                     color="autopista", zoom=10, height=800)
fig.update_layout(map_style="carto-positron")
fig.write_html("mapa_dispositivos.html", include_plotlyjs=True)
fig.show()



# 11. ¿De qué dispositivos son las 120 filas sin sentido?
print(df[df["sentido"].isna()]["dispositivo"].value_counts())

# 12. MAÑANA vs TARDE, solo días de semana (lunes=0 ... viernes=4)
laborables = df[df["fecha"].dt.dayofweek < 5]
manana = laborables[laborables["hora"].between(6, 10)].groupby(["dispositivo", "sentido"])["vehiculos"].mean()
tarde = laborables[laborables["hora"].between(17, 21)].groupby(["dispositivo", "sentido"])["vehiculos"].mean()
comparacion = pd.DataFrame({"manana": manana, "tarde": tarde}).reset_index()
comparacion["dif"] = comparacion["manana"] - comparacion["tarde"]
comparacion.to_csv("comparacion_manana_tarde.csv", index=False, encoding="utf-8")
print(comparacion.sort_values("dif").head(10))
print(comparacion.sort_values("dif").tail(10))

# 13. LISTA ordenada de dispositivos: autopista, kilómetro y coordenadas
lista = (df[["autopista", "dispositivo", "ubicacion", "lat", "lng"]]
         .drop_duplicates()
         .sort_values(["autopista", "ubicacion"]))
print(lista.to_string(index=False))


# 14. TABLA FINAL para Supabase: sentido A, lunes a viernes, pico de la mañana
df["dispositivo"] = df["dispositivo"].str.strip()
df["autopista"] = df["autopista"].str.replace(r"\s+", " ", regex=True).str.strip()  # arregla "AU 4  Lugones"

# 14a. Filtro: sentido A, lunes a viernes (dayofweek < 5), horas 6 a 10
pico = df[
    (df["sentido"] == "A")
    & (df["fecha"].dt.dayofweek < 5)
    & (df["hora"].between(6, 10))
]

# 14b. Una fila por sensor: promedio de vehículos por hora
puntos = pico.groupby(["autopista", "dispositivo", "ubicacion", "lat", "lng"], as_index=False).agg(
    valor=("vehiculos", "mean")
)
puntos["valor"] = puntos["valor"].round(0).astype(int)

puntos = puntos[puntos["valor"] > 0]

# 14c. Categoría por nivel de tránsito: divide los sensores en 3 grupos del mismo tamaño
puntos["categoria"] = pd.qcut(puntos["valor"], 3, labels=["Bajo", "Medio", "Alto"])

# 14d. Descripción = autopista + kilómetro, que es el "tramo"
puntos["descripcion"] = puntos["autopista"] + " - km " + puntos["ubicacion"].astype(str)

# 14e. Nombres de columna como la tabla "puntos" del TP
puntos = puntos.rename(columns={"dispositivo": "nombre", "lat": "latitud", "lng": "longitud"})
puntos = puntos[["nombre", "categoria", "latitud", "longitud", "valor", "descripcion"]]

# 14f. Controles
print("Filas de la tabla final:", len(puntos))
print(puntos["categoria"].value_counts())
print(puntos["valor"].describe())
print(puntos.sort_values("valor", ascending=False).head(10).to_string(index=False))

# 14g. Guardar (este es el archivo que se importa en Supabase)
puntos.to_csv("puntos.csv", index=False, encoding="utf-8")
# 15. DIAGNÓSTICO: ¿qué sentidos tienen estos accesos y cómo se comportan?
revisar = ["RD050 Gral. Paz B", "RD053 Riach-AccNorte",
           "RD183 Centro Naval", "RD052 Acceso AU6"]
base = df[df["dispositivo"].isin(revisar) & (df["fecha"].dt.dayofweek < 5)]

# 15a. Qué sentidos aparecen en cada dispositivo y cuántas filas tiene cada uno
print(base.groupby(["dispositivo", "sentido"], dropna=False).size())

# 15b. Promedio por hora: mañana (6 a 10) contra tarde (17 a 21)
manana = base[base["hora"].between(6, 10)].groupby(["dispositivo", "sentido"], dropna=False)["vehiculos"].mean()
tarde = base[base["hora"].between(17, 21)].groupby(["dispositivo", "sentido"], dropna=False)["vehiculos"].mean()
print(pd.DataFrame({"manana": manana.round(0), "tarde": tarde.round(0)}))

x = df[(df["dispositivo"] == "RD089 Defensa") & (df["sentido"] == "A")]
print(x["vehiculos"].describe())

print(puntos.sort_values("valor").head(5).to_string(index=False))