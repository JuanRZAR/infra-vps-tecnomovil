# Guía para subir un proyecto al VPS: empieza aquí

Esta guía es para un dev que quiere publicar su proyecto en el VPS del equipo, y para el asistente de IA (LLM) que lo ayude. No importa el lenguaje ni el framework: Node, Python, Java, Go, PHP, .NET, una web estática... todos siguen las mismas reglas.

Orden de lectura:

1. Este archivo: reglas del VPS y qué necesitas en tu equipo.
2. [02-preparar-proyecto.md](02-preparar-proyecto.md): cómo dejar tu proyecto listo y **validarlo** (pruebas de rendimiento y consumo). Sin la validación completa no se pasa al 3.
3. [03-subir-proyecto.md](03-subir-proyecto.md): dominio, alta en el VPS, CI/CD, primer despliegue, carga de datos existentes y monitoreo.

¿Ya subiste otro proyecto (o eres admin) y tienes usuario en el VPS, clave SSH y Tailscale? Lee las reglas de este archivo y salta «Qué necesitas en tu equipo»: empieza en el 02.

Si algo falla en el servidor y no es de tu proyecto (el VPS no responde, Cloudflare da 521/522), avisa al admin del VPS.

---

## Instrucciones para el LLM

Si eres un asistente de IA ayudando a un dev con esta guía, sigue estas reglas:

