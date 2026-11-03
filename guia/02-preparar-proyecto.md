# 2. Preparar tu proyecto para el VPS

Qué tiene que tener tu proyecto antes de subirlo. Vale para cualquier lenguaje. Al final hay una lista de verificación: no pidas el merge sin cumplirla entera.

---

## 2.1 Estructura de carpetas obligatoria

```
<tu-proyecto>/
├─ deploy/
│  ├─ deploy-dev/            levantar el proyecto con Docker en tu equipo, como en producción
│  │  ├─ compose.yml
│  │  └─ .env.example
│  └─ deploy-produccion/     lo que necesita el VPS
│     ├─ compose.yml         tu app: imagen, healthcheck (obligatorio)
│     ├─ servicios.yml       solo si traes servicios con estado propios: otra base, Redis (opcional)
│     ├─ .env.example        nombres de las variables de producción, sin valores
│     ├─ nginx/              opcional: solo ajustes extra (p. ej. un location más); el admin los revisa e instala en /etc/nginx/vps-extra/
│     └─ README.md           qué despliega, qué variables usa, cómo se migra la base
├─ .github/workflows/deploy.yml     llama al flujo compartido (GitHub exige esta ruta)
└─ <tu código>                el Dockerfile va junto al código que construye (p. ej. backend/Dockerfile)
```

- **`deploy-dev`**: sirve para probar en tu equipo la misma imagen que irá a producción. Si tu proyecto usa una base local, puede ir aquí en un contenedor o apuntar a la base que ya tengas.
- **`deploy-produccion`**: lo único que lee el VPS. El `.env` real **no** está en el repositorio: el admin lo crea en el VPS (`/srv/apps/<tu-proyecto>/.env`).

## 2.2 Las reglas del VPS

`vps-check` revisa estas reglas en cada PR y en cada despliegue, y rechaza el que no las cumpla.

| N.º | Regla | Por qué |
|---|---|---|
| 1 | El servicio principal del `compose.yml` se llama `app` y usa `image: ${IMAGE}` (sin `build:`) | El VPS no compila: descarga la imagen ya construida por GitHub Actions |
| 2 | Único puerto permitido: `"127.0.0.1:${HOST_PORT}:<puerto interno>"` | Nada queda expuesto a Internet saltándose nginx y el firewall |
| 3 | `app` tiene `healthcheck` y `restart: unless-stopped` | Sin healthcheck, el despliegue no sabe si la versión nueva funciona |
| 4 | El contenedor corre como `user: "10001:10001"` | Si alguien explota tu app, no es root |
| 5 | Prohibido: `privileged`, `network_mode: host`, `pid: host`, `cap_add`, `devices`, montar `docker.sock` | Cualquiera de ellos da control del servidor entero |
| 6 | Volúmenes solo dentro de `/srv/apps/${PROYECTO}/data/` | No se toca nada fuera de tu carpeta |
| 7 | Variables con `env_file: /srv/apps/${PROYECTO}/.env`; nada de secretos escritos en el compose | Los secretos no viajan en el repositorio |
| 8 | Redes: `infra` (solo si usas el Postgres compartido) y `${PROYECTO}-red` (para tus servicios propios) | Tu Redis o tu base no quedan al alcance de otros proyectos |

**No hay límites de RAM, CPU ni disco por proyecto.** Cada proyecto consume lo que necesita: uno puede usar 2,5 GB y otro 500 MB. A cambio, cada dev es responsable de que su proyecto consuma lo justo y de vigilarlo antes y después de desplegar (2.9 y 2.10). Los 8 GB de RAM y los 100 GB de disco son de todos: que sobre espacio no es motivo para gastarlo.

## 2.3 Plantilla de `deploy/deploy-produccion/compose.yml`

```yaml
services:
  app:
    image: ${IMAGE}
    user: "10001:10001"
    env_file: /srv/apps/${PROYECTO}/.env
    ports:
      - "127.0.0.1:${HOST_PORT}:8000"      # tu app escucha en 8000 dentro del contenedor
    pids_limit: 200
    restart: unless-stopped
    stop_grace_period: 20s
    security_opt: ["no-new-privileges:true"]
    cap_drop: [ALL]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:8000/health"]   # usa una herramienta que exista en tu imagen
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 30s
    volumes:
      - /srv/apps/${PROYECTO}/data/uploads:/app/uploads   # solo si guardas archivos
    networks: [infra]

  migrate:                                  # opcional: se ejecuta una vez antes de cada despliegue
    profiles: ["migrate"]
    image: ${IMAGE}
    user: "10001:10001"
    env_file: /srv/apps/${PROYECTO}/.env
    command: ["<comando de migración>"]     # p. ej. npx prisma migrate deploy, alembic upgrade head
    networks: [infra]

networks:
  infra:
    external: true
```

