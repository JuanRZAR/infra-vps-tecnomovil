# Plantillas para tu proyecto

Punto de partida para cualquier lenguaje. Copia estos archivos a tu proyecto y adáptalos. No copies archivos de otros proyectos del VPS: la fuente de verdad es esta carpeta.

| Archivo | Va en tu proyecto como |
|---|---|
| `Dockerfile` | junto al código que construye (p. ej. `Dockerfile` o `backend/Dockerfile`) |
| `.dockerignore` | junto al Dockerfile (en la carpeta de contexto del build) |
| `deploy-produccion/` | `deploy/deploy-produccion/` |
| `deploy-dev/` | `deploy/deploy-dev/` |
| `github-workflow-deploy.yml` | `.github/workflows/deploy.yml` |

## Cómo se adaptan

- **`<MARCADOR>`**: hay que reemplazarlo. Los valores para cada lenguaje están en [guia/02-preparar-proyecto.md](../guia/02-preparar-proyecto.md), 2.4 («Valores para los marcadores»). Si tu lenguaje no está en la tabla, usa el equivalente y explica la elección en `deploy/deploy-produccion/README.md`.
- **`# FIJO`**: no se cambia. Son reglas del VPS que comprueba `vps-check` (2.2).
- **`# OPCIONAL`**: bórralo si tu proyecto no lo necesita.
- Al terminar no debe quedar ningún `<` `>` de marcador. Compruébalo con `grep -rn "<[A-Z_]*>" Dockerfile deploy .github`.

## Instrucciones para el LLM

1. Analiza el proyecto (lenguaje, framework, gestor de dependencias, base de datos, migraciones, pruebas) y elige la fila de la tabla 2.4 que corresponde.
2. Rellena todos los marcadores con valores reales del proyecto. No inventes comandos: comprueba que existen (`package.json`, `requirements.txt`, `pom.xml`, `go.mod`...).
3. Comprueba qué herramientas trae la imagen final antes de elegir el healthcheck: `docker run --rm --entrypoint sh <imagen> -c "command -v curl wget"`. Si no hay shell (distroless), el healthcheck debe ser una opción del propio binario.
4. No cambies las líneas `# FIJO`. Valida con `vps-check` (2.11).
