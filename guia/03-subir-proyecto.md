# 3. Subir tu proyecto al VPS

Requisito: la lista de verificación 2.11 de [02-preparar-proyecto.md](02-preparar-proyecto.md) completa y validada con tu LLM. Aquí: dominio, alta en el VPS, GitHub Actions, primer despliegue, carga de datos existentes y monitoreo. El VPS ya está configurado: nada de este documento cambia el servidor, solo da de alta tu proyecto.

Tú (con tu LLM) haces 3.1 y 3.2 y preparas la **entrega al admin** (3.3). Ahí **te detienes**: el admin da de alta tu proyecto en el servidor y te devuelve unos datos. Con su OK sigues desde 3.4.

---

## 3.1 Tu dominio en Cloudflare

Todo proyecto del VPS entra por Cloudflare con **su propio dominio**. Cloudflare oculta la IP del servidor y filtra ataques; el VPS rechaza cualquier tráfico web que no venga de Cloudflare.

### Si el dominio aún no está en Cloudflare (Hostinger, Spaceship, GoDaddy, Namecheap...)

1. Crea una cuenta gratuita en Cloudflare > **Add a domain** > plan Free.
2. Cloudflare importa los registros DNS que encuentre. **Revisa los de correo** (`MX`, `TXT` con SPF/DKIM/DMARC): si tu dominio tiene correo (por ejemplo, de Hostinger), esos registros deben quedar tal cual y en gris (DNS only), o el correo deja de funcionar.
3. Si tu registrador tiene **DNSSEC** activado, desactívalo antes del cambio.
4. Cambia los nameservers por los dos que te da Cloudflare:
   - **Hostinger**: hPanel > Dominios > tu dominio > DNS / Nameservers > Cambiar nameservers > «Usar nameservers personalizados» > pega los dos de Cloudflare > Guardar.
   - **Otro registrador**: busca «Nameservers» o «DNS personalizados» en la gestión del dominio; es el mismo cambio.
5. Espera a que Cloudflare marque el dominio como **Active** (minutos u horas).

### Configuración en Cloudflare (siempre)

1. **DNS > Records**, con la nube naranja (Proxied). La IP te la da el admin en privado:

| Tipo | Nombre | Para qué |
|---|---|---|
| A | `@` (tu dominio) | La web |
| A | `www` | Redirige a la web |
| A | `api` | La API (si la tienes) |

2. **SSL/TLS** > modo **Full (strict)**; Edge Certificates > **Always Use HTTPS** y TLS mínimo 1.2.
3. **SSL/TLS > Origin Server** > **Create Certificate** (RSA, `tudominio.com` y `*.tudominio.com`, 15 años). Guarda el certificado y la clave en dos archivos: la clave se muestra una sola vez. Van en la entrega al admin (3.3).
4. **SSL/TLS > Origin Server > Authenticated Origin Pulls**: activado.
5. **DNS > Settings > DNSSEC**: activar y copiar el registro DS en tu registrador.
6. **No actives Bot Fight Mode** (Security > Bots). En el plan gratis no admite excepciones y bloquea a quien llama desde centros de datos: la comprobación de salud que hace GitHub Actions tras cada despliegue fallaría y Uptime Kuma marcaría tu web como caída. Contra los intentos de adivinar contraseñas, limita los intentos de inicio de sesión en tu app.
7. Activa la **auto-renovación** del dominio en tu registrador.

## 3.2 Registra tu proyecto

Abre un PR a `projects.yml` de `infra-vps-tecnomovil` con tu proyecto (el admin lo revisa y lo acepta en 3.3):

```yaml
<tu-proyecto>:
  dueno: <tu-usuario-del-vps>
  repo: <cuenta>/<repositorio>
  dominios: { web: tudominio.com, api: api.tudominio.com }
  puertos: [81N1, 81N2]        # el admin te asigna N
  base: postgres               # postgres | propia | ninguna
  bd: <nombre>                 # opcional: nombre de la base y su usuario (minúsculas, números y _); por defecto, el del proyecto
```

## 3.3 Entrega al admin y PARADA

### Lo que preparas tú

1. **Clave solo para el CI** de tu proyecto, sin frase de paso:
   - Terminal: `ssh-keygen -t ed25519 -C "ci-<tu-proyecto>" -f ci-<tu-proyecto> -N ""`
   - PuTTYgen: tipo EdDSA (Ed25519) > Generate, comentario `ci-<tu-proyecto>`, sin passphrase. La pública es el texto del recuadro de arriba; la privada se guarda con Conversions > **Export OpenSSH key** (GitHub Actions no lee `.ppk`).

   La **privada** se queda en tu equipo hasta 3.4 (va en un secreto de GitHub y después la borras). La **pública** va al admin.
