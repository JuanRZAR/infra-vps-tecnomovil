# 2. Preparar tu proyecto para el VPS

Qué tiene que tener tu proyecto antes de subirlo. Vale para cualquier lenguaje. Al final hay una lista de verificación: no pidas el merge sin cumplirla entera.

---

## 2.0 La forma de tu proyecto

Cada proyecto es distinto. Elige la fila que le corresponde: de ella sale qué registras en `projects.yml` (3.2). Un proyecto es **una sola entrada** en `projects.yml` aunque tenga frontend y backend. En `projects.yml`, `dominios.web` es una web **estática** que sirve nginx, y `dominios.api` es **un dominio que va a un contenedor** (una API o un frontend con SSR).

| Forma | Ejemplo | Registro en `projects.yml` | Puertos |
|---|---|---|---|
| Solo API (con app móvil o sin ella) | Flask + APK | `dominios: { api }` | 1 par |
| Solo web estática | Astro estático, landing | `dominios: { web }`, sin `puertos` | Ninguno |
| Web estática + API | Angular/Vite/Astro estático + Flask/Node/Rust | `dominios: { web, api }` | 1 par |
| Frontend con SSR solo | Next que habla directo con la base | `dominios: { api }` | 1 par |
| Frontend con SSR + API | Astro SSR + Flask/Rust | `dominios: { api }` con el dominio del frontend. El frontend es `app` y la API, un servicio interno (abajo) | 1 par |

- **Prefiere la web estática** siempre que puedas: nginx la sirve sin gastar RAM. Usa SSR solo si de verdad necesitas renderizar en el servidor (páginas con sesión o contenido por usuario).
- **Un proceso por contenedor.** No se meten dos servidores (Astro y Flask) en el mismo contenedor: el healthcheck y el despliegue azul/verde solo vigilan uno.
- **La app móvil** no se despliega en el VPS: solo necesita la URL pública de la API. Si la distribuyes como APK, puedes publicarla en GitHub Releases desde tu propio workflow.
- Un subdominio vale como dominio del proyecto (por ejemplo `api.tudominio.com`).
- **¿Tu proyecto no encaja en ninguna fila?** No improvises una forma ni se lo preguntes al admin por chat: abre un *issue* en `infra-vps-tecnomovil` con la forma del proyecto (lenguajes, qué es público, qué habla con qué). El admin lo resuelve añadiéndolo a esta guía.

### Varios contenedores en un proyecto (servicios internos)

Para el frontend con SSR + API, o cualquier proyecto con más de un servidor propio en el mismo repositorio (un monorepo con `frontend/` y `backend/` vale):

- **`app` es el único contenedor público**: recibe el tráfico de nginx en su puerto y usa `image: ${IMAGE}`. Si el navegador necesita la API, `app` se la reenvía (por ejemplo, una ruta `/api/...` en el frontend que llama al backend).
- **Cada servicio interno** usa su propia imagen `${IMAGE_<NOMBRE>}` (`api` → `${IMAGE_API}`), no publica puertos y escucha en `8000`. Cumple las mismas reglas que `app` (usuario `10001`, `env_file`, `restart`) y debe tener `healthcheck`: el despliegue espera a que todos estén sanos antes de pasarles tráfico.
- **Se hablan por el nombre del servicio**, en la red `default` de su versión: `app` llama a `http://api:8000`. Cada versión (azul y verde) tiene su red `default` propia, así que el frontend nuevo siempre habla con el backend nuevo. Nunca llames a `127.0.0.1` (es el propio contenedor) ni a `81N1`/`81N2`.
- Quien necesita el Postgres compartido se une también a `infra`. Al declarar `networks:` en un servicio, incluye `default` o dejará de ver a los demás.
- `migrate` usa la imagen que tiene tus migraciones (normalmente `${IMAGE_API}`).
- `/health` de `app` **no** llama al servicio interno (2.6).
- La IP real del usuario llega a `app` en `X-Real-IP`. Si el servicio interno la necesita, `app` debe reenviarla en esa misma cabecera.

```yaml
# deploy/deploy-produccion/compose.yml (frontend con SSR + API)
services:
  app:                                  # frontend: lo de la plantilla, sin networks (solo default)
    image: ${IMAGE}
    # ...user, env_file, ports, restart, healthcheck de la plantilla...
  api:                                  # backend interno
    image: ${IMAGE_API}
    user: "10001:10001"
    env_file: /srv/apps/${PROYECTO}/.env
    read_only: true
    tmpfs: [/tmp]
    restart: unless-stopped
    security_opt: ["no-new-privileges:true"]
    cap_drop: [ALL]
    healthcheck:
      test: <COMANDO_SALUD>             # contra http://127.0.0.1:8000/health dentro de su contenedor
      interval: 15s
      timeout: 3s
      retries: 3
      start_period: 30s
    networks: [default, infra]          # default: habla con app; infra: Postgres
  migrate:
    profiles: ["migrate"]
    image: ${IMAGE_API}
    user: "10001:10001"
    env_file: /srv/apps/${PROYECTO}/.env
    command: <COMANDO_MIGRACION>
    networks: [infra]
networks:
  infra:
    external: true
```

