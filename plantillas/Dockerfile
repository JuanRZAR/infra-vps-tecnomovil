# Plantilla agnóstica (plantillas/README.md). Reemplaza cada <MARCADOR> con la fila
# de tu lenguaje en guia/02-preparar-proyecto.md, 2.4. Las líneas "# FIJO" no se cambian.

# --- Etapa 1: instala dependencias y compila (todas las herramientas) ---
FROM <IMAGEN_BUILD> AS build
WORKDIR /app
COPY <ARCHIVOS_DE_DEPENDENCIAS> ./
RUN <INSTALAR_DEPENDENCIAS>
COPY . .
# OPCIONAL: bórrala si tu lenguaje no compila
RUN <COMPILAR>

# --- Etapa 2: solo lo necesario para ejecutar ---
FROM <IMAGEN_FINAL>
WORKDIR /app
<VARIABLES_DE_PRODUCCION>
COPY --from=build <LO_QUE_NECESITA_EJECUTAR> <DESTINO>
# FIJO: el VPS ejecuta como 10001 (2.2, regla 4); la app solo escribe en /tmp o en data/
USER 10001:10001
# FIJO: tu app escucha en 0.0.0.0:8000 dentro del contenedor
EXPOSE 8000
CMD <SERVIDOR_PRODUCCION>