2. Envía al admin **por un canal privado** (nunca por el repositorio ni por un chat grupal):
   - el enlace de tu PR a `projects.yml` (3.2);
   - el certificado Origin y su clave (3.1);
   - la clave **pública** del CI (`ci-<tu-proyecto>.pub`);
   - los valores del `.env` que solo tú conoces (por ejemplo, claves de servicios externos). La URL de la base y las claves nuevas de la app (`SECRET_KEY` o similares) las genera el admin.

### Lo que hace el admin (tú no)

- Instala tu certificado en el servidor.
- Acepta tu PR y da de alta el proyecto (`vps-new-project`): carpeta, sitios nginx y, si `base: postgres`, tu base y tu usuario.
- Crea tu `.env` de producción en el VPS y guarda una copia en su gestor de contraseñas.
- Autoriza tu clave del CI con un comando forzado: esa clave solo puede desplegar tu proyecto.
- Te devuelve **por un canal privado** estos datos, que necesitas en 3.4: `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `VPS_HOST`, `VPS_KNOWN_HOSTS`, `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`.

### PARADA

**Instrucción para el LLM: detente aquí.** No sigas con 3.4 hasta que el dev confirme que el admin le dio el **OK** y le entregó los seis datos. Mientras tanto, solo resuelve dudas o ayuda con cambios del proyecto que no alteren lo entregado (dominio, puertos, nombre del proyecto ni variables). Si el dev intenta seguir sin el OK, recuérdale que el despliegue fallará porque el servidor todavía no conoce su proyecto.

## 3.4 GitHub Actions

### Secretos del repositorio

GitHub > tu repo > Settings > Secrets and variables > Actions, con los datos de la entrega:

| Secreto | Valor |
|---|---|
| `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET` | Te los dio el admin |
| `VPS_SSH_KEY` | La clave **privada** del CI que generaste en 3.3, completa (con las líneas `-----BEGIN` y `-----END`). Después bórrala de tu equipo |
| `VPS_HOST` | Te lo dio el admin |
| `VPS_KNOWN_HOSTS` | Te lo dio el admin (evita conectarse a un servidor falso) |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | Te los dio el admin: avisos de despliegues fallidos |

### El workflow de tu proyecto

`.github/workflows/deploy.yml`. Tu parte son las pruebas (y compilar la web, si tienes); el flujo compartido hace el resto. Estructura (los nombres exactos de las entradas los define `infra-vps-tecnomovil/.github/workflows/deploy.yml`; consúltalos allí):

```yaml
name: Desplegar
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

concurrency:
  group: desplegar-${{ github.ref }}
  cancel-in-progress: false

jobs:
  pruebas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      # Prepara tu lenguaje (setup-node, setup-python, setup-java...) y ejecuta tus pruebas.
      # Si tienes web estática: compílala y súbela con actions/upload-artifact como artefacto "web".

  vps:
    needs: pruebas
    uses: <cuenta>/infra-vps-tecnomovil/.github/workflows/deploy.yml@v1
    with:
      proyecto: <tu-proyecto>
      dockerfile: <ruta>/Dockerfile
      contexto: <ruta>
      web: web                                  # omítelo si no tienes web estática
      url_salud: https://api.tudominio.com/health
      desplegar: ${{ github.event_name != 'pull_request' }}
    secrets:
      TS_OAUTH_CLIENT_ID: ${{ secrets.TS_OAUTH_CLIENT_ID }}
      TS_OAUTH_SECRET: ${{ secrets.TS_OAUTH_SECRET }}
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
      VPS_HOST: ${{ secrets.VPS_HOST }}
      VPS_KNOWN_HOSTS: ${{ secrets.VPS_KNOWN_HOSTS }}
      TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

Los secretos se pasan uno por uno: `secrets: inherit` no funciona entre repositorios de cuentas distintas.

Qué pasa:

| Momento | Se ejecuta |
|---|---|
| Abres o actualizas un PR | Tus pruebas + build de la imagen + escaneo de vulnerabilidades + reglas del VPS + prueba de rendimiento y consumo (informa; solo bloquea si la app se cae). Nada se despliega |
| Merge a `main` | Todo lo anterior + imagen a GHCR + despliegue sin cortes + comprobación de la URL pública |
| Run workflow (manual) | Volver a desplegar `main`, por ejemplo tras cambiar el `.env` |

