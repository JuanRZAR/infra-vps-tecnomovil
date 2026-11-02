# Guía para subir un proyecto al VPS: empieza aquí

Esta guía es para un dev que quiere publicar su proyecto en el VPS del equipo, y para el asistente de IA (LLM) que lo ayude. No importa el lenguaje ni el framework: Node, Python, Java, Go, PHP, .NET, una web estática... todos siguen las mismas reglas.

Orden de lectura:

1. Este archivo: reglas del VPS y qué necesitas en tu equipo.
2. [02-preparar-proyecto.md](02-preparar-proyecto.md): cómo dejar tu proyecto listo.
3. [03-subir-proyecto.md](03-subir-proyecto.md): dominio, alta en el VPS, CI/CD y primer despliegue.

Si algo falla en el servidor y no es de tu proyecto (el VPS no responde, Cloudflare da 521/522), avisa al admin del VPS.

---

## Instrucciones para el LLM

Si eres un asistente de IA ayudando a un dev con esta guía, sigue estas reglas:

1. **Antes de nada, pregunta en qué sistema operativo trabaja el dev: Windows, macOS o Linux** (en Windows, también si usa PowerShell, Git Bash/WSL o PuTTY y WinSCP; las dos formas valen, la elige el dev). Da comandos solo para ese sistema.
2. **Lo que se puede saber leyendo el proyecto, no lo preguntes: analízalo.** Lenguaje, framework y versiones; si tiene frontend y si compila a estáticos o necesita servidor (SSR); qué base de datos usa; si sube archivos; si tiene tareas programadas o pesadas; cómo se ejecutan sus pruebas. Resume al dev lo que encontraste y pídele que lo confirme antes de seguir.
3. **Pregunta solo lo que no está en el código**, sin suponer las respuestas:
   - **Dominio**: ¿cuál es y dónde está registrado (Hostinger, Spaceship, GoDaddy, Cloudflare...)? Sin dominio propio no se puede publicar: díselo y detente.
   - **DNS**: ¿quién gestiona hoy el DNS de ese dominio y acepta pasarlo a Cloudflare? En este VPS es **obligatorio**: el servidor solo acepta tráfico web que llegue por Cloudflare, así su IP queda oculta y los ataques se filtran antes de llegar a cualquier proyecto. Si usa otro DNS, su dominio no funcionará. Si el dev no acepta, explícale el motivo y detente: la excepción solo la puede decidir el admin del VPS. Si el dominio tiene correo, avísale de que los registros de correo se conservan (ver [03-subir-proyecto.md](03-subir-proyecto.md), 3.1).
   - **Repositorio**: ¿es público o privado? Si tiene GitHub CLI, compruébalo con `gh repo view --json visibility`.
4. **Nunca inventes datos del servidor** (nombres, puertos, rutas, IP, usuarios). Los puertos salen de `projects.yml`; lo demás pídelo al dev, que lo consulta con el admin del VPS.
5. Antes de proponer el merge a `main`, recorre con el dev la **lista de verificación** final de [02-preparar-proyecto.md](02-preparar-proyecto.md) y haz que ejecute las **pruebas de rendimiento y consumo** (2.10). Como el VPS no pone límites por proyecto, revisa en el código los puntos de memoria, CPU y disco de 2.9 y señala los que encuentres. Lo marcado como **opcional** (por ejemplo, la caché de listas) no es obligatorio: analiza el proyecto, explica al dev si le conviene y por qué, y deja que decida.
6. No toques nada del VPS fuera de `/srv/apps/<su-proyecto>`. No cambies la configuración global (nginx global, firewall, Postgres, Docker): eso lo decide el admin.
7. Nunca pongas secretos (contraseñas, tokens, claves) en el código, en el Dockerfile, en el compose ni en el repositorio. Van en el `.env` del VPS o en los secretos de GitHub.
8. Explica en español, con pasos cortos, y comprueba cada paso antes de pasar al siguiente.

---

## Cómo funciona el VPS (en 1 minuto)

- Un solo servidor (8 GB de RAM, 2 CPU, 100 GB de disco) **compartido** entre varios proyectos.
- Todo el tráfico entra por **Cloudflare** a tu dominio, de ahí a **nginx** en el VPS, que lo envía a tu contenedor o sirve tu web estática.
- Tu backend corre en **Docker**. Tu web estática la sirve nginx directamente.
- **PostgreSQL** es compartido: tu proyecto tiene su propia base y su propio usuario; no ves las de otros.
- **Despliegue automático**: abres un PR (se ejecutan las pruebas), haces merge a `main` (pruebas de nuevo, se construye la imagen, se despliega). Sin cortes: la versión nueva arranca al lado de la vieja y solo cuando responde bien recibe el tráfico. Si falla, la vieja sigue sirviendo.
- Al servidor se entra solo por **Tailscale** (una red privada); el SSH no está abierto a Internet.

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
2. Acepta la invitación a Tailscale que te enviará el admin e inicia sesión.
3. Comprueba: `ssh <tu-usuario>@<nombre-del-vps-en-tailscale>` entra al servidor (con PuTTY: Host Name el nombre del VPS en Tailscale, Auto-login username tu usuario y tu `.ppk` en Connection > SSH > Auth > Credentials).

Sigue con [02-preparar-proyecto.md](02-preparar-proyecto.md).