1. **Antes de nada, pregunta en un solo mensaje:**
   - Sistema operativo: Windows, macOS o Linux. En Windows, si usa PowerShell, Git Bash/WSL o PuTTY y WinSCP (las dos formas valen; la elige el dev). Da comandos solo para ese sistema.
   - ¿Tiene **Tailscale** instalado y con sesión iniciada en la cuenta del equipo?
   - ¿Tiene **usuario en el VPS** y le funciona `ssh <usuario>@<vps>` (o su sesión de PuTTY)? Que te diga el usuario.

   Si le falta Tailscale o el usuario, llévalo a «[Qué necesitas en tu equipo](#qué-necesitas-en-tu-equipo)» y **detente** hasta que entre por SSH: sin eso no puede consultar el VPS ni cargar datos.
2. **Lo que es del servidor no se le pregunta al admin.** Está en «[Datos fijos del VPS](#datos-fijos-del-vps)». Si falta algo o quieres confirmarlo, pide al dev que entre por SSH, ejecute los comandos de «[Consultar el VPS](#consultar-el-vps-solo-lectura)» y te pegue la salida. Al admin solo se le pide lo de «[Lo que solo hace el admin](#lo-que-solo-hace-el-admin)», todo junto en la entrega del 3.3.

   Si aun así la guía no responde algo, o el proyecto no encaja en ninguna forma de 2.0, **no improvises ni mandes la pregunta por chat**. Redacta con el dev un *issue* en `infra-vps-tecnomovil` (qué necesita, qué encontró en la guía y en el VPS, y qué propone) y espera. El admin lo responde añadiéndolo a la guía, para que nadie tenga que volver a preguntarlo.
3. **Lo que se puede saber leyendo el proyecto, no lo preguntes: analízalo.** Lenguaje, framework y versiones; si tiene frontend y si compila a estáticos o necesita servidor (SSR); qué base de datos usa; si sube archivos; si tiene tareas programadas o pesadas; cómo se ejecutan sus pruebas. Resume al dev lo que encontraste y pídele que lo confirme antes de seguir.
4. **Elige con el dev la forma de desplegar** con la tabla de [02-preparar-proyecto.md](02-preparar-proyecto.md), 2.0 (solo API, web estática + API, SSR + API...). De ella salen cuántos proyectos registra y cuántos puertos.
5. **Pregunta solo lo que no está en el código**, sin suponer las respuestas:
   - **Dominio**: ¿cuál es y dónde está registrado (Hostinger, Spaceship, GoDaddy, Cloudflare...)? Sin dominio propio no se puede publicar: díselo y detente.
   - **DNS**: ¿quién gestiona hoy el DNS de ese dominio y acepta pasarlo a Cloudflare? En este VPS es **obligatorio**: el servidor solo acepta tráfico web que llegue por Cloudflare, así su IP queda oculta y los ataques se filtran antes de llegar a cualquier proyecto. Si usa otro DNS, su dominio no funcionará. Si el dev no acepta, explícale el motivo y detente: la excepción solo la puede decidir el admin del VPS. Si el dominio tiene correo, avísale de que los registros de correo se conservan (ver [03-subir-proyecto.md](03-subir-proyecto.md), 3.1).
   - **Repositorio**: ¿es público o privado? Si tiene GitHub CLI, compruébalo con `gh repo view --json visibility`.
6. **Parte de [`plantillas/`](../plantillas/README.md)** para el Dockerfile, el compose, `deploy-dev` y el workflow, y adáptalas al lenguaje del proyecto con la tabla de 2.4. No copies archivos de otros proyectos del VPS: la fuente de verdad es este repositorio.
7. **Nunca inventes datos del servidor** (nombres, puertos, rutas, IP, usuarios). Salen de «Datos fijos del VPS», de `projects.yml` o de lo que el dev consulte en el VPS. La IP pública no está en ningún sitio: se la da el admin por privado.
8. **No pases a [03-subir-proyecto.md](03-subir-proyecto.md) hasta validar el 02.** Recorre con el dev la lista de verificación 2.11 punto por punto y pídele que te pegue las salidas reales, no un «ya está»: `vps-check` sin errores, las pruebas automáticas en verde y las de rendimiento y consumo de 2.10 (memoria en reposo, tras una carga y tras una segunda carga, p95, `OOM=false reinicios=0` y tamaño de la imagen). Como el VPS no pone límites por proyecto, revisa además en el código los puntos de memoria, CPU y disco de 2.9 y señala los que encuentres. Si algo no cumple, ayúdale a corregirlo y repite la prueba. Solo cuando todo esté validado, dile que es seguro subirlo y sigue con el 03. Lo marcado como **opcional** (por ejemplo, la caché de listas) no bloquea: analiza el proyecto, explica al dev si le conviene y por qué, y deja que decida.
9. **Segunda parada: la entrega al admin** ([03-subir-proyecto.md](03-subir-proyecto.md), 3.3). Guía al dev hasta preparar y enviar la entrega y **detente**: no sigas con 3.4 hasta que confirme que el admin le dio el OK y le devolvió los seis datos que pide esa sección.
10. En el VPS, el dev solo **consulta** (comandos de solo lectura) y trabaja en `/srv/apps/<su-proyecto>`. No cambies la configuración global (nginx global, firewall, Postgres, Docker, Tailscale) aunque su usuario tenga `sudo`: eso lo decide el admin.
11. Nunca pongas secretos (contraseñas, tokens, claves) en el código, en el Dockerfile, en el compose ni en el repositorio. Van en el `.env` del VPS o en los secretos de GitHub.
12. Explica en español, con pasos cortos, y comprueba cada paso antes de pasar al siguiente.

---

## Cómo funciona el VPS (en 1 minuto)

- Un solo servidor (8 GB de RAM, 2 CPU, 100 GB de disco) **compartido** entre varios proyectos.
- Todo el tráfico entra por **Cloudflare** a tu dominio, de ahí a **nginx** en el VPS, que lo envía a tu contenedor o sirve tu web estática.
- Tu backend corre en **Docker**. Tu web estática la sirve nginx directamente.
- **PostgreSQL** es compartido: tu proyecto tiene su propia base y su propio usuario; no ves las de otros.
- **Despliegue automático**: abres un PR (se ejecutan las pruebas), haces merge a `main` (pruebas de nuevo, se construye la imagen, se despliega). Sin cortes: la versión nueva arranca al lado de la vieja y solo cuando responde bien recibe el tráfico. Si falla, la vieja sigue sirviendo.
- Al servidor se entra solo por **Tailscale** (una red privada); el SSH no está abierto a Internet.

## Datos fijos del VPS

Lo que un proyecto necesita saber del servidor. No hace falta preguntarlo.

| Tema | Dato |
|---|---|
| Sistema | Ubuntu 24.04, hora en UTC. Docker con logs rotados (30 MB por contenedor) |
| Nombre del VPS | Su nombre en Tailscale, que se usa en `ssh`, en PuTTY (Host Name) y en Uptime Kuma y Beszel. Se ve en `tailscale status` desde tu PC (el equipo con `tag:vps`) o, en el VPS, con el primer comando de la tabla de abajo |
| Puertos | El proyecto número N de `projects.yml` usa `81N1` (azul) y `81N2` (verde). Toma el siguiente N libre; el admin lo confirma al revisar tu PR. **Cada proyecto con contenedor necesita su par.** La web estática no usa puertos |
| Dentro del contenedor | Tu app escucha en `8000` (se cambia con `puerto_interno` del workflow), corre como usuario `10001` y solo escribe en `data/` y `/tmp` |
| PostgreSQL | **17**, imagen oficial `postgres:17`, sin PostGIS. Las apps llegan a él como `postgres:5432` por la red Docker `infra`. Desde tu PC, solo por túnel SSH (3.7) |
| Tu base | **Un solo rol por proyecto**, dueño de su base, que usan la app y el servicio `migrate`. `CONNECTION LIMIT 20`, `statement_timeout 30s` e `idle_in_transaction_session_timeout 60s`. Puedes crear extensiones de confianza (`pgcrypto`, `pg_trgm`, `citext`, `uuid-ossp`...). Un rol extra para la app se hace como en [02](02-preparar-proyecto.md), 2.8; una extensión que exija superusuario se pide en la entrega (3.3) con el SQL exacto. Dos proyectos que leen los mismos datos comparten base con el mismo `bd:` en `projects.yml`, y entonces comparten también el límite de 20 conexiones |
| URL de la base | `postgresql://<rol>:<clave>@postgres:5432/<bd>`. La genera el admin y va en tu `.env`. Con SQLAlchemy y psycopg 3, el esquema es `postgresql+psycopg://` |
| Respaldos | `pg_dump` diario de tu base (se guardan 7 días) y otro antes de cada migración. La carpeta `data/` no se respalda: si tus archivos son importantes, avisa al admin |
| IP real del usuario | Todo entra por Cloudflare y nginx ya cambia la IP de Cloudflare por la del usuario. Tu app la recibe en **`X-Real-IP`** (y como último valor de `X-Forwarded-For`): Flask con `ProxyFix(x_for=1)`, Express con `trust proxy` en `1`. `CF-Connecting-IP` también llega, sin tocar. Úsala para logs y límites de intentos, no como control de acceso. La que ve tu servidor como IP de origen (por ejemplo `clientAddress` en Astro) es la de nginx, no la del usuario |
| HTTPS | Lo terminan Cloudflare y nginx. Tu app recibe HTTP con `X-Forwarded-Proto: https`. No redirijas a HTTPS desde tu app: haría un bucle |
| Límites de nginx | 20 peticiones/s por IP (ráfagas de hasta 40), cuerpo de 10 MB como máximo (se sube con un ajuste en `nginx/`), 60 s para responder |
| Correo | El VPS no tiene servidor de correo ni proveedor contratado. Usa uno externo (por ejemplo Brevo, Resend o Amazon SES) por SMTP en el 587 o 465, o por su API HTTP, con las credenciales en el `.env`. No uses el puerto 25 |
| Salida a Internet | Permitida (APIs externas, correo, pagos) |
| Monitoreo | Uptime Kuma en `https://<vps>.<tailnet>.ts.net:8443` y Beszel en `:8444`, con Tailscale activo y la cuenta compartida que te da el admin |

## Consultar el VPS (solo lectura)

Con Tailscale activo, entra con `ssh <tu-usuario>@<vps>` (o tu sesión de PuTTY). Estos comandos no cambian nada y bastan para resolver casi cualquier duda. El LLM te pide el que necesite y tú le pegas la salida:

| Para saber | Comando |
|---|---|
| Nombre completo del VPS en Tailscale | `tailscale status --json \| jq -r .Self.DNSName` |
| Proyectos, dominios, puertos y bases ya registrados | `cat /opt/vps/infra/projects.yml` |
| Puertos en uso en el servidor | `ss -ltn \| grep ':81'` |
| Versión exacta de Postgres | `docker exec postgres postgres --version` |
| Estado, versión activa y consumo de cada proyecto | `vps-status` |
| Logs de tu proyecto | `vps-logs <tu-proyecto>` |
| Memoria y disco libres | `free -h` y `df -h /` |
| Cómo publica nginx tu sitio (después del alta) | `cat /etc/nginx/sites-available/<tu-proyecto>.conf` |
| Historial de tus despliegues | `cat /srv/apps/<tu-proyecto>/despliegues.log` |

Si tu usuario no está en el grupo `docker`, los comandos con `docker` fallan con «permission denied»: pídeselo al admin.

## Lo que solo hace el admin

Tú (y tu LLM) no puedes hacerlo. Pídelo todo junto en la entrega del 3.3, salvo el primer punto, que va antes de empezar:

- Crear tu usuario en el VPS y darte acceso a Tailscale (con tu clave pública SSH).
- Aceptar tu PR a `projects.yml` y dar de alta el proyecto (`vps-new-project`): carpeta, sitios nginx, base y rol.
- Instalar el certificado Origin de tu dominio.
- Crear tu `.env` de producción con la URL de la base y las claves nuevas.
- Lo que va más allá de lo normal: un rol extra en la base, una extensión que exija superusuario o un ajuste de nginx (`deploy/deploy-produccion/nginx/`).
- Autorizar la clave del CI y crear su credencial de Tailscale.
- Añadir tus URLs a Uptime Kuma.

## Reglas de convivencia

1. **Sin límites, con responsabilidad**: tu proyecto no tiene topes de RAM, CPU ni disco. Por eso optimizarlo es tarea tuya, antes y después de desplegar (ver 2.9 y 2.10 de la guía): un descuido en tu proyecto (una fuga de memoria, fotos sin optimizar, logs sin fin) afecta a todos los proyectos del VPS.
2. **Nada escucha en Internet directamente**: tu contenedor solo escucha en `127.0.0.1` y nginx le pasa el tráfico.
3. **Un dominio propio por proyecto**, siempre a través de Cloudflare.
4. **Solo tocas tu carpeta** `/srv/apps/<tu-proyecto>`.
5. **Todo cambio entra por PR**. Nada de editar código directamente en el servidor.
6. **Tus logs y tus datos son tu responsabilidad**: que no crezcan sin límite.
7. Si algo tuyo afecta al VPS (consumo, errores en bucle), el admin puede limitarlo o detenerlo y te avisará.

## Qué necesitas en tu equipo

| Herramienta | Windows | macOS | Linux |
|---|---|---|---|
| Git | `winget install Git.Git` | `xcode-select --install` o `brew install git` | `sudo apt install git` (o el gestor de tu distro) |
| Docker | Docker Desktop (`winget install Docker.DockerDesktop`, con WSL 2) | Docker Desktop (`brew install --cask docker`) | Docker Engine: https://docs.docker.com/engine/install/ |
| Clave SSH | `ssh-keygen -t ed25519` en PowerShell, o PuTTYgen > EdDSA (Ed25519) > Generate > Save private key (`.ppk`) | `ssh-keygen -t ed25519` | `ssh-keygen -t ed25519` |
| Cliente SSH y archivos | `ssh`/`scp` en PowerShell, o PuTTY y WinSCP (`winget install PuTTY.PuTTY WinSCP.WinSCP`) | `ssh`/`scp` en Terminal | `ssh`/`scp` |
| Tailscale | `winget install tailscale.tailscale` | App Store o `brew install --cask tailscale` | https://tailscale.com/download/linux |
| GitHub CLI (opcional) | `winget install GitHub.cli` | `brew install gh` | https://github.com/cli/cli#installation |

Después:

1. Envía al admin tu clave **pública** (`~/.ssh/id_ed25519.pub`; en Windows `$env:USERPROFILE\.ssh\id_ed25519.pub`; con PuTTYgen, el texto del recuadro «Public key for pasting into OpenSSH authorized_keys file»). La privada nunca sale de tu equipo.
2. Abre Tailscale e inicia sesión con la **cuenta compartida del equipo** (te la indica el admin). No crees otra cuenta: el VPS solo está en esa red.
3. Comprueba: `ssh <tu-usuario>@<nombre-del-vps-en-tailscale>` entra al servidor (con PuTTY: Host Name el nombre del VPS en Tailscale, Auto-login username tu usuario y tu `.ppk` en Connection > SSH > Auth > Credentials).

Sigue con [02-preparar-proyecto.md](02-preparar-proyecto.md).