Y en tu workflow, el flujo compartido construye cada imagen interna con la entrada `imagenes`, una línea por servicio (`nombre dockerfile contexto [ruta_salud]`):

```yaml
    with:
      proyecto: <tu-proyecto>
      dockerfile: frontend/Dockerfile   # la de app
      contexto: frontend
      imagenes: |
        api backend/Dockerfile backend
```

Cada imagen interna pasa por hadolint y Trivy, y se arranca sola en la prueba de consumo (sin base de datos ni secretos, con `env_prueba`): su `/health` debe responder igual que el de `app`. La imagen se publica como `ghcr.io/<repo>-<nombre>:<sha>`. Las variables de todos los servicios van en el mismo `.env` del VPS.

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
- **Punto de partida**: copia los archivos de [`plantillas/`](../plantillas/README.md) (Dockerfile, `.dockerignore`, `deploy-dev/`, `deploy-produccion/` y el workflow) y adapta sus `<MARCADORES>` a tu lenguaje con la tabla de 2.4. Sirven para cualquier lenguaje; no copies archivos de otros proyectos.

## 2.2 Las reglas del VPS

`vps-check` revisa estas reglas en cada PR y en cada despliegue, y rechaza el que no las cumpla.

| N.º | Regla | Por qué |
|---|---|---|
| 1 | El servicio principal del `compose.yml` se llama `app` y usa `image: ${IMAGE}` (sin `build:`). Los servicios internos usan `${IMAGE_<NOMBRE>}` (2.0) | El VPS no compila: descarga las imágenes ya construidas por GitHub Actions |
| 2 | Único puerto permitido: `"127.0.0.1:${HOST_PORT}:<puerto interno>"` | Nada queda expuesto a Internet saltándose nginx y el firewall |
| 3 | `app` tiene `healthcheck` y `restart: unless-stopped` | Sin healthcheck, el despliegue no sabe si la versión nueva funciona |
| 4 | El contenedor corre como `user: "10001:10001"` | Si alguien explota tu app, no es root |
| 5 | Prohibido: `privileged`, `network_mode: host`, `pid: host`, `cap_add`, `devices`, montar `docker.sock` | Cualquiera de ellos da control del servidor entero |
| 6 | Volúmenes solo dentro de `/srv/apps/${PROYECTO}/data/` | No se toca nada fuera de tu carpeta |
| 7 | Variables con `env_file: /srv/apps/${PROYECTO}/.env`; nada de secretos escritos en el compose | Los secretos no viajan en el repositorio |
| 8 | Redes: `infra` (solo si usas el Postgres compartido), `default` (entre `app` y tus servicios internos, 2.0) y `${PROYECTO}-red` (para tus servicios de `servicios.yml`) | Tu Redis o tu base no quedan al alcance de otros proyectos |

**No hay límites de RAM, CPU ni disco por proyecto.** Cada proyecto consume lo que necesita: uno puede usar 2,5 GB y otro 500 MB. A cambio, cada dev es responsable de que su proyecto consuma lo justo y de vigilarlo antes y después de desplegar (2.9 y 2.10). Los 8 GB de RAM y los 100 GB de disco son de todos: que sobre espacio no es motivo para gastarlo.

## 2.3 `deploy/deploy-produccion/compose.yml`

Copia [`plantillas/deploy-produccion/compose.yml`](../plantillas/deploy-produccion/compose.yml). Ya cumple las 8 reglas: las líneas `# FIJO` no se tocan. Solo rellenas:

- `<COMANDO_SALUD>`: el healthcheck, con una herramienta que **exista en tu imagen** (tabla de 2.4). Ojo: `python:slim` y las imágenes distroless no traen `wget` ni `curl`.
- `<COMANDO_MIGRACION>`: si tu base necesita migraciones; si no, borra el servicio `migrate`.
- `volumes`: solo si guardas archivos; si no, bórralo.

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

### Valores para los marcadores de las plantillas

Comprueba qué trae tu imagen final antes de elegir el healthcheck: `docker run --rm --entrypoint sh <imagen> -c "command -v curl wget"`.