`IMAGE`, `HOST_PORT` y `PROYECTO` los pone el VPS al desplegar; no los definas tú.

**Servicios propios con estado** (MySQL, MongoDB, Redis...) van en `servicios.yml`, nunca en `compose.yml`. El despliegue sin cortes levanta dos copias de `compose.yml` a la vez: dos bases sobre los mismos archivos los corrompen. `servicios.yml` sigue las mismas reglas (sin puertos publicados, datos en `data/`, red `${PROYECTO}-red`) y se aplica sin duplicar. Cambiar la versión mayor de una base exige migrar sus datos: habla antes con el admin.

## 2.4 Dockerfile

Reglas para cualquier lenguaje:

- **Multi-etapa**: una etapa compila con todas las herramientas; la final solo lleva lo necesario para ejecutar.
- **Servidor de producción**, nunca el de desarrollo: nada de `flask run`, `npm run dev`, `ng serve`, `php artisan serve`, `manage.py runserver`.
- **Sin secretos** dentro de la imagen. Incluye un `.dockerignore` con `.git`, `node_modules`, `.env*`, `*.log`, carpetas de compilación locales y de pruebas.
- La app **escribe solo** en las carpetas montadas de `data/` o en `/tmp`, nunca dentro de su propio código (corre como usuario 10001 y no tiene permiso).
- Responde a **SIGTERM** cerrando conexiones en menos de 20 s.

| Tecnología | Imagen final sugerida | Servidor de producción | Cuidado con |
|---|---|---|---|
| Node (Express, Nest, Fastify) | `node:<LTS>-alpine` | `node dist/main.js` | `NODE_ENV=production`; `npm ci --omit=dev` |
| Python (Flask, Django, FastAPI) | `python:<versión>-slim` | gunicorn (Flask/Django) o gunicorn con workers uvicorn (FastAPI) | 2 workers por defecto: cada uno ocupa RAM; `DEBUG` apagado |
| Java (Spring Boot) | `eclipse-temurin:<versión>-jre` | `java -Xmx<valor> -jar app.jar` | Sin `-Xmx`, la JVM puede reservar hasta el 25 % de la RAM del servidor (2 GB). Fija el valor según lo que mida tu prueba de consumo |
| Go | `gcr.io/distroless/static-debian12` | el binario | Sin shell: el healthcheck debe ser una opción del propio binario |
| PHP (Laravel, Symfony) | `dunglas/frankenphp` | FrankenPHP (sirve HTTP en un solo contenedor) | `APP_DEBUG=false`; caché de configuración en el build |
| .NET | `mcr.microsoft.com/dotnet/aspnet:<versión>` | Kestrel con `ASPNETCORE_URLS=http://+:8000` | Modo `Production` |
| Frontend con SSR (Next, Nuxt, Remix) | `node:<LTS>-alpine` | el servidor del framework en modo producción (Next: `output: "standalone"`) | Es un contenedor más, con las mismas reglas |

Ejemplo completo (Node):

```dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=8000
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
EXPOSE 8000
CMD ["node", "dist/main.js"]
```

## 2.5 Web estática

Si tu frontend compila a archivos estáticos (Angular, React con Vite, Vue, Svelte, Astro estático), **no necesita contenedor**: GitHub Actions lo compila y nginx sirve la carpeta resultante.

- Indica la carpeta de salida (por ejemplo `dist/`, `build/`, `www/browser/`).
- Las variables del frontend son **públicas**: cualquiera puede leerlas en el navegador. Nunca pongas ahí claves ni contraseñas.
- La URL de tu API se fija al compilar (por ejemplo `https://api.tudominio.com`).
- Si usa rutas del lado del cliente (SPA), la plantilla `web.conf` ya devuelve `index.html` para rutas desconocidas.

## 2.6 Endpoint `/health`

- Responde `200` rápido (menos de 100 ms) si el proceso puede atender peticiones.
- **No** hace consultas pesadas. Recomendado: no consultar la base. Si la base cae un momento y `/health` depende de ella, Docker reiniciaría tu app en bucle sin motivo.
- Sin autenticación y sin datos sensibles en la respuesta.

