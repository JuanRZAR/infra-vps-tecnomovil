# Despliegue de producción de <TU_PROYECTO>

- **Qué se despliega**: <DESCRIPCIÓN BREVE (API, web, worker...)>.
- **Imagen**: construida desde `<RUTA>/Dockerfile` por GitHub Actions.
- **Salud**: `GET /health` (sin base de datos ni autenticación).
- **Base de datos**: <postgres compartido | propia en servicios.yml | ninguna>.
- **Migraciones**: `<COMANDO_MIGRACION>` (servicio `migrate`). Compatibles con la versión anterior (2.8).

## Variables (`.env` en el VPS)

| Variable | Para qué | Quién la genera |
|---|---|---|
| `DATABASE_URL` | Conexión a la base | admin (`vps-new-db`) |
| `SECRET_KEY` | <uso> | admin (`openssl rand -base64 48`) |

## Operación

- Comandos de administración dentro del contenedor activo: `docker exec -it <proyecto>-<color>-app-1 <comando>` (el color activo lo muestra `vps-status`).