| Tecnología | `<COMANDO_SALUD>` (compose) | `<COMANDO_MIGRACION>` (ejemplos) | `<PASOS_DE_PRUEBA>` (workflow) |
|---|---|---|---|
| Node | `["CMD", "node", "-e", "fetch('http://127.0.0.1:8000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]` | `["npx", "prisma", "migrate", "deploy"]` | `actions/setup-node` + `npm ci` + `npm test` |
| Python | `["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]` | `["alembic", "upgrade", "head"]`, `["python", "manage.py", "migrate"]` | `actions/setup-python` + `pip install -r ...` + `pytest` |
| Java | `["CMD", "curl", "-fsS", "http://127.0.0.1:8000/health"]` si la imagen trae `curl`; si no, instálalo en la etapa final | Flyway o Liquibase (su comando o un modo de tu jar) | `actions/setup-java` + `./mvnw test` o `./gradlew test` |
| Go (distroless) | `["CMD", "/app/servidor", "-salud"]`: una opción del propio binario que pide `/health` | `["/app/servidor", "-migrar"]` o la herramienta que uses (goose, migrate) | `actions/setup-go` + `go test ./...` |
| PHP (FrankenPHP) | `["CMD", "curl", "-fsS", "http://127.0.0.1:8000/health"]` (compruébalo en tu imagen) | `["php", "artisan", "migrate", "--force"]` | `shivammathur/setup-php` + `composer install` + `php artisan test` |
| .NET | `aspnet` no trae `curl` ni `wget`: instala `curl` en la etapa final o añade un modo `--salud` a tu app | el bundle de EF (`./efbundle`) | `actions/setup-dotnet` + `dotnet test` |

Si tu tecnología no está, usa el equivalente y explica la elección en `deploy/deploy-produccion/README.md`.

Ejemplo de la plantilla ya adaptada (Node):

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
USER 10001:10001
EXPOSE 8000
CMD ["node", "dist/main.js"]
```

Parte de [`plantillas/Dockerfile`](../plantillas/Dockerfile) y [`plantillas/.dockerignore`](../plantillas/.dockerignore).

## 2.5 Web estática

Si tu frontend compila a archivos estáticos (Angular, React con Vite, Vue, Svelte, Astro estático), **no necesita contenedor**: GitHub Actions lo compila y nginx sirve la carpeta resultante.

- Indica la carpeta de salida (por ejemplo `dist/`, `build/`, `www/browser/`).
- Las variables del frontend son **públicas**: cualquiera puede leerlas en el navegador. Nunca pongas ahí claves ni contraseñas.
- La URL de tu API se fija al compilar (por ejemplo `https://api.tudominio.com`).
- Si usa rutas del lado del cliente (SPA), la plantilla `web.conf` ya devuelve `index.html` para rutas desconocidas.

## 2.6 Endpoint `/health`

- Responde `200` rápido (menos de 100 ms) si el proceso puede atender peticiones.
- **No** hace consultas pesadas. Recomendado: no consultar la base **ni llamar a otros servicios** (tu backend, APIs externas). Si la base o ese servicio caen un momento y `/health` depende de ellos, Docker reiniciaría tu app en bucle sin motivo.
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

### Un rol solo para la app (opcional)

Por defecto, la app y `migrate` usan el mismo rol, dueño de la base. Si quieres que la app use un rol con menos permisos (por ejemplo, que solo ejecute funciones), el reparto es este:

- **El admin** crea el rol y le deja conectarse. Lo pides en la entrega (3.3) con el nombre y el límite de conexiones:

  ```sql
  CREATE ROLE <rol_app> LOGIN PASSWORD '<aleatoria>' CONNECTION LIMIT 10;
  GRANT CONNECT ON DATABASE <bd> TO <rol_app>;
  ALTER ROLE <rol_app> SET statement_timeout = '30s';
  ALTER ROLE <rol_app> SET idle_in_transaction_session_timeout = '60s';
  ```

- **Tú** pones el resto de permisos en una **migración**, que corre como el dueño. Así se aplican en orden y vuelven solos si hay que recrear la base. Por ejemplo, para un esquema de funciones:

  ```sql
  GRANT USAGE ON SCHEMA <esquema> TO <rol_app>;
  GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA <esquema> TO <rol_app>;                -- las que ya existen
  ALTER DEFAULT PRIVILEGES IN SCHEMA <esquema> GRANT EXECUTE ON FUNCTIONS TO <rol_app>; -- las futuras
  REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA <esquema> FROM PUBLIC;               -- Postgres da EXECUTE a PUBLIC por defecto
  ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
  ```

- Cada función `SECURITY DEFINER` lleva `SET search_path = <esquema>, pg_temp`; sin eso, quien la ejecuta puede desviarla a objetos suyos.
- `app` y `migrate` leen el mismo `.env`: usa **dos variables**, por ejemplo `DATABASE_URL` (rol de la app) y `DATABASE_URL_MIGRACION` (dueño), y que tu comando de migración lea la segunda.
- La cuenta de conexiones (2.9) se hace contra el límite del rol de la app, no contra 20.

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