## 2.7 Variables de entorno

- Toda la configuración que cambia entre tu equipo y producción va en variables: URL de la base, claves, orígenes CORS, dominios.
- `deploy/deploy-produccion/.env.example` lista los nombres sin valores. El admin crea el `.env` real en el VPS con los valores (la URL de Postgres se la da `vps-new-db`).
- Genera claves nuevas para producción (`openssl rand -base64 48`); nunca reutilices las de desarrollo.

## 2.8 Migraciones de base de datos compatibles

Durante unos segundos conviven la versión vieja y la nueva de tu app sobre la **misma base**. Por eso cada migración debe funcionar con las dos:

- Añadir una tabla o una columna que admita nulos (o con valor por defecto): sin problema.
- **Renombrar o borrar** una columna: en dos despliegues. Primero se añade la nueva y el código usa las dos; en un despliegue posterior se borra la vieja.
- Añadir `NOT NULL` a una columna existente: primero se rellenan los datos, después la restricción.
- Índices sobre tablas grandes en Postgres: `CREATE INDEX CONCURRENTLY`.

Antes de cada migración el VPS guarda un volcado de tu base.

## 2.9 Lo que suele dañar el VPS sin que nadie lo note

Como no hay límites por proyecto, un descuido en uno afecta a todos. Revisa cada punto: son los errores que hacen que un proyecto funcione bien en tu equipo y ralentice o llene el servidor.

**Memoria y CPU**

- **Modo depuración o servidor de desarrollo en producción**: lento, inseguro y consume más memoria.
- **Demasiados workers o hilos**: cada worker es una copia de tu app en RAM. Empieza con 2.
- **Conexiones a la base**: `pool` × workers × 2 (las dos versiones conviviendo) debe quedar por debajo de 20, el límite de tu usuario en Postgres.
- **Listas sin paginar** y consultas sin índice: una tabla que crece convierte una página en segundos de CPU.
- **Cachés en memoria sin tamaño máximo** y fugas de memoria: la RAM crece hasta agotar la del servidor y Linux empieza a matar procesos, posiblemente de otros proyectos.
- **Bucles de tareas sin pausa** (sondeos cada pocos milisegundos, reintentos infinitos sin espera).
- **Peticiones sin tiempo máximo** hacia servicios externos: se acumulan hilos bloqueados.

**Disco**

- **Imágenes subidas sin optimizar**: redimensiona (por ejemplo, lado máximo 1200 px), convierte a WebP, limita el tamaño por archivo (`client_max_body_size` en tu `nginx/` y también en tu app) y pon una cuota total en tu app.
- **Archivos que nunca se borran**: fotos reemplazadas, exportaciones temporales, archivos de usuarios eliminados. Bórralos o programa su limpieza.
- **Logs en nivel DEBUG** o archivos de log dentro del contenedor: escribe a la salida estándar y en nivel INFO (Docker ya rota esos logs).
- **Imágenes Docker grandes**: cada despliegue descarga la imagen y el VPS guarda las 3 últimas. Una imagen de 1,5 GB son 4,5 GB solo en versiones guardadas. Usa multi-etapa y `.dockerignore`.
- **Respaldos o volcados propios dentro de `data/`**: el VPS ya hace los de la base.
- Haz la cuenta: si tu app sube 50 MB al día, son 18 GB al año.
- **Tareas programadas duplicadas**: durante el despliegue hay dos copias de tu app. Si cada una lanza una tarea programada, se ejecuta dos veces. Hazlas idempotentes o ejecútalas fuera del contenedor web.

**Recomendado, opcional: no volver a pedir lo mismo a la base**

El usuario abre la lista de productos (consulta a la base), va a otra página, vuelve a productos y la consulta se repite aunque nada cambió. No todos los proyectos lo necesitan: decide con tu LLM, que debe analizar tu proyecto (cuántos usuarios, cuánto cambian los datos, cuánto tardan esas consultas, si la app ya guarda los datos en el frontend) y recomendarte si conviene y cuál de estas opciones, de menos a más trabajo:

- **Frontend**: guardar en memoria la lista ya cargada y mostrarla al instante al volver; refrescarla en segundo plano solo si pasó cierto tiempo o si el propio usuario creó, editó o borró algo.
- **API**: responder con `ETag` o `Last-Modified` y atender `If-None-Match`; si nada cambió, devuelve `304` sin cuerpo y casi sin trabajo. Para datos que cambian poco (catálogos), `Cache-Control: max-age=60` o similar.
- **Servidor**: para consultas caras y muy repetidas, una caché con tiempo de expiración (en memoria con tamaño máximo, o Redis en `servicios.yml`).

