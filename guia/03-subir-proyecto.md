# 3. Subir tu proyecto al VPS

Requisito: tu proyecto cumple [02-preparar-proyecto.md](02-preparar-proyecto.md). Aquí: dominio, alta en el VPS, GitHub Actions y primer despliegue.

Algunos pasos los hace el **admin del VPS** (marcados así). Si tú también eres admin, los haces tú.

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
3. **SSL/TLS > Origin Server** > **Create Certificate** (RSA, `tudominio.com` y `*.tudominio.com`, 15 años). Guarda el certificado y la clave: la clave se muestra una sola vez. Envíalos al admin por un canal privado, nunca por el repositorio ni por un chat grupal.
4. **SSL/TLS > Origin Server > Authenticated Origin Pulls**: activado.
5. **DNS > Settings > DNSSEC**: activar y copiar el registro DS en tu registrador.
6. **No actives** Bot Fight Mode sin probar antes que tu app (sobre todo si tiene app móvil) y GitHub Actions siguen funcionando.
7. Activa la **auto-renovación** del dominio en tu registrador.

**Admin**: instala el certificado en `/etc/ssl/cloudflare/<dominio>.pem` y `.key` (clave con permisos 600).

## 3.2 Alta del proyecto en el VPS

1. Abre un PR a `projects.yml` de `infra-vps-tecnomovil` con tu proyecto:

```yaml
<tu-proyecto>:
  dueno: <tu-usuario-del-vps>
  repo: <cuenta>/<repositorio>
  dominios: { web: tudominio.com, api: api.tudominio.com }
  puertos: [81N1, 81N2]        # el admin te asigna N
  base: postgres               # postgres | propia | ninguna
  bd: <nombre>                 # opcional: nombre de la base y su usuario (minúsculas, números y _); por defecto, el del proyecto
```

2. **Admin**: acepta el PR y ejecuta `sudo vps-new-project <tu-proyecto>`. Crea la carpeta, los sitios nginx y, si `base: postgres`, la base y el usuario, e imprime una sola vez la URL de conexión.
3. **Admin**: crea `/srv/apps/<tu-proyecto>/.env` (600, dueño `deploy`) con los valores de tu `.env.example`. Guarda una copia de los valores en un gestor de contraseñas: si se pierde el VPS, es la única forma de recuperarlos.

## 3.3 GitHub Actions

### Secretos del repositorio

GitHub > tu repo > Settings > Secrets and variables > Actions:

| Secreto | De dónde sale |
|---|---|
| `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET` | **Admin**: Tailscale > Settings > OAuth clients (o Trust credentials) > nuevo cliente con permiso de escritura en `auth_keys` y etiqueta `tag:ci`. Uno por proyecto |
| `VPS_SSH_KEY` | Clave **solo para el CI** de tu proyecto: `ssh-keygen -t ed25519 -f ci-<tu-proyecto> -N ""`. La privada (`ci-<tu-proyecto>`) va aquí; la pública (`.pub`) se la das al admin y la borras de tu equipo. Con PuTTYgen: genera sin frase de paso y usa Conversions > **Export OpenSSH key** (GitHub Actions no lee `.ppk`) |
| `VPS_HOST` | Nombre del VPS en Tailscale (te lo da el admin) |
| `VPS_KNOWN_HOSTS` | **Admin**: salida de `ssh-keyscan <vps>` ejecutado desde un equipo del tailnet (vale el propio VPS, desde PuTTY). Evita conectarse a un servidor falso |
| `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | Te los da el admin: avisos de despliegues fallidos |

**Admin**: añade la clave pública a `/home/deploy/.ssh/authorized_keys` con el comando forzado (así esa clave solo puede desplegar tu proyecto):

```
command="/opt/vps/admin/bin/vps-deploy <tu-proyecto>",restrict ssh-ed25519 AAAA... ci-<tu-proyecto>
```

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

## 3.4 Repositorio público o privado

| Tema | Público | Privado (cuenta gratuita) |
|---|---|---|
| Protección de rama (rulesets) | Funciona | **No se aplica** en cuentas gratuitas (necesita GitHub Pro o una organización). Sin ella, cualquiera con acceso puede hacer push a `main` y desplegar: acuerda no hacerlo o pasa el repo a una organización |
| Minutos de GitHub Actions | Ilimitados | 2.000 al mes. Una ejecución típica gasta 5-10 minutos |
| Imagen en GHCR | Pública: el VPS la descarga sin credenciales | Privada: el flujo compartido pasa al VPS un token temporal de solo lectura que se borra al terminar. No hay que guardar nada en el VPS |
| Espacio para imágenes | Gratis | Con cuota: consulta las cifras vigentes en la página de facturación de GitHub y borra imágenes viejas (Settings del paquete > políticas de retención) |
| Escaneo de secretos y CodeQL | Gratis | Limitado en cuentas gratuitas |
| Cuidado especial | Todo el código es visible: nada de IP, hosts internos ni secretos. Los PR de forks no reciben secretos (correcto). Nunca uses `pull_request_target` con el código del PR | Que sea privado no autoriza a guardar secretos en él |

## 3.5 Primer despliegue

1. Haz merge de tu PR a `main` (o Actions > Desplegar > Run workflow).
2. Sigue el job en GitHub Actions. Si falla, el mensaje dice el paso: reglas, migración, salud o nginx.
3. Comprueba tu dominio en el navegador y `https://api.tudominio.com/health`.
4. **Admin**: añade tus URLs a Uptime Kuma.

## 3.6 Día a día

| Quiero... | Cómo |
|---|---|
| Publicar un cambio | PR > pruebas en verde > merge. Nada más |
| Volver a la versión anterior | Por SSH: `vps-rollback <tu-proyecto>` (o a una concreta: `vps-rollback <tu-proyecto> <sha>`) |
| Ver logs | Por SSH: `vps-logs <tu-proyecto>` |
| Ver estado y consumo | Por SSH: `vps-status` |
| Cambiar una variable de producción | Editar `/srv/apps/<tu-proyecto>/.env` y volver a desplegar con Run workflow |

## 3.7 Errores frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| El job falla en «reglas del VPS» | El compose incumple una regla | El mensaje dice cuál; ver 2.2 |
| La prueba de consumo muestra memoria alta o que crece sin parar | Consumo excesivo o fuga de memoria | Optimiza antes de desplegar (2.9, 2.10): afecta a todos los proyectos del VPS |
| El job falla en «salud» | `/health` no responde en 90 s | Revisar logs del job; la app no arranca, falta una variable o la herramienta del healthcheck no existe en la imagen |
| El job falla en «migración» | Error en la migración | La versión anterior sigue sirviendo; corregir y volver a desplegar |
| Error de CORS en el navegador | Falta el dominio de la web en los orígenes permitidos de la API | Añadirlo en el `.env` y volver a desplegar |
| 404 al recargar una ruta de la web | El sitio no devuelve `index.html` para rutas de la SPA | Usar la plantilla `web.conf` |
| 502 / 504 | La app está caída o tarda demasiado | `vps-logs`; optimizar el endpoint lento |
| 521 / 522 de Cloudflare | Cloudflare no llega al VPS | Avisar al admin |
| 525 / 526 de Cloudflare | Certificado Origin mal instalado o no cubre ese nombre | Revisar 3.1 con el admin |
| La imagen tarda mucho en subir o es muy grande | Imagen sin multi-etapa o con dependencias de desarrollo | Ver 2.4 y `.dockerignore` |