### Protege la rama `main`

Settings > Rules > Rulesets > New branch ruleset sobre `main`: exigir PR antes de merge, exigir que los checks `pruebas` y `vps` pasen, bloquear force push y borrado.

## 3.5 Repositorio público o privado

| Tema | Público | Privado (cuenta gratuita) |
|---|---|---|
| Protección de rama (rulesets) | Funciona | **No se aplica** en cuentas gratuitas (necesita GitHub Pro o una organización). Sin ella, cualquiera con acceso puede hacer push a `main` y desplegar: acuerda no hacerlo o pasa el repo a una organización |
| Minutos de GitHub Actions | Ilimitados | 2.000 al mes. Una ejecución típica gasta 5-10 minutos |
| Imagen en GHCR | En los dos casos el flujo compartido pasa al VPS un token temporal de solo lectura que caduca al terminar el job (GHCR crea los paquetes como privados aunque el repo sea público). No hay que guardar nada en el VPS | Igual |
| Espacio para imágenes | Gratis | Con cuota: consulta las cifras vigentes en la página de facturación de GitHub y borra imágenes viejas (Settings del paquete > políticas de retención) |
| Escaneo de secretos y CodeQL | Gratis | Limitado en cuentas gratuitas |
| Cuidado especial | Todo el código es visible: nada de IP, hosts internos ni secretos. Los PR de forks no reciben secretos (correcto). Nunca uses `pull_request_target` con el código del PR | Que sea privado no autoriza a guardar secretos en él |

## 3.6 Primer despliegue

1. Haz merge de tu PR a `main` (o Actions > Desplegar > Run workflow).
2. Sigue el job en GitHub Actions. Si falla, el mensaje dice el paso: reglas, migración, salud o nginx.
3. Comprueba tu dominio en el navegador y `https://api.tudominio.com/health`.
4. **Admin**: añade tus URLs a Uptime Kuma (3.8). Pídeselo con las URLs exactas: la web y la de `/health`.

## 3.7 Cargar datos que ya tienes (solo si tu proyecto ya funciona en otro sitio)

Si tu proyecto ya tiene usuarios, registros o archivos en otro servidor, se copian **después del primer despliegue** (las migraciones ya crearon las tablas) y **antes de avisar a tus usuarios**. Para que nadie cambie datos durante la copia, apaga primero el servidor viejo (mejor deshabilitarlo que borrarlo: si algo sale mal, se vuelve a encender).

### La base de datos (Postgres compartido)

Postgres no está abierto a Internet: se llega por un **túnel SSH** que lleva un puerto de tu equipo al Postgres del VPS. Usa un puerto libre en tu equipo, por ejemplo `15432`, para no chocar con un Postgres local.

- **Terminal (Windows, macOS, Linux)**, déjalo abierto mientras copias: `ssh -N -L 15432:127.0.0.1:5432 <tu-usuario>@<vps-en-tailscale>`
- **PuTTY**: carga tu sesión > Connection > SSH > Tunnels: Source port `15432`, Destination `127.0.0.1:5432`, Local > **Add**; vuelve a Session > **Save** y ábrela.

Con el túnel abierto, tu herramienta de copia (`pg_restore`, `psql`, un script propio...) se conecta a `127.0.0.1:15432` con el usuario y la contraseña de tu base, los mismos del `.env` del VPS. Compruébalo antes con `psql -h 127.0.0.1 -p 15432 -U <tu-usuario-bd> -d <tu-base> -c "select current_user"`.

Cuidado con:

- **Datos que tu app crea al arrancar** (categorías por defecto, un admin inicial...): si tu copia trae los suyos, chocan. Vacía esas tablas antes de copiar (pídeselo al admin) o haz que tu script los omita.
- **La contraseña en la URL**: si tiene `/`, `@`, `:`, `%`, `#` o `+`, hay que codificarla (`/` pasa a `%2F`) o la conexión falla. Más fácil: que sea solo letras y números.
- **No dejes la contraseña en pantalla ni en el historial.** Mejor que la herramienta la pida (como `psql` con `-U`). En PowerShell 5.1 (el de Windows por defecto), `Read-Host -MaskInput` **no oculta nada**: muestra lo que escribes. Para pedirla oculta: `$s = Read-Host "URL" -AsSecureString; $url = [Net.NetworkCredential]::new('', $s).Password` y al terminar `Remove-Variable s, url`. Si una contraseña llega a verse (en un chat, una captura, un log), pide al admin que la cambie.
- **Compara los conteos** de filas por tabla entre el origen y el VPS al terminar.