## 2.10 Pruebas de rendimiento y consumo (antes del primer PR y cuando la app crezca)

Con Docker en tu equipo (los comandos valen en PowerShell, Git Bash, macOS y Linux):

```bash
docker build -t miapp:prueba -f <ruta>/Dockerfile <ruta>
docker image ls miapp:prueba                                   # tamaño: cuanto menos, mejor (ideal menos de 500 MB)

docker run -d --name prueba --user 10001:10001 \
  -p 127.0.0.1:8000:8000 --env-file deploy/deploy-dev/.env miapp:prueba
curl http://127.0.0.1:8000/health                              # 200
docker stats prueba --no-stream                                # memoria en reposo
```

Carga corta con [oha](https://github.com/hatoo/oha#installation) contra un endpoint de lectura real:

```bash
oha -z 30s -c 20 http://127.0.0.1:8000/<endpoint-de-lectura>
docker inspect prueba --format 'OOM={{.State.OOMKilled}} reinicios={{.RestartCount}}'
docker stats prueba --no-stream                                # memoria tras la carga
oha -z 30s -c 20 http://127.0.0.1:8000/<endpoint-de-lectura>   # segunda carga, igual a la primera
docker stats prueba --no-stream                                # debe quedar parecida a la anterior
docker rm -f prueba
```

Si tu app usa base de datos, haz la carga contra un endpoint que la consulte: así también se ve si las conexiones vuelven al pool (si la segunda carga da errores o se queda colgada, alguna petición no devuelve su conexión).

Qué mirar:
- **Memoria**: cuánto usa en reposo y tras la carga, y que no crezca sin parar entre una carga y la siguiente (eso es una fuga).
- **Tiempo de respuesta**: que el p95 de `oha` sea razonable para tu app (como referencia, menos de 1,5 s).
- **Reinicios**: ninguno.
- **Disco**: tamaño de la imagen y cuánto crecerá `data/` con el uso real (fotos, archivos), según la cuenta de 2.9.

Si algo sale mal, optimiza: workers, consultas, índices, imágenes, caché (2.9).

GitHub Actions repite esta prueba en cada PR y **te muestra el resultado** (memoria, CPU, p95, tamaño de imagen) en el resumen del job. Solo bloquea el merge si la app se cae o no responde a `/health`. Lo demás es información para que optimices. Después de desplegar, revisa de vez en cuando el consumo real de tu proyecto con `vps-status` y repite la prueba cuando tu app crezca: lo que hoy va bien con 100 registros puede ir mal con 100.000.

## 2.11 Lista de verificación (sin ella completa no se pasa al 3)

Tu LLM te pedirá la salida real de cada prueba, no un «ya está». Si algo no cumple, se corrige y se repite.

- [ ] Carpetas `deploy/deploy-dev` y `deploy/deploy-produccion` con sus archivos.
- [ ] `compose.yml` cumple las 8 reglas (2.2); servicios con estado en `servicios.yml`. Compruébalo en tu equipo con `python3 <ruta-a>/infra-vps-tecnomovil/herramientas/vps-check deploy/deploy-produccion/compose.yml <tu-proyecto>` (necesita PyYAML): debe terminar sin errores.
- [ ] Dockerfile multi-etapa, servidor de producción, `.dockerignore`, sin secretos.
- [ ] `/health` rápido y sin base de datos.
- [ ] Variables en `.env.example`; ningún secreto en el repositorio ni en el frontend.
- [ ] Migraciones compatibles con la versión anterior.
- [ ] Puntos de memoria, CPU y disco de 2.9 revisados; la caché de listas, evaluada con tu LLM (opcional).
- [ ] Pruebas de rendimiento y consumo hechas y revisadas (2.10): `/health` da 200, sin OOM ni reinicios, la memoria no crece entre la primera y la segunda carga, p95 razonable, imagen de tamaño razonable.
- [ ] Pruebas automáticas del proyecto en verde.
- [ ] Sin vulnerabilidades críticas con solución en tus dependencias (GitHub Actions las busca con Trivy en cada PR y bloquea si las hay).

Con todo marcado y validado, tu proyecto es seguro para el VPS: sigue con [03-subir-proyecto.md](03-subir-proyecto.md).