### Archivos (fotos, documentos subidos)

Tu app corre como el usuario `10001` y solo escribe en `/srv/apps/<tu-proyecto>/data/`, que tu usuario no puede leer. Por eso los archivos se suben primero a `/tmp` y se mueven con `sudo` (si no tienes `sudo`, este paso lo hace el admin):

1. Sube los archivos a `/tmp/` del VPS: con **WinSCP** (protocolo SFTP, arrástralos al panel derecho) o con `scp <archivos> <tu-usuario>@<vps-en-tailscale>:/tmp/`.
2. En el VPS:

```bash
sudo mv /tmp/<archivos> /srv/apps/<tu-proyecto>/data/<carpeta>/
sudo sh -c 'chown 10001:10001 /srv/apps/<tu-proyecto>/data/<carpeta>/* && ls -l /srv/apps/<tu-proyecto>/data/<carpeta>/'
```

El `chown` va dentro de `sudo sh -c '...'` a propósito: con `sudo chown ... /ruta/*`, el `*` lo expande tu usuario antes de `sudo` y, como no puede leer esa carpeta, falla con «No such file or directory». En el `ls` final todos los archivos deben aparecer con dueño `10001 10001`.

## 3.8 Día a día

| Quiero... | Cómo |
|---|---|
| Publicar un cambio | PR > pruebas en verde > merge. Nada más |
| Volver a la versión anterior | Por SSH: `vps-rollback <tu-proyecto>` (o a una concreta: `vps-rollback <tu-proyecto> <sha>`) |
| Ver logs | Por SSH: `vps-logs <tu-proyecto>` |
| Saber si mi web o mi API están caídas, y desde cuándo | **Uptime Kuma**: `https://<vps-en-tailscale>:8443`, con Tailscale activo y la cuenta compartida que te da el admin. Comprueba tus URLs cada minuto y avisa al grupo de Telegram si caen |
| Ver el consumo de mi proyecto (CPU, RAM, red) en tiempo real y su historial | **Beszel**: `https://<vps-en-tailscale>:8444`, con la cuenta compartida. En el sistema del VPS, la sección de Docker muestra tu contenedor (`<tu-proyecto>-azul-app-1` o `-verde-`) |
| Ver estado y consumo por consola | Por SSH: `vps-status` |
| Cambiar una variable de producción | Editar `/srv/apps/<tu-proyecto>/.env` y volver a desplegar con Run workflow |

Revisa Beszel después de cada despliegue grande y de vez en cuando: si la memoria de tu contenedor sube día tras día sin bajar, es una fuga. Corrígela antes de que afecte al resto del VPS.

## 3.9 Errores frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| El job falla en «reglas del VPS» | El compose incumple una regla | El mensaje dice cuál; ver 2.2 |
| El job falla en «Vulnerabilidades (Trivy)» | Una dependencia tiene una vulnerabilidad **crítica** que ya tiene solución publicada | La tabla del log dice la librería, la versión instalada y la versión con la solución. Actualízala (aunque tu proyecto limite la versión mayor, por ejemplo `<13`: sube ese límite), prueba que todo sigue funcionando y vuelve a subir |
| La prueba de consumo muestra memoria alta o que crece sin parar | Consumo excesivo o fuga de memoria | Optimiza antes de desplegar (2.9, 2.10): afecta a todos los proyectos del VPS |
| El job falla en «salud» | `/health` no responde en 90 s | Revisar logs del job; la app no arranca, falta una variable o la herramienta del healthcheck no existe en la imagen |
| El job falla en «migración» | Error en la migración | La versión anterior sigue sirviendo; corregir y volver a desplegar |
| Error de CORS en el navegador | Falta el dominio de la web en los orígenes permitidos de la API | Añadirlo en el `.env` y volver a desplegar |
| 404 al recargar una ruta de la web | El sitio no devuelve `index.html` para rutas de la SPA | Usar la plantilla `web.conf` |
| 502 / 504 | La app está caída o tarda demasiado | `vps-logs`; optimizar el endpoint lento |
| 521 / 522 de Cloudflare | Cloudflare no llega al VPS | Avisar al admin |
| 525 / 526 de Cloudflare | Certificado Origin mal instalado o no cubre ese nombre | Revisar 3.1 con el admin |
| La imagen tarda mucho en subir o es muy grande | Imagen sin multi-etapa o con dependencias de desarrollo | Ver 2.4 y `.dockerignore` |
